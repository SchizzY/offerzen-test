from fastapi import Depends, HTTPException, status
from fastapi.concurrency import run_in_threadpool

from app.resources.product_resource import ProductResource
from app.schemas.product import ProductStock


class ProductController:
    def __init__(self, resource: ProductResource = Depends()) -> None:
        self.resource = resource

    async def get_stock(self, sku: str) -> ProductStock:
        product = await run_in_threadpool(self.resource.get_by_sku, sku)
        if product is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Product {sku!r} not found")
        return ProductStock.model_validate(product)
