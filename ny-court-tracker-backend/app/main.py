import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import init_db, DB_PATH
from app.routers import auth, cases, appearances, dashboard, notifications, court_configs
from app.routers.scraper import router as scraper_router
from app.routers.email_integration import router as email_router
from app.routers.discovery import router as discovery_router
from app.scraper.scheduler import start_scheduler, stop_scheduler

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="NY Court Case Tracker API")

# Disable CORS. Do not remove this for full-stack development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)


@app.on_event("startup")
def on_startup():
    init_db()
    start_scheduler(DB_PATH)


@app.on_event("shutdown")
def on_shutdown():
    stop_scheduler()


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


app.include_router(auth.router)
app.include_router(cases.router)
app.include_router(appearances.router)
app.include_router(dashboard.router)
app.include_router(notifications.router)
app.include_router(court_configs.router)
app.include_router(scraper_router)
app.include_router(email_router)
app.include_router(discovery_router)
