from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.inventory import Inventory


class InventoryRepository:

    def __init__(
        self,
        db: Session,
    ):
        self.db = db

    def get_for_products(
        self,
        product_ids: list[str],
    ) -> list[Inventory]:
        """
        Get inventory records for products
        without locking them.
        """

        statement = select(Inventory).where(Inventory.product_id.in_(product_ids))

        return list(self.db.scalars(statement).all())

    def get_for_products_for_update(
        self,
        product_ids: list[str],
    ) -> list[Inventory]:
        """
        Get and lock inventory records.

        Used during order creation so concurrent
        requests cannot reserve the same stock
        simultaneously.
        """

        statement = (
            select(Inventory)
            .where(Inventory.product_id.in_(product_ids))
            .with_for_update()
        )

        return list(self.db.scalars(statement).all())

    def get_for_order_cancellation(
        self,
        warehouse_id: str,
        product_ids: list[str],
    ) -> list[Inventory]:
        """
        Lock inventory from the warehouse that
        fulfilled the order.
        """

        statement = (
            select(Inventory)
            .where(
                Inventory.warehouse_id == warehouse_id,
                Inventory.product_id.in_(product_ids),
            )
            .with_for_update()
        )

        return list(self.db.scalars(statement).all())
