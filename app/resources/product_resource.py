from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models.product import Product


class ProductResource:
    def __init__(self, session: Session = Depends(get_session)) -> None:
        self.session = session

    def get_by_sku(self, sku: str) -> Product | None:
        return self.session.scalar(select(Product).where(Product.sku == sku))

    def prices(self, skus: set[str]) -> dict[str, float]:
        rows = self.session.execute(
            select(Product.sku, Product.price_cents).where(Product.sku.in_(skus))
        )
        return {sku: price for sku, price in rows}
