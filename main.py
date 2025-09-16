from fastapi import FastAPI
from core.db import engine
from fastapi.middleware.cors import CORSMiddleware
from core.settings import settings
from routers import auth as auth_router, families as families_router
from routers import users as users_router
from routers import memberships as memberships_router


app = FastAPI(title=settings.APP_NAME)
origins = settings.CORS_ORIGINS or []
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["*"],  # tighten to exact frontend origins in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router.router)
app.include_router(families_router.router)
app.include_router(users_router.router)
app.include_router(memberships_router.router)

@app.on_event("startup")
def startup_event():
    try:
        with engine.connect() as conn:
            result = conn.exec_driver_sql("SELECT version();")
            print("[DB OK] Connected to:", result.scalar_one())
    except Exception as e:
        print("[DB ERROR]", e)