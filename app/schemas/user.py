from pydantic import BaseModel

class UpdateProfileRequest(BaseModel):
    full_name: str | None = None
