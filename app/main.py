from app.api.v1 import subscription
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1 import auth, users, reports, dashboard, stripe
from app.api.v1.auth import router as auth_router
from app.api.v1.report import router as report_router
from contextlib import asynccontextmanager
from app.api.v1.subscription import router as subscription_router
from app.api.v1.admin import router as admin_router

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
app.include_router(subscription.router, prefix="/api/subscriptions", tags=["subscriptions"])
app.include_router(reports.router, prefix="/api/reports", tags=["reports"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["dashboard"])
app.include_router(stripe.router, prefix="/api/stripe", tags=["stripe"])
app.include_router(report_router)
app.include_router(subscription_router)
app.include_router(admin_router)

@app.get("/")
def read_root():
    return {"message": "Welcome to the Site Report API"}
