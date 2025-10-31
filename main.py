import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
import time
import uuid

from core.settings import settings
from core.db import engine
from core.security import RateLimitMiddleware, SecurityHeadersMiddleware
from routers import auth as auth_router, families as families_router
from routers import meals, storage, chat, meal_plans, pantry_items, user_preferences, memberships as memberships_router, users as users_router
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
    try:
        with engine.connect() as conn:
            result = conn.exec_driver_sql("SELECT version();")
            logger.info(f"[DB OK] Connected to: {result.scalar_one()}")
    except Exception as e:
        logger.error(f"[DB ERROR] {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down application")
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
        RateLimitMiddleware,
        default_requests=settings.RATE_LIMIT_REQUESTS,
        window_seconds=settings.RATE_LIMIT_WINDOW
    )

app.add_middleware(
    TrustedHostMiddleware, 
    allowed_hosts=["*"] if settings.APP_ENV == "local" else ["freshlybackend.duckdns.org", "freshly-app-frontend.vercel.app"]
)

# CORS middleware
origins = settings.CORS_ORIGINS + [
    "https://freshlybackend.duckdns.org",
    "https://freshly-app-frontend.vercel.app",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
] if settings.APP_ENV == "local" else settings.CORS_ORIGINS

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
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


# Health check endpoints
@app.get("/health")
async def health_check():
    """Basic health check"""
    return {"status": "healthy", "app": settings.APP_NAME, "env": settings.APP_ENV}


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
# API Routes with versioning
API_V1_PREFIX = "/api/v1"

app.include_router(auth_router.router, prefix=API_V1_PREFIX)
app.include_router(families_router.router, prefix=API_V1_PREFIX)
app.include_router(users_router.router, prefix=API_V1_PREFIX)
app.include_router(memberships_router.router, prefix=API_V1_PREFIX)
app.include_router(user_preferences.router, prefix=API_V1_PREFIX)
app.include_router(pantry_items.router, prefix=API_V1_PREFIX)
app.include_router(meal_plans.router, prefix=API_V1_PREFIX)
app.include_router(chat.router, prefix=API_V1_PREFIX)
app.include_router(meals.router, prefix=API_V1_PREFIX)
app.include_router(storage.router, prefix=API_V1_PREFIX)


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