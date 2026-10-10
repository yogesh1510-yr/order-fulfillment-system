from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    Numeric,
    String,
    func
)

from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.inventory import Inventory
    from app.models.order import Order


class Warehouse(Base):
    """
    ORM model for the warehouses table.
    """

    __tablename__ = "warehouses"

    warehouse_id: Mapped[str] = mapped_column(
        String(50),
        primary_key=True,
    )

    warehouse_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    warehouse_number: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    city: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    state: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    postal_code: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    country: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    latitude: Mapped[Decimal | None] = mapped_column(
        Numeric(9, 6),
        nullable=True,
    )

    longitude: Mapped[Decimal | None] = mapped_column(
        Numeric(9, 6),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )

    inventory_records: Mapped[list["Inventory"]] = relationship(
        back_populates="warehouse"
    )

    orders: Mapped[list["Order"]] = relationship(back_populates="warehouse")
