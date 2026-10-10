from decimal import Decimal

from app.models.order import OrderItem


def test_order_item_line_total():
    item = OrderItem(
        order_item_id="ITEM-001",
        order_id="ORD-001",
        product_id="PROD-001",
        quantity=3,
        unit_price=Decimal("250.00"),
    )

    assert item.line_total == Decimal("750.00")


def test_order_item_line_total_with_decimal_price():
    item = OrderItem(
        order_item_id="ITEM-001",
        order_id="ORD-001",
        product_id="PROD-001",
        quantity=2,
        unit_price=Decimal("199.99"),
    )

    assert item.line_total == Decimal("399.98")


def test_order_item_line_total_for_single_quantity():
    item = OrderItem(
        order_item_id="ITEM-001",
        order_id="ORD-001",
        product_id="PROD-001",
        quantity=1,
        unit_price=Decimal("499.50"),
    )

    assert item.line_total == Decimal("499.50")