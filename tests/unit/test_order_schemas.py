import pytest
from pydantic import ValidationError

from app.schemas.orders import (
    CreateOrderRequest,
    OrderItemRequest,
    ShippingAddress,
)


def make_shipping_address() -> ShippingAddress:
    return ShippingAddress(
        recipient_name="Yogesh",
        phone_number="9999999999",
        address_line1="123 Main Road",
        street="MG Road",
        city="Bengaluru",
        state="Karnataka",
        postal_code="560001",
        country="India",
    )


def test_order_item_request_accepts_valid_quantity():
    item = OrderItemRequest(
        product_id="PROD-001",
        quantity=2,
    )

    assert item.product_id == "PROD-001"
    assert item.quantity == 2


def test_order_item_request_rejects_zero_quantity():
    with pytest.raises(ValidationError):
        OrderItemRequest(
            product_id="PROD-001",
            quantity=0,
        )


def test_order_item_request_rejects_negative_quantity():
    with pytest.raises(ValidationError):
        OrderItemRequest(
            product_id="PROD-001",
            quantity=-5,
        )


def test_product_id_cannot_be_empty():
    with pytest.raises(ValidationError):
        OrderItemRequest(
            product_id="",
            quantity=1,
        )


def test_product_id_cannot_contain_only_whitespace():
    with pytest.raises(ValidationError):
        OrderItemRequest(
            product_id="     ",
            quantity=1,
        )


def test_product_id_whitespace_is_stripped():
    item = OrderItemRequest(
        product_id="   PROD-001   ",
        quantity=1,
    )

    assert item.product_id == "PROD-001"


def test_shipping_address_line2_is_optional():
    address = make_shipping_address()

    assert address.address_line2 is None


def test_create_order_requires_at_least_one_item():
    with pytest.raises(ValidationError):
        CreateOrderRequest(
            customer_id="CUST-001",
            idempotency_key="REQ-001",
            items=[],
            shipping_address=make_shipping_address(),
        )


def test_create_order_accepts_valid_request():
    request = CreateOrderRequest(
        customer_id="CUST-001",
        idempotency_key="REQ-001",
        items=[
            OrderItemRequest(
                product_id="PROD-001",
                quantity=2,
            )
        ],
        shipping_address=make_shipping_address(),
    )

    assert request.customer_id == "CUST-001"
    assert request.idempotency_key == "REQ-001"
    assert len(request.items) == 1
    assert request.items[0].quantity == 2