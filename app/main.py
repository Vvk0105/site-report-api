from app.api.v1 import subscription
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1 import auth, users, reports, dashboard, stripe
from app.api.v1.auth import router as auth_router
from app.api.v1.report import router as report_router
from contextlib import asynccontextmanager
from app.api.v1.subscription import router as subscription_router
from app.api.v1.admin import router as admin_router
from app.api.v1.system import router as system_router
from app.api.v1.admin_plan import router as admin_plan_router
from app.api.v1.plan import router as plan_router
from app.db.database import SessionLocal
from app.startup.seed import seed_admin

from app.core.exceptions import (
    register_exception_handlers,
)
from app.api.v1.payment import (
    router as payment_router,
)
@asynccontextmanager
async def lifespan(app: FastAPI):

    async with SessionLocal() as db:
        await seed_admin(db)

    yield

app = FastAPI(title="Site Report API", version="1.0.0", lifespan=lifespan)

register_exception_handlers(
    app,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router,prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
# app.include_router(subscription.router, prefix="/api/v1/subscriptions", tags=["subscriptions"])
app.include_router(reports.router, prefix="/api/v1/reports", tags=["reports"])
app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["dashboard"])
app.include_router(stripe.router, prefix="/api/v1/stripe", tags=["stripe"])
app.include_router(report_router, prefix="/api/v1")
app.include_router(subscription_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")
app.include_router(system_router, prefix="/api/v1")
app.include_router(admin_plan_router, prefix="/api/v1")
app.include_router(payment_router, prefix="/api/v1")
app.include_router(plan_router, prefix="/api/v1")

@app.get("/")
def read_root():
    return {"message": "Welcome to the Site Report API"}
