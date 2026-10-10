from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
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
    from app.models.customer import Customer
    from app.models.product import Product
    from app.models.warehouse import Warehouse


# =========================================================
# ORDER
# =========================================================


class Order(Base):

    __tablename__ = "orders"

    __table_args__ = (
        CheckConstraint(
            "subtotal_amount >= 0",
            name="chk_orders_subtotal",
        ),
        CheckConstraint(
            "tax_amount >= 0",
            name="chk_orders_tax",
        ),
        CheckConstraint(
            "handling_amount >= 0",
            name="chk_orders_handling",
        ),
        CheckConstraint(
            "discount_amount >= 0",
            name="chk_orders_discount",
        ),
        CheckConstraint(
            "total_amount >= 0",
            name="chk_orders_total",
        ),
    )

    order_id: Mapped[str] = mapped_column(
        String(50),
        primary_key=True,
    )

    customer_id: Mapped[str] = mapped_column(
        ForeignKey("customers.customer_id"),
        nullable=False,
    )

    warehouse_id: Mapped[str] = mapped_column(
        ForeignKey("warehouses.warehouse_id"),
        nullable=False,
    )

    idempotency_key: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    subtotal_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    tax_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("0.00"),
    )

    handling_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("0.00"),
    )

    discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("0.00"),
    )

    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
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

    customer: Mapped["Customer"] = relationship(back_populates="orders")

    warehouse: Mapped["Warehouse"] = relationship(back_populates="orders")

    items: Mapped[list["OrderItem"]] = relationship(back_populates="order")

    shipping_address: Mapped["OrderShippingAddress | None"] = relationship(
        back_populates="order",
        uselist=False,
    )

    status_history: Mapped[list["OrderStatusHistory"]] = relationship(
        back_populates="order"
    )


# =========================================================
# ORDER ITEM
# =========================================================


class OrderItem(Base):

    __tablename__ = "order_items"

    __table_args__ = (
        CheckConstraint(
            "quantity > 0",
            name="chk_order_items_quantity",
        ),
        CheckConstraint(
            "unit_price >= 0",
            name="chk_order_items_unit_price",
        ),
    )

    order_item_id: Mapped[str] = mapped_column(
        String(50),
        primary_key=True,
    )

    order_id: Mapped[str] = mapped_column(
        ForeignKey("orders.order_id"),
        nullable=False,
    )

    product_id: Mapped[str] = mapped_column(
        ForeignKey("products.product_id"),
        nullable=False,
    )

    quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )

    order: Mapped["Order"] = relationship(back_populates="items")

    product: Mapped["Product"] = relationship(back_populates="order_items")

    @property
    def line_total(self) -> Decimal:
        return self.quantity * self.unit_price


# =========================================================
# SHIPPING ADDRESS
# =========================================================


class OrderShippingAddress(Base):

    __tablename__ = "order_shipping_addresses"

    order_id: Mapped[str] = mapped_column(
        ForeignKey("orders.order_id"),
        primary_key=True,
    )

    recipient_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    phone_number: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    address_line1: Mapped[str] = mapped_column(
        String(300),
        nullable=False,
    )

    address_line2: Mapped[str | None] = mapped_column(
        String(300),
        nullable=True,
    )

    street: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
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

    order: Mapped["Order"] = relationship(back_populates="shipping_address")


# =========================================================
# ORDER STATUS HISTORY
# =========================================================


class OrderStatusHistory(Base):

    __tablename__ = "order_status_history"

    status_history_id: Mapped[str] = mapped_column(
        String(50),
        primary_key=True,
    )

    order_id: Mapped[str] = mapped_column(
        ForeignKey("orders.order_id"),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    status_open_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )

    status_close_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    order: Mapped["Order"] = relationship(back_populates="status_history")
