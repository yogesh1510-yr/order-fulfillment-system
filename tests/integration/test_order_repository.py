from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.models.order import (
    Order,
    OrderItem,
    OrderShippingAddress,
    OrderStatusHistory,
)
from app.models.product import Product
from app.models.warehouse import Warehouse
from app.repositories.orders import OrderRepository


# =========================================================
# TEST DATA HELPERS
# =========================================================


def create_customer(
    db_session: Session,
    customer_id: str = "CUST-001",
) -> Customer:
    customer = Customer(
        customer_id=customer_id,
        name="Test Customer",
        phone_number="9999999999",
    )

    db_session.add(customer)

    return customer


def create_product(
    db_session: Session,
    product_id: str = "PROD-001",
) -> Product:
    product = Product(
        product_id=product_id,
        sku=f"SKU-{product_id}",
        product_name="Test Product",
        size="M",
        mrp=Decimal("500.00"),
    )

    db_session.add(product)

    return product


def create_warehouse(
    db_session: Session,
    warehouse_id: str = "WH-001",
) -> Warehouse:
    warehouse = Warehouse(
        warehouse_id=warehouse_id,
        warehouse_name="Test Warehouse",
        warehouse_number="WH-NUM-001",
        city="Bengaluru",
        state="Karnataka",
        postal_code="560001",
        country="India",
    )

    db_session.add(warehouse)

    return warehouse


def create_order(
    db_session: Session,
    order_id: str = "ORD-001",
    idempotency_key: str = "IDEMP-001",
    status: str = "CREATED",
) -> Order:
    order = Order(
        order_id=order_id,
        customer_id="CUST-001",
        warehouse_id="WH-001",
        idempotency_key=idempotency_key,
        status=status,
        subtotal_amount=Decimal("1000.00"),
        tax_amount=Decimal("100.00"),
        handling_amount=Decimal("50.00"),
        discount_amount=Decimal("0.00"),
        total_amount=Decimal("1150.00"),
    )

    db_session.add(order)

    return order


def create_basic_order_data(
    db_session: Session,
) -> Order:
    """
    Create the minimum database records required for an Order.

    Order depends on:
        Customer
        Warehouse

    Product is also created because several OrderRepository
    tests create OrderItems.
    """

    create_customer(db_session)
    create_product(db_session)
    create_warehouse(db_session)

    # Insert Customer/Product/Warehouse before Order because
    # Order contains foreign keys.
    db_session.flush()

    order = create_order(db_session)

    db_session.flush()

    return order


# =========================================================
# GET BY ID
# =========================================================


def test_get_order_by_id(
    db_session: Session,
):
    # Arrange
    create_basic_order_data(db_session)

    repository = OrderRepository(db_session)

    # Act
    result = repository.get_by_id(
        "ORD-001"
    )

    # Assert
    assert result is not None
    assert result.order_id == "ORD-001"
    assert result.customer_id == "CUST-001"
    assert result.warehouse_id == "WH-001"
    assert result.status == "CREATED"


def test_get_order_by_id_returns_none_when_missing(
    db_session: Session,
):
    repository = OrderRepository(db_session)

    result = repository.get_by_id(
        "ORD-NOT-FOUND"
    )

    assert result is None


# =========================================================
# IDEMPOTENCY
# =========================================================


def test_get_order_by_idempotency_key(
    db_session: Session,
):
    # Arrange
    create_basic_order_data(db_session)

    repository = OrderRepository(db_session)

    # Act
    result = repository.get_by_idempotency_key(
        "IDEMP-001"
    )

    # Assert
    assert result is not None
    assert result.order_id == "ORD-001"
    assert result.idempotency_key == "IDEMP-001"


def test_get_order_by_idempotency_key_returns_none(
    db_session: Session,
):
    repository = OrderRepository(db_session)

    result = repository.get_by_idempotency_key(
        "IDEMP-NOT-FOUND"
    )

    assert result is None


# =========================================================
# COMPLETE ORDER
# =========================================================


