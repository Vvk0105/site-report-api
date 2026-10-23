from pydantic import BaseModel, Field


class UpdateProfileRequest(BaseModel):
    full_name: str | None = Field(default=None, max_length=255)
