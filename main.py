from core.settings import settings
from fastapi import FastAPI
from core.db import engine
from fastapi.middleware.cors import CORSMiddleware
from routers import auth as auth_router, families as families_router
from routers import meals, storage, chat, meal_plans, pantry_items, user_preferences, memberships as memberships_router, users as users_router
from dotenv import load_dotenv
load_dotenv()


app = FastAPI(title=settings.APP_NAME)
origins = settings.CORS_ORIGINS or []
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://freshlybackend.duckdns.org",
        "https://freshly-app-frontend.vercel.app",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "x-user-id", 
        "X-User-Id",  

    ],)
app.include_router(auth_router.router)
app.include_router(families_router.router)
app.include_router(users_router.router)
app.include_router(memberships_router.router)
app.include_router(user_preferences.router)
app.include_router(pantry_items.router)
app.include_router(meal_plans.router)
app.include_router(chat.router)
app.include_router(meals.router)
app.include_router(storage.router)



@app.on_event("startup")
def startup_event():
    try:
        with engine.connect() as conn:
            result = conn.exec_driver_sql("SELECT version();")
            print("[DB OK] Connected to:", result.scalar_one())
    except Exception as e:
        print("[DB ERROR]", e)