def test_get_complete_order_loads_relationships(
    db_session: Session,
):
    # Arrange
    create_basic_order_data(db_session)

    order_item = OrderItem(
        order_item_id="ITEM-001",
        order_id="ORD-001",
        product_id="PROD-001",
        quantity=2,
        unit_price=Decimal("500.00"),
    )

    shipping_address = OrderShippingAddress(
        order_id="ORD-001",
        recipient_name="Test Customer",
        phone_number="9999999999",
        address_line1="123 Test Road",
        address_line2=None,
        street="MG Road",
        city="Bengaluru",
        state="Karnataka",
        postal_code="560001",
        country="India",
    )

    status_history = OrderStatusHistory(
        status_history_id="STATUS-001",
        order_id="ORD-001",
        status="CREATED",
    )

    db_session.add_all(
        [
            order_item,
            shipping_address,
            status_history,
        ]
    )

    db_session.flush()

    repository = OrderRepository(db_session)

    # Act
    result = repository.get_complete_order(
        "ORD-001"
    )

    # Assert
    assert result is not None

    # -------------------------
    # Order
    # -------------------------

    assert result.order_id == "ORD-001"
    assert result.customer_id == "CUST-001"
    assert result.warehouse_id == "WH-001"

    # -------------------------
    # Warehouse
    # -------------------------

    assert result.warehouse is not None
    assert result.warehouse.warehouse_id == "WH-001"
    assert result.warehouse.warehouse_name == "Test Warehouse"

    # -------------------------
    # Order Items
    # -------------------------

    assert len(result.items) == 1

    item = result.items[0]

    assert item.order_item_id == "ITEM-001"
    assert item.product_id == "PROD-001"
    assert item.quantity == 2
    assert item.unit_price == Decimal("500.00")
    assert item.line_total == Decimal("1000.00")

    # -------------------------
    # Product relationship
    # -------------------------

    assert item.product is not None
    assert item.product.product_id == "PROD-001"
    assert item.product.product_name == "Test Product"

    # -------------------------
    # Shipping Address
    # -------------------------

    assert result.shipping_address is not None

    assert (
        result.shipping_address.recipient_name
        == "Test Customer"
    )

    assert result.shipping_address.city == "Bengaluru"
    assert result.shipping_address.state == "Karnataka"

    # -------------------------
    # Status History
    # -------------------------

    assert len(result.status_history) == 1

    assert (
        result.status_history[0].status
        == "CREATED"
    )


def test_get_complete_order_returns_none_when_missing(
    db_session: Session,
):
    repository = OrderRepository(db_session)

    result = repository.get_complete_order(
        "ORD-NOT-FOUND"
    )

    assert result is None


# =========================================================
# LOCK ORDER
# =========================================================


def test_get_order_by_id_for_update(
    db_session: Session,
):
    # Arrange
    create_basic_order_data(db_session)

    repository = OrderRepository(db_session)

    # Act
    result = repository.get_by_id_for_update(
        "ORD-001"
    )

    # Assert
    assert result is not None
    assert result.order_id == "ORD-001"


# =========================================================
# OPEN STATUS HISTORY
# =========================================================


def test_get_open_status_history(
    db_session: Session,
):
    # Arrange
    create_basic_order_data(db_session)

    history = OrderStatusHistory(
        status_history_id="STATUS-001",
        order_id="ORD-001",
        status="CREATED",
        status_close_date=None,
    )

    db_session.add(history)
    db_session.flush()

    # =====================================================
    # TEMPORARY DEBUGGING
    # =====================================================

    rows = db_session.scalars(
        select(OrderStatusHistory)
    ).all()

    print("\n")
    print("========================================")
    print("STATUS HISTORY ROWS")
    print("========================================")

    for row in rows:
        print(
            "status_history_id:",
            row.status_history_id,
        )

        print(
            "order_id:",
            row.order_id,
        )

        print(
            "status:",
            row.status,
        )

        print(
            "status_open_date:",
            row.status_open_date,
        )

        print(
            "status_close_date:",
            row.status_close_date,
        )

        print("----------------------------------------")

    # =====================================================
    # Repository
    # =====================================================

    repository = OrderRepository(db_session)

    # Act
    result = repository.get_open_status_history(
        "ORD-001"
    )

    print("\n")
    print("========================================")
    print("REPOSITORY RESULT")
    print("========================================")
    print(result)
    print("========================================")

    # Assert
    assert result is not None
    assert result.order_id == "ORD-001"
    assert result.status == "CREATED"
    assert result.status_close_date is None


