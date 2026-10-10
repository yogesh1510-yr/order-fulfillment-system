from enum import Enum


class OrderStatus(str, Enum):
    """
    Order lifecycle statuses.
    """

    PENDING = "PENDING"
    PAYMENT_PENDING = "PAYMENT_PENDING"
    CONFIRMED = "CONFIRMED"

    PACKING = "PACKING"
    READY_FOR_SHIPMENT = "READY_FOR_SHIPMENT"
    SHIPPED = "SHIPPED"
    OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY"
    DELIVERED = "DELIVERED"

    CANCELLED = "CANCELLED"