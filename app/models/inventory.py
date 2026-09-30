from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)

from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.product import Product
    from app.models.warehouse import Warehouse


class Inventory(Base):
    """
    Inventory for one product at one warehouse.
    """

    __tablename__ = "inventory"

    __table_args__ = (
        UniqueConstraint(
            "product_id",
            "warehouse_id",
            name="uq_inventory_product_warehouse",
        ),
        CheckConstraint(
            "total_quantity >= 0",
            name="chk_inventory_total_quantity",
        ),
        CheckConstraint(
            "reserved_quantity >= 0",
            name="chk_inventory_reserved_quantity",
        ),
        CheckConstraint(
            "reserved_quantity <= total_quantity",
            name="chk_inventory_reserved_lte_total",
        ),
    )

    inventory_id: Mapped[str] = mapped_column(
        String(50),
        primary_key=True,
    )

    product_id: Mapped[str] = mapped_column(
        ForeignKey("products.product_id"),
        nullable=False,
    )

    warehouse_id: Mapped[str] = mapped_column(
        ForeignKey("warehouses.warehouse_id"),
        nullable=False,
    )

    total_quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    reserved_quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    product: Mapped["Product"] = relationship(back_populates="inventory_records")

    warehouse: Mapped["Warehouse"] = relationship(back_populates="inventory_records")

    @property
    def available_quantity(self) -> int:
        """
        Stock available for new orders.
        """

        return self.total_quantity - self.reserved_quantity

    def can_fulfill(
        self,
        requested_quantity: int,
    ) -> bool:
        """
        Check whether enough inventory is available.
        """

        return self.available_quantity >= requested_quantity
