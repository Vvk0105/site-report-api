from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1 import auth, users, subscriptions, reports, dashboard, stripe
from app.api.v1.auth import router as auth_router
from contextlib import asynccontextmanager

from app.db.database import SessionLocal
from app.startup.seed import seed_admin

@asynccontextmanager
async def lifespan(app: FastAPI):

    async with SessionLocal() as db:
        await seed_admin(db)

    yield

app = FastAPI(title="Site Report API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router,prefix="/api/v1")
app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(subscriptions.router, prefix="/api/subscriptions", tags=["subscriptions"])
app.include_router(reports.router, prefix="/api/reports", tags=["reports"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["dashboard"])
app.include_router(stripe.router, prefix="/api/stripe", tags=["stripe"])

@app.get("/")
def read_root():
    return {"message": "Welcome to the Site Report API"}