def test_get_open_status_history_ignores_closed_status(
    db_session: Session,
):
    # Arrange
    create_basic_order_data(db_session)

    history = OrderStatusHistory(
        status_history_id="STATUS-001",
        order_id="ORD-001",
        status="CREATED",
        status_close_date=datetime.now(timezone.utc),
    )

    db_session.add(history)
    db_session.flush()

    repository = OrderRepository(db_session)

    # Act
    result = repository.get_open_status_history(
        "ORD-001"
    )

    # Assert
    assert result is None


# =========================================================
# ADD ORDER
# =========================================================


def test_add_order(
    db_session: Session,
):
    # Arrange
    create_customer(db_session)
    create_warehouse(db_session)

    db_session.flush()

    repository = OrderRepository(db_session)

    order = Order(
        order_id="ORD-NEW",
        customer_id="CUST-001",
        warehouse_id="WH-001",
        idempotency_key="IDEMP-NEW",
        status="CREATED",
        subtotal_amount=Decimal("500.00"),
        tax_amount=Decimal("50.00"),
        handling_amount=Decimal("20.00"),
        discount_amount=Decimal("0.00"),
        total_amount=Decimal("570.00"),
    )

    # Act
    repository.add(order)

    db_session.flush()

    # Assert
    result = db_session.get(
        Order,
        "ORD-NEW",
    )

    assert result is not None
    assert result.order_id == "ORD-NEW"
    assert result.status == "CREATED"


# =========================================================
# ADD ORDER ITEM
# =========================================================


def test_add_order_item(
    db_session: Session,
):
    # Arrange
    create_basic_order_data(db_session)

    repository = OrderRepository(db_session)

    item = OrderItem(
        order_item_id="ITEM-NEW",
        order_id="ORD-001",
        product_id="PROD-001",
        quantity=1,
        unit_price=Decimal("500.00"),
    )

    # Act
    repository.add_item(item)

    db_session.flush()

    # Assert
    result = db_session.get(
        OrderItem,
        "ITEM-NEW",
    )

    assert result is not None
    assert result.order_id == "ORD-001"
    assert result.product_id == "PROD-001"
    assert result.quantity == 1
    assert result.unit_price == Decimal("500.00")


# =========================================================
# ADD SHIPPING ADDRESS
# =========================================================


def test_add_shipping_address(
    db_session: Session,
):
    # Arrange
    create_basic_order_data(db_session)

    repository = OrderRepository(db_session)

    address = OrderShippingAddress(
        order_id="ORD-001",
        recipient_name="Test Customer",
        phone_number="9999999999",
        address_line1="123 Test Road",
        address_line2=None,
        street="MG Road",
        city="Bengaluru",
        state="Karnataka",
        postal_code="560001",
        country="India",
    )

    # Act
    repository.add_shipping_address(
        address
    )

    db_session.flush()

    # Assert
    result = db_session.get(
        OrderShippingAddress,
        "ORD-001",
    )

    assert result is not None
    assert result.order_id == "ORD-001"
    assert result.city == "Bengaluru"
    assert result.state == "Karnataka"


# =========================================================
# ADD STATUS HISTORY
# =========================================================


def test_add_status_history(
    db_session: Session,
):
    # Arrange
    create_basic_order_data(db_session)

    repository = OrderRepository(db_session)

    history = OrderStatusHistory(
        status_history_id="STATUS-NEW",
        order_id="ORD-001",
        status="CREATED",
    )

    # Act
    repository.add_status_history(
        history
    )

    db_session.flush()

    # Assert
    result = db_session.get(
        OrderStatusHistory,
        "STATUS-NEW",
    )

    assert result is not None
    assert result.order_id == "ORD-001"
    assert result.status == "CREATED"
    assert result.status_close_date is None