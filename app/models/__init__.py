"""
SQLAlchemy ORM models.

Importing this package registers all ORM models
with the shared Base metadata.
"""

from app.models.customer import Customer
from app.models.inventory import Inventory
from app.models.order import (
    Order,
    OrderItem,
    OrderShippingAddress,
    OrderStatusHistory,
)
from app.models.product import Product
from app.models.warehouse import Warehouse


__all__ = [
    "Customer",
    "Inventory",
    "Order",
    "OrderItem",
    "OrderShippingAddress",
    "OrderStatusHistory",
    "Product",
    "Warehouse",
]