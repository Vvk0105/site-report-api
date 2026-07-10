from fastapi import APIRouter

router = APIRouter(
    tags=["System"],
)


@router.get("/health")
async def health():

    return {
        "status": "ok",
    }


@router.get("/version")
async def version():

    return {
        "app": "Site Report API",
        "version": "1.0.0",
    }