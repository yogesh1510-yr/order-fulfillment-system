from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import (
    BaseModel,
    Field,
    StringConstraints,
)

# =========================================================
# COMMON STRING TYPE
# =========================================================

NonEmptyStr = Annotated[
    str,
    StringConstraints(
        min_length=1,
        strip_whitespace=True,
    ),
]


# =========================================================
# REQUEST SCHEMAS
# =========================================================


class OrderItemRequest(BaseModel):

    product_id: NonEmptyStr

    quantity: int = Field(gt=0)


class ShippingAddress(BaseModel):

    recipient_name: NonEmptyStr
    phone_number: NonEmptyStr
    address_line1: NonEmptyStr

    address_line2: str | None = None

    street: NonEmptyStr
    city: NonEmptyStr
    state: NonEmptyStr
    postal_code: NonEmptyStr
    country: NonEmptyStr


class CreateOrderRequest(BaseModel):

    customer_id: NonEmptyStr

    idempotency_key: NonEmptyStr

    items: list[OrderItemRequest] = Field(min_length=1)

    shipping_address: ShippingAddress


# =========================================================
# RESPONSE SCHEMAS
# =========================================================


class OrderItemResponse(BaseModel):

    product_id: str
    product_name: str
    quantity: int
    unit_price: Decimal
    line_total: Decimal


class ShippingAddressResponse(BaseModel):

    recipient_name: str
    phone_number: str
    address_line1: str
    address_line2: str | None
    street: str
    city: str
    state: str
    postal_code: str
    country: str


class OrderPricingResponse(BaseModel):

    subtotal_amount: Decimal
    tax_amount: Decimal
    handling_amount: Decimal
    discount_amount: Decimal
    total_amount: Decimal


class OrderStatusHistoryResponse(BaseModel):

    status: str
    opened_at: datetime
    closed_at: datetime | None


class OrderResponse(BaseModel):

    order_id: str
    customer_id: str
    warehouse_id: str
    status: str

    items: list[OrderItemResponse]

    shipping_address: ShippingAddressResponse | None

    pricing: OrderPricingResponse

    status_history: list[OrderStatusHistoryResponse]

    created_at: datetime


class CreateOrderResponse(BaseModel):

    order_id: str
    status: str
    warehouse_id: str
    total_amount: Decimal
    message: str


class CancelOrderResponse(BaseModel):

    order_id: str
    status: str
    message: str
