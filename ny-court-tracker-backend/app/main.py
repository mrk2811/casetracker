from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import init_db
from app.routers import auth, cases, appearances, dashboard, notifications, court_configs

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


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


app.include_router(auth.router)
app.include_router(cases.router)
app.include_router(appearances.router)
app.include_router(dashboard.router)
app.include_router(notifications.router)
app.include_router(court_configs.router)
