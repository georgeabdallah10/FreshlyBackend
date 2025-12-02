import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
import time
import uuid

from core.settings import settings
from core.db import engine
from core.security import SecurityHeadersMiddleware
from utils.cache import InMemoryCache
from routers import auth as auth_router, families as families_router
from routers import meals, storage, chat, meal_plans, pantry_items, user_preferences, memberships as memberships_router, users as users_router, meal_share_requests, notifications
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info(f"Starting {settings.APP_NAME} in {settings.APP_ENV} environment")

    # Database connection
    try:
        with engine.connect() as conn:
            result = conn.exec_driver_sql("SELECT version();")
            logger.info(f"[DB OK] Connected to: {result.scalar_one()}")
    except Exception as e:
        logger.error(f"[DB ERROR] {e}")
        raise

    # Redis connection (for rate limiting)
    if settings.REDIS_URL:
        try:
            import redis.asyncio as redis
            app.state.redis = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )
            await app.state.redis.ping()
            logger.info("[REDIS OK] Connected to Redis for rate limiting")
        except Exception as e:
            logger.warning(f"[REDIS WARNING] Failed to connect: {e}, using in-memory fallback")
            app.state.redis = None
    else:
        logger.info("[REDIS] URL not configured, rate limiting will use in-memory fallback")
        app.state.redis = None

    # Initialize in-memory fallback for rate limiting
    app.state.rate_limit_cache = InMemoryCache()
    logger.info("[CACHE] In-memory rate limit cache initialized")

    yield

    # Shutdown
    logger.info("Shutting down application")
    if hasattr(app.state, 'redis') and app.state.redis:
        await app.state.redis.close()
    engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="Freshly Meal Planning API",
    lifespan=lifespan
)
# Middleware setup
# Security middleware
if not settings.is_development:
    app.add_middleware(SecurityHeadersMiddleware)

app.add_middleware(
    TrustedHostMiddleware, 
    allowed_hosts=["*"] if settings.APP_ENV == "local" else ["freshlybackend.duckdns.org", "freshly-app-frontend.vercel.app"]
)

# CORS middleware
if settings.APP_ENV == "local":
    # Development - allow all origins
    origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://freshly-app-frontend.vercel.app",
        "https://freshlybackend.duckdns.org",
    ]
else:
    # Production - use configured origins
    origins = settings.CORS_ORIGINS or [
        "https://freshly-app-frontend.vercel.app",
        "https://freshlybackend.duckdns.org"
    ]

logger.info(f"CORS origins configured: {origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=[
        "Accept",
        "Accept-Language",
        "Content-Language",
        "Content-Type",
        "Authorization",
        "X-Requested-With",
        "Origin",
        "Access-Control-Request-Method",
        "Access-Control-Request-Headers",
        # Removed X-User-ID as we now use JWT authentication instead
    ],
    expose_headers=["X-Correlation-ID", "X-Process-Time", "ETag", "Cache-Control"],
)

# Compression middleware - reduces response sizes by 60-80%
app.add_middleware(
    GZipMiddleware,
    minimum_size=1000,  # Only compress responses > 1KB
    compresslevel=5     # Balance between speed and compression ratio
)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests with timing and correlation ID"""
    correlation_id = str(uuid.uuid4())[:8]
    start_time = time.time()
    
    # Add correlation ID to request state
    request.state.correlation_id = correlation_id
    
    logger.info(f"[{correlation_id}] {request.method} {request.url.path}")
    
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        
        logger.info(
            f"[{correlation_id}] {request.method} {request.url.path} "
            f"completed in {process_time:.3f}s with status {response.status_code}"
        )
        
        response.headers["X-Correlation-ID"] = correlation_id
        response.headers["X-Process-Time"] = str(process_time)
        
        return response
        
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(f"[{correlation_id}] Request failed after {process_time:.3f}s: {str(e)}")
        raise


# Global exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    correlation_id = getattr(request.state, "correlation_id", "unknown")
    logger.warning(f"[{correlation_id}] HTTP {exc.status_code}: {exc.detail}")
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "correlation_id": correlation_id,
            "status_code": exc.status_code
        }
    )


@app.exception_handler(SQLAlchemyError)
async def database_exception_handler(request: Request, exc: SQLAlchemyError):
    correlation_id = getattr(request.state, "correlation_id", "unknown")
    logger.error(f"[{correlation_id}] Database error: {str(exc)}")
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal database error",
            "correlation_id": correlation_id,
            "status_code": 500
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    correlation_id = getattr(request.state, "correlation_id", "unknown")
    logger.error(f"[{correlation_id}] Unexpected error: {str(exc)}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "correlation_id": correlation_id,
            "status_code": 500
        }
    )


# Explicit preflight handler for CORS
@app.options("/{full_path:path}")
async def preflight_handler(request: Request):
    """Handle CORS preflight requests explicitly"""
    response = JSONResponse(content=None, status_code=200)
    
    # Get origin from request
    origin = request.headers.get("origin")
    
    if origin:
        # Check if origin is allowed
        allowed_origins = [
            "https://freshly-app-frontend.vercel.app",
            "https://freshlybackend.duckdns.org", 
            "http://localhost:3000",
            "http://127.0.0.1:3000"
        ]
        
        if origin in allowed_origins or settings.APP_ENV == "local":
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, PATCH, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Accept, Accept-Language, Content-Language, Content-Type, Authorization, X-Requested-With, Origin"
            response.headers["Access-Control-Max-Age"] = "86400"  # 24 hours
    
    return response

# Health check endpoints
@app.get("/health")
async def health_check():
    """Basic health check"""
    return {"status": "healthy", "app": settings.APP_NAME, "env": settings.APP_ENV}

@app.get("/debug/version")
async def debug_version():
    """Debug endpoint to check current code version"""
    import subprocess
    try:
        # Get git commit hash if available
        result = subprocess.run(['git', 'rev-parse', '--short', 'HEAD'], 
                              capture_output=True, text=True, cwd='.')
        git_hash = result.stdout.strip() if result.returncode == 0 else "unknown"
    except:
        git_hash = "unknown"
    
    return {
        "git_commit": git_hash,
        "openai_configured": settings.openai_enabled,
        "storage_auth_method": "JWT via get_current_user",
        "cors_headers_removed": "X-User-ID removed from CORS",
        "timestamp": "2025-11-01T18:55:00Z"
    }

@app.get("/ready")
async def readiness_check():
    """Readiness check including database connectivity"""
    try:
        with engine.connect() as conn:
            conn.exec_driver_sql("SELECT 1")
        return {"status": "ready", "database": "connected"}
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "database": "disconnected", "error": str(e)}
        )

# API Routes - Simple structure without versioning
app.include_router(auth_router.router)
app.include_router(families_router.router)
app.include_router(users_router.router)
app.include_router(memberships_router.router)
app.include_router(user_preferences.router)
app.include_router(pantry_items.router)
app.include_router(meal_plans.router)
app.include_router(chat.router)
app.include_router(meals.router)
app.include_router(meal_share_requests.router)
app.include_router(notifications.router)
app.include_router(storage.router)


# Root endpoint
@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "environment": settings.APP_ENV
    }