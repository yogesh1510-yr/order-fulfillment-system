from enum import Enum


class OrderStatus(str, Enum):
    """
    Order statuses currently supported by NovaCart.
    """

    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"
    PACKED = "PACKED"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"