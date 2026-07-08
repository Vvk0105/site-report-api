from fastapi import APIRouter

router = APIRouter()

@router.get("/")
def get_stripe():
    return {"message": "Hello from stripe api endpoint"}
