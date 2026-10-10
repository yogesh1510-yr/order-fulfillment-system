from app.core.exceptions import (
    CustomerNotFoundError,
    InventoryConsistencyError,
    OrderCannotBeCancelledError,
    OrderFulfillmentError,
    OrderNotFoundError,
    ProductNotFoundError,
)


def test_customer_not_found_error():
    error = CustomerNotFoundError("CUST-001")

    assert error.customer_id == "CUST-001"
    assert str(error) == "Customer 'CUST-001' was not found"


def test_customer_not_found_is_application_error():
    error = CustomerNotFoundError("CUST-001")

    assert isinstance(error, OrderFulfillmentError)


def test_product_not_found_stores_product_ids():
    product_ids = [
        "PROD-001",
        "PROD-002",
    ]

    error = ProductNotFoundError(product_ids)

    assert error.product_ids == product_ids


def test_order_not_found_error():
    error = OrderNotFoundError("ORD-001")

    assert error.order_id == "ORD-001"
    assert str(error) == "Order 'ORD-001' was not found"


def test_order_cannot_be_cancelled_error():
    error = OrderCannotBeCancelledError(
        order_id="ORD-001",
        current_status="SHIPPED",
    )

    assert error.order_id == "ORD-001"
    assert error.current_status == "SHIPPED"

    assert (
        str(error)
        == "Order 'ORD-001' cannot be cancelled from status 'SHIPPED'"
    )


def test_inventory_consistency_error_preserves_message():
    error = InventoryConsistencyError(
        "Reserved quantity cannot become negative"
    )

    assert str(error) == "Reserved quantity cannot become negative"