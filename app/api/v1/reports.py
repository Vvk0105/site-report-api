from fastapi import APIRouter

router = APIRouter()

@router.get("/")
def get_reports():
    return {"message": "Hello from reports api endpoint"}
