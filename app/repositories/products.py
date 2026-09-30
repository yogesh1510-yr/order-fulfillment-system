from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.product import Product


class ProductRepository:

    def __init__(
        self,
        db: Session,
    ):
        self.db = db

    def get_by_ids(
        self,
        product_ids: list[str],
    ) -> list[Product]:

        statement = select(Product).where(Product.product_id.in_(product_ids))

        return list(self.db.scalars(statement).all())
