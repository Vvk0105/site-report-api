from fastapi import APIRouter

router = APIRouter()

@router.get("/")
def get_auth():
    return {"message": "Hello from auth api endpoint"}
