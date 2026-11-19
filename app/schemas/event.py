from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class OrderEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="Position in the log; resume with Last-Event-ID / after", examples=[17])
    type: Literal["order_accepted", "order_fulfilled"] = Field(
        description="`order_accepted`: what was ordered. `order_fulfilled`: what was supplied and charged"
    )
    order_id: int = Field(examples=[9])
    payload: dict = Field(description="The order as it was at this event")
    created_at: datetime
