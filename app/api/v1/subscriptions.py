from fastapi import APIRouter

router = APIRouter()

@router.get("/")
def get_subscriptions():
    return {"message": "Hello from subscriptions api endpoint"}
