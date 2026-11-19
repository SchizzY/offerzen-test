from fastapi import APIRouter, Depends, status

from app.controllers.product_controller import ProductController
from app.schemas.common import ErrorResponse
from app.schemas.product import ProductStock

router = APIRouter(prefix="/products", tags=["products"])


@router.get(
    "/{sku}/stock",
    status_code=status.HTTP_200_OK,
    operation_id="getProductStock",
    summary="Get current stock for a SKU",
    description=(
        "Current units on the shelf, read straight from Postgres. Stock is reduced "
        "by the stock worker after an order is accepted, so `pending` orders are "
        "not reflected until the worker processes them."
    ),
    response_description="The product's current stock",
    responses={
        status.HTTP_200_OK: {
            "content": {
                "application/json": {
                    "example": {
                        "sku": "BAN-001",
                        "name": "Bananas (1kg)",
                        "stock": 118,
                        "updated_at": "2026-11-19T09:30:00Z",
                    }
                }
            }
        },
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponse,
            "description": "No product with this SKU",
            "content": {"application/json": {"example": {"detail": "Product 'NOPE-001' not found"}}},
        },
    },
)
async def get_product_stock(sku: str, controller: ProductController = Depends()) -> ProductStock:
    return await controller.get_stock(sku)
