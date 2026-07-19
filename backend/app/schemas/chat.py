from typing import Any

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    service_id: int = Field(ge=1, description="ID сохранённого Moodle-сервиса")


class ChatResponse(BaseModel):
    result: Any
    tools_used: list[str] = []
