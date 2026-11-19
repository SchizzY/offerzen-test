from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProductStock(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    sku: str = Field(description="Product SKU", examples=["BAN-001"])
    name: str = Field(description="Product name", examples=["Bananas (1kg)"])
    stock: int = Field(
        description="Units on the shelf now; never negative. Orders still `pending` aren't deducted yet",
        examples=[118],
    )
    updated_at: datetime = Field(description="Last change to the product, including stock")
