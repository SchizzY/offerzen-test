from typing import Literal

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    detail: str = Field(description="What went wrong", examples=["Order 999 not found"])


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded", "down"] = Field(
        description="ok: all up. degraded: Valkey down, orders still accepted. down: Postgres down"
    )
    database: Literal["ok", "down"] = Field(description="Postgres connectivity")
    valkey: Literal["ok", "down"] = Field(description="Valkey cache connectivity")
