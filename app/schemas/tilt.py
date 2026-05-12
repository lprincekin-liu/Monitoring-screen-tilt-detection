from __future__ import annotations

from pydantic import BaseModel, Field


class TiltRequest(BaseModel):
    image_base64: str = Field(..., min_length=1, description="Base64 encoded image")


class TiltResponse(BaseModel):
    code: int
    is_tilted: bool
    angle: float
    cost_ms: float
    msg: str


class ErrorResponse(BaseModel):
    code: int
    msg: str
