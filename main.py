from fastapi import FastAPI
from core.db import engine
from fastapi.middleware.cors import CORSMiddleware
from core.settings import settings

app = FastAPI(title=settings.APP_NAME)
origins = settings.CORS_ORIGINS or []
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["*"],  # tighten to exact frontend origins in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    try:
        with engine.connect() as conn:
            result = conn.exec_driver_sql("SELECT version();")
            print("[DB OK] Connected to:", result.scalar_one())
    except Exception as e:
        print("[DB ERROR]", e)