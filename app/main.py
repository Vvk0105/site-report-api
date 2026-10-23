from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.admin import router as admin_router
from app.api.v1.admin_plan import router as admin_plan_router
from app.api.v1.auth import router as auth_router
from app.api.v1.payment import router as payment_router
from app.api.v1.plan import router as plan_router
from app.api.v1.report import router as report_router
from app.api.v1.subscription import router as subscription_router
from app.api.v1.system import router as system_router
from app.api.v1.users import router as users_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.db.database import SessionLocal
from app.startup.seed import seed_admin, seed_plans


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Schema changes are applied with `alembic upgrade head` (see the Dockerfile entrypoint).
    async with SessionLocal() as db:
        await seed_admin(db)
        await seed_plans(db)

    yield


app = FastAPI(title="Site Report API", version="1.0.0", lifespan=lifespan)

register_exception_handlers(app)

# Requests authenticate with a Bearer token, not cookies, so credentials are not needed.
# Origins are restricted to the admin panel and the public website.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

API_PREFIX = "/api/v1"

app.include_router(auth_router, prefix=API_PREFIX)
app.include_router(users_router, prefix=f"{API_PREFIX}/users", tags=["users"])
app.include_router(report_router, prefix=API_PREFIX)
app.include_router(subscription_router, prefix=API_PREFIX)
app.include_router(admin_router, prefix=API_PREFIX)
app.include_router(admin_plan_router, prefix=API_PREFIX)
app.include_router(plan_router, prefix=API_PREFIX)
app.include_router(payment_router, prefix=API_PREFIX)
app.include_router(system_router, prefix=API_PREFIX)


@app.get("/")
def read_root():
    return {"message": "Welcome to the Site Report API"}
