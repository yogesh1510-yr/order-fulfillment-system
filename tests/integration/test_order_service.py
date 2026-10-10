from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import OrderStatus
from app.core.exceptions import (
    CustomerNotFoundError,
    ProductNotFoundError,
    InsufficientInventoryError,
    OrderNotFoundError,
    OrderCannotBeCancelledError,
    InventoryConsistencyError,
)
from app.models.customer import Customer
from app.models.inventory import Inventory
from app.models.payment import Payment
from app.payments.gateway import PaymentStatus
from app.payments.fake_gateway import FakePaymentGateway
from app.models.order import (
    Order,
    OrderItem,
    OrderShippingAddress,
    OrderStatusHistory,
)
from app.models.product import Product
from app.models.warehouse import Warehouse
from app.schemas.orders import (
    CreateOrderRequest,
    OrderItemRequest,
    ShippingAddress,
)
from app.services.orders import OrderService


class TimeoutPaymentGateway:
    def charge(
        self,
        *,
        order_id: str,
        amount: Decimal,
        idempotency_key: str,
    ):
        raise TimeoutError("Payment provider timed out")


class LostResponsePaymentGateway(FakePaymentGateway):
    """
    Simulates this scenario:

    First call:
        payment succeeds at provider,
        but response is lost.

    Later calls with the same idempotency key:
        provider returns the original successful result
        without charging again.
    """

    def __init__(self):
        super().__init__(should_succeed=True)
        self._first_call = True

    def charge(
        self,
        *,
        order_id: str,
        amount: Decimal,
        idempotency_key: str,
    ):
        result = super().charge(
            order_id=order_id,
            amount=amount,
            idempotency_key=idempotency_key,
        )

        if self._first_call:
            self._first_call = False

            raise TimeoutError("Payment succeeded but response was lost")

        return result


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
    db_session.flush()

    return customer


def create_product(
    db_session: Session,
    product_id: str = "PROD-001",
    mrp: Decimal = Decimal("500.00"),
) -> Product:
    product = Product(
        product_id=product_id,
        sku=f"SKU-{product_id}",
        product_name=f"Test Product {product_id}",
        size="M",
        mrp=mrp,
    )

    db_session.add(product)
    db_session.flush()

    return product


def create_warehouse(
    db_session: Session,
    warehouse_id: str = "WH-001",
    city: str = "Bengaluru",
    state: str = "Karnataka",
    postal_code: str = "560001",
) -> Warehouse:
    warehouse = Warehouse(
        warehouse_id=warehouse_id,
        warehouse_name=f"Warehouse {warehouse_id}",
        warehouse_number=f"NUM-{warehouse_id}",
        city=city,
        state=state,
        postal_code=postal_code,
        country="India",
    )

    db_session.add(warehouse)
    db_session.flush()

    return warehouse


def create_inventory(
    db_session: Session,
    product_id: str = "PROD-001",
    warehouse_id: str = "WH-001",
    total_quantity: int = 10,
    reserved_quantity: int = 0,
) -> Inventory:
    inventory = Inventory(
        inventory_id=f"INV-{product_id}-{warehouse_id}",
        product_id=product_id,
        warehouse_id=warehouse_id,
        total_quantity=total_quantity,
        reserved_quantity=reserved_quantity,
    )

    db_session.add(inventory)
    db_session.flush()

    return inventory


def create_order_request(
    *,
    customer_id: str = "CUST-001",
    idempotency_key: str = "IDEMP-001",
    product_id: str = "PROD-001",
    quantity: int = 2,
) -> CreateOrderRequest:
    return CreateOrderRequest(
        customer_id=customer_id,
        idempotency_key=idempotency_key,
        items=[
            OrderItemRequest(
                product_id=product_id,
                quantity=quantity,
            )
        ],
        shipping_address=ShippingAddress(
            recipient_name="Test Customer",
            phone_number="9999999999",
            address_line1="123 Test Road",
            address_line2=None,
            street="MG Road",
            city="Bengaluru",
            state="Karnataka",
            postal_code="560001",
            country="India",
        ),
    )


def create_standard_order_data(
    db_session: Session,
    *,
    total_quantity: int = 10,
    reserved_quantity: int = 0,
) -> Inventory:
    create_customer(db_session)

    create_product(
        db_session,
        product_id="PROD-001",
        mrp=Decimal("500.00"),
    )

    create_warehouse(db_session)

    inventory = create_inventory(
        db_session,
        product_id="PROD-001",
        warehouse_id="WH-001",
        total_quantity=total_quantity,
        reserved_quantity=reserved_quantity,
    )

    return inventory


# =========================================================
# 1. SUCCESSFUL ORDER CREATION
# =========================================================


def test_create_order_success(
    db_session: Session,
):
    # Arrange
    create_standard_order_data(db_session)

    request = create_order_request(
        quantity=2,
    )

    service = OrderService(
        db_session,
        payment_gateway=FakePaymentGateway(
            should_succeed=True,
        ),
    )

    # Act
    response = service.create_order(request)

    # Assert response
    assert response.order_id.startswith("ORD-")
    assert response.status == OrderStatus.CONFIRMED.value
    assert response.warehouse_id == "WH-001"
    assert response.total_amount == Decimal("1000.00")
    assert response.message == "Order created and payment successful"

    # -----------------------------------------------------
    # Verify Order exists in database
    # -----------------------------------------------------

    order = db_session.get(
        Order,
        response.order_id,
    )

    assert order is not None
    assert order.customer_id == "CUST-001"
    assert order.warehouse_id == "WH-001"
    assert order.idempotency_key == "IDEMP-001"
    assert order.status == OrderStatus.CONFIRMED.value

    assert order.subtotal_amount == Decimal("1000.00")
    assert order.tax_amount == Decimal("0.00")
    assert order.handling_amount == Decimal("0.00")
    assert order.discount_amount == Decimal("0.00")
    assert order.total_amount == Decimal("1000.00")

    # -----------------------------------------------------
    # Verify OrderItem
    # -----------------------------------------------------

    item = db_session.scalar(
        select(OrderItem).where(OrderItem.order_id == response.order_id)
    )

    assert item is not None
    assert item.product_id == "PROD-001"
    assert item.quantity == 2
    assert item.unit_price == Decimal("500.00")
    assert item.line_total == Decimal("1000.00")

    # -----------------------------------------------------
    # Verify Shipping Address
    # -----------------------------------------------------

    shipping = db_session.get(
        OrderShippingAddress,
        response.order_id,
    )

    assert shipping is not None
    assert shipping.recipient_name == "Test Customer"
    assert shipping.city == "Bengaluru"
    assert shipping.state == "Karnataka"
    assert shipping.postal_code == "560001"

    # -----------------------------------------------------
    # Verify Status History
    #
    # Successful payment now creates:
    #
    # PAYMENT_PENDING -> CONFIRMED
    # -----------------------------------------------------

    histories = list(
        db_session.scalars(
            select(OrderStatusHistory)
            .where(OrderStatusHistory.order_id == response.order_id)
            .order_by(OrderStatusHistory.status_open_date)
        ).all()
    )

    assert len(histories) == 2

    payment_pending = histories[0]

    assert payment_pending.status == OrderStatus.PAYMENT_PENDING.value
    assert payment_pending.status_open_date is not None
    assert payment_pending.status_close_date is not None

    confirmed = histories[1]

    assert confirmed.status == OrderStatus.CONFIRMED.value
    assert confirmed.status_open_date is not None
    assert confirmed.status_close_date is None

    assert payment_pending.status_close_date == confirmed.status_open_date


# =========================================================
# 2. INVENTORY RESERVATION
# =========================================================


def test_create_order_reserves_inventory(
    db_session: Session,
):
    # Arrange
    inventory = create_standard_order_data(
        db_session,
        total_quantity=10,
        reserved_quantity=2,
    )

    assert inventory.available_quantity == 8

    request = create_order_request(
        quantity=3,
    )

    service = OrderService(
        db_session,
        payment_gateway=FakePaymentGateway(
            should_succeed=True,
        ),
    )

    # Act
    service.create_order(request)

    # Refresh from PostgreSQL
    db_session.refresh(inventory)

    # Before:
    #
    # total     = 10
    # reserved  = 2
    # available = 8
    #
    # Order requests 3.
    #
    # After:
    #
    # total     = 10
    # reserved  = 5
    # available = 5

    assert inventory.total_quantity == 10
    assert inventory.reserved_quantity == 5
    assert inventory.available_quantity == 5


# =========================================================
# 3. DUPLICATE PRODUCT AGGREGATION
# =========================================================


def test_create_order_aggregates_duplicate_products(
    db_session: Session,
):
    # Arrange
    inventory = create_standard_order_data(
        db_session,
        total_quantity=10,
    )

    request = CreateOrderRequest(
        customer_id="CUST-001",
        idempotency_key="IDEMP-DUPLICATE",
        items=[
            OrderItemRequest(
                product_id="PROD-001",
                quantity=2,
            ),
            OrderItemRequest(
                product_id="PROD-001",
                quantity=3,
            ),
        ],
        shipping_address=ShippingAddress(
            recipient_name="Test Customer",
            phone_number="9999999999",
            address_line1="123 Test Road",
            address_line2=None,
            street="MG Road",
            city="Bengaluru",
            state="Karnataka",
            postal_code="560001",
            country="India",
        ),
    )

    service = OrderService(
        db_session,
        payment_gateway=FakePaymentGateway(
            should_succeed=True,
        ),
    )

    # Act
    response = service.create_order(request)

    db_session.refresh(inventory)

    # -----------------------------------------------------
    # 2 + 3 must become 5
    # -----------------------------------------------------

    assert inventory.reserved_quantity == 5
    assert inventory.available_quantity == 5

    # -----------------------------------------------------
    # Service creates one aggregated OrderItem
    # -----------------------------------------------------

    items = list(
        db_session.scalars(
            select(OrderItem).where(OrderItem.order_id == response.order_id)
        ).all()
    )

    assert len(items) == 1

    assert items[0].product_id == "PROD-001"
    assert items[0].quantity == 5
    assert items[0].unit_price == Decimal("500.00")

    # -----------------------------------------------------
    # Pricing must also use quantity 5
    # -----------------------------------------------------

    assert response.total_amount == Decimal("2500.00")


# =========================================================
# 4. CUSTOMER NOT FOUND
# =========================================================


def test_create_order_customer_not_found(
    db_session: Session,
):
    # Arrange
    #
    # We intentionally DO NOT create the customer.

    request = create_order_request(
        customer_id="CUST-NOT-FOUND",
    )

    service = OrderService(
        db_session,
        payment_gateway=FakePaymentGateway(
            should_succeed=True,
        ),
    )

    # Act + Assert
    with pytest.raises(CustomerNotFoundError):
        service.create_order(request)

    # -----------------------------------------------------
    # No order should have been created
    # -----------------------------------------------------

    orders = list(db_session.scalars(select(Order)).all())

    assert orders == []


# =========================================================
# 5. PRODUCT NOT FOUND
# =========================================================


def test_create_order_product_not_found(
    db_session: Session,
):
    # Arrange

    create_customer(db_session)

    request = create_order_request(
        product_id="PROD-NOT-FOUND",
    )

    service = OrderService(
        db_session,
        payment_gateway=FakePaymentGateway(
            should_succeed=True,
        ),
    )

    # Act + Assert
    with pytest.raises(ProductNotFoundError):
        service.create_order(request)

    # -----------------------------------------------------
    # No order should have been created
    # -----------------------------------------------------

    orders = list(db_session.scalars(select(Order)).all())

    assert orders == []


# =========================================================
# 6. INSUFFICIENT INVENTORY
# =========================================================


def test_create_order_insufficient_inventory(
    db_session: Session,
):
    # Arrange

    create_standard_order_data(
        db_session,
        total_quantity=5,
        reserved_quantity=3,
    )

    # Commit setup data so that the service rollback
    # does not remove our test fixtures.
    db_session.commit()

    inventory = db_session.scalar(
        select(Inventory).where(
            Inventory.product_id == "PROD-001",
            Inventory.warehouse_id == "WH-001",
        )
    )

    assert inventory is not None

    # total = 5
    # reserved = 3
    # available = 2

    assert inventory.total_quantity == 5
    assert inventory.reserved_quantity == 3
    assert inventory.available_quantity == 2

    request = create_order_request(
        quantity=3,
    )

    service = OrderService(
        db_session,
        payment_gateway=FakePaymentGateway(
            should_succeed=True,
        ),
    )

    # Act + Assert

    with pytest.raises(InsufficientInventoryError):
        service.create_order(request)

    # -----------------------------------------------------
    # Re-query after rollback
    # -----------------------------------------------------

    inventory_after_failure = db_session.scalar(
        select(Inventory).where(
            Inventory.product_id == "PROD-001",
            Inventory.warehouse_id == "WH-001",
        )
    )

    assert inventory_after_failure is not None

    # -----------------------------------------------------
    # Inventory must remain unchanged
    # -----------------------------------------------------

    assert inventory_after_failure.total_quantity == 5
    assert inventory_after_failure.reserved_quantity == 3
    assert inventory_after_failure.available_quantity == 2

    # -----------------------------------------------------
    # No Order should have been created
    # -----------------------------------------------------

    orders = list(db_session.scalars(select(Order)).all())

    assert orders == []


# =========================================================
# 7. IDEMPOTENT RETRY
# =========================================================


def test_create_order_idempotent_retry(
    db_session: Session,
):
    # Arrange
    inventory = create_standard_order_data(
        db_session,
        total_quantity=10,
    )

    request = create_order_request(
        idempotency_key="IDEMP-RETRY",
        quantity=2,
    )

    service = OrderService(
        db_session,
        payment_gateway=FakePaymentGateway(
            should_succeed=True,
        ),
    )

    # -----------------------------------------------------
    # First request
    # -----------------------------------------------------

    first_response = service.create_order(request)

    db_session.refresh(inventory)

    assert inventory.reserved_quantity == 2

    # -----------------------------------------------------
    # Same request again
    # -----------------------------------------------------

    second_response = service.create_order(request)

    # -----------------------------------------------------
    # Same order must be returned
    # -----------------------------------------------------

    assert second_response.order_id == first_response.order_id
    assert second_response.status == first_response.status
    assert second_response.warehouse_id == first_response.warehouse_id
    assert second_response.total_amount == first_response.total_amount

    assert second_response.message == "Order already exists"

    # -----------------------------------------------------
    # Inventory must NOT be reserved twice
    # -----------------------------------------------------

    db_session.refresh(inventory)

    assert inventory.reserved_quantity == 2
    assert inventory.available_quantity == 8

    # -----------------------------------------------------
    # Only one order must exist
    # -----------------------------------------------------

    orders = list(db_session.scalars(select(Order)).all())

    assert len(orders) == 1


# =========================================================
# 8. ALL-OR-NOTHING INVENTORY
# =========================================================


def test_create_order_multi_product_all_or_nothing(
    db_session: Session,
):
    # Arrange

    create_customer(db_session)

    create_product(
        db_session,
        product_id="PROD-001",
        mrp=Decimal("500.00"),
    )

    create_product(
        db_session,
        product_id="PROD-002",
        mrp=Decimal("300.00"),
    )

    create_warehouse(
        db_session,
        warehouse_id="WH-001",
    )

    # Product 1 has enough inventory.
    create_inventory(
        db_session,
        product_id="PROD-001",
        warehouse_id="WH-001",
        total_quantity=10,
    )

    # Product 2 does NOT have enough.
    create_inventory(
        db_session,
        product_id="PROD-002",
        warehouse_id="WH-001",
        total_quantity=1,
    )

    # Commit setup because create_order() will rollback
    # when it raises InsufficientInventoryError.
    db_session.commit()

    request = CreateOrderRequest(
        customer_id="CUST-001",
        idempotency_key="IDEMP-ALL-OR-NOTHING",
        items=[
            OrderItemRequest(
                product_id="PROD-001",
                quantity=2,
            ),
            OrderItemRequest(
                product_id="PROD-002",
                quantity=2,
            ),
        ],
        shipping_address=ShippingAddress(
            recipient_name="Test Customer",
            phone_number="9999999999",
            address_line1="123 Test Road",
            address_line2=None,
            street="MG Road",
            city="Bengaluru",
            state="Karnataka",
            postal_code="560001",
            country="India",
        ),
    )

    service = OrderService(
        db_session,
        payment_gateway=FakePaymentGateway(
            should_succeed=True,
        ),
    )

    # Act + Assert

    with pytest.raises(InsufficientInventoryError):
        service.create_order(request)

    # -----------------------------------------------------
    # Re-query inventory
    # -----------------------------------------------------

    inventories = list(db_session.scalars(select(Inventory)).all())

    inventory_by_product = {
        inventory.product_id: inventory for inventory in inventories
    }

    # Product 1 must NOT be partially reserved.
    assert inventory_by_product["PROD-001"].reserved_quantity == 0

    # Product 2 must also remain unchanged.
    assert inventory_by_product["PROD-002"].reserved_quantity == 0

    # -----------------------------------------------------
    # No order should exist
    # -----------------------------------------------------

    orders = list(db_session.scalars(select(Order)).all())

    assert orders == []


# =========================================================
# 9. WAREHOUSE - POSTAL CODE PRIORITY
# =========================================================


def test_create_order_selects_postal_code_match(
    db_session: Session,
):
    # Arrange

    create_customer(db_session)
    create_product(db_session)

    # Exact postal-code match.
    create_warehouse(
        db_session,
        warehouse_id="WH-POSTAL",
        city="Bengaluru",
        state="Karnataka",
        postal_code="560001",
    )

    # Same state, different city/postal code.
    create_warehouse(
        db_session,
        warehouse_id="WH-STATE",
        city="Mysuru",
        state="Karnataka",
        postal_code="570001",
    )

    create_inventory(
        db_session,
        product_id="PROD-001",
        warehouse_id="WH-POSTAL",
        total_quantity=10,
    )

    # Give the other warehouse MUCH more inventory.
    # Location score should still win.
    create_inventory(
        db_session,
        product_id="PROD-001",
        warehouse_id="WH-STATE",
        total_quantity=1000,
    )

    request = create_order_request(
        idempotency_key="IDEMP-POSTAL",
        quantity=2,
    )

    service = OrderService(
        db_session,
        payment_gateway=FakePaymentGateway(
            should_succeed=True,
        ),
    )

    # Act

    response = service.create_order(request)

    # Assert

    assert response.warehouse_id == "WH-POSTAL"


# =========================================================
# 10. WAREHOUSE - CITY PRIORITY
# =========================================================


def test_create_order_selects_city_match_over_state_match(
    db_session: Session,
):
    # Arrange

    create_customer(db_session)
    create_product(db_session)

    # Same city but different postal code.
    create_warehouse(
        db_session,
        warehouse_id="WH-CITY",
        city="Bengaluru",
        state="Karnataka",
        postal_code="560099",
    )

    # Same state but different city.
    create_warehouse(
        db_session,
        warehouse_id="WH-STATE",
        city="Mysuru",
        state="Karnataka",
        postal_code="570001",
    )

    create_inventory(
        db_session,
        product_id="PROD-001",
        warehouse_id="WH-CITY",
        total_quantity=10,
    )

    create_inventory(
        db_session,
        product_id="PROD-001",
        warehouse_id="WH-STATE",
        total_quantity=100,
    )

    request = create_order_request(
        idempotency_key="IDEMP-CITY",
        quantity=2,
    )

    service = OrderService(
        db_session,
        payment_gateway=FakePaymentGateway(
            should_succeed=True,
        ),
    )

    # Act

    response = service.create_order(request)

    # Assert

    assert response.warehouse_id == "WH-CITY"


# =========================================================
# 11. REMAINING STOCK TIE-BREAKER
# =========================================================


def test_create_order_uses_remaining_stock_as_tiebreaker(
    db_session: Session,
):
    # Arrange

    create_customer(db_session)
    create_product(db_session)

    # Both warehouses have exactly the same
    # location score.

    create_warehouse(
        db_session,
        warehouse_id="WH-LOW",
        city="Bengaluru",
        state="Karnataka",
        postal_code="560001",
    )

    create_warehouse(
        db_session,
        warehouse_id="WH-HIGH",
        city="Bengaluru",
        state="Karnataka",
        postal_code="560001",
    )

    create_inventory(
        db_session,
        product_id="PROD-001",
        warehouse_id="WH-LOW",
        total_quantity=10,
    )

    create_inventory(
        db_session,
        product_id="PROD-001",
        warehouse_id="WH-HIGH",
        total_quantity=50,
    )

    request = create_order_request(
        idempotency_key="IDEMP-STOCK",
        quantity=2,
    )

    service = OrderService(
        db_session,
        payment_gateway=FakePaymentGateway(
            should_succeed=True,
        ),
    )

    # Act

    response = service.create_order(request)

    # Assert
    #
    # Both location scores = 3.
    #
    # WH-LOW:
    # remaining = 10 - 2 = 8
    #
    # WH-HIGH:
    # remaining = 50 - 2 = 48
    #
    # Therefore WH-HIGH should win.

    assert response.warehouse_id == "WH-HIGH"


# =========================================================
# 12. ONLY ONE WAREHOUSE CAN FULFILL ENTIRE ORDER
# =========================================================


def test_create_order_selects_warehouse_that_can_fulfill_all_products(
    db_session: Session,
):
    # Arrange

    create_customer(db_session)

    create_product(
        db_session,
        product_id="PROD-001",
        mrp=Decimal("500.00"),
    )

    create_product(
        db_session,
        product_id="PROD-002",
        mrp=Decimal("300.00"),
    )

    create_warehouse(
        db_session,
        warehouse_id="WH-001",
    )

    create_warehouse(
        db_session,
        warehouse_id="WH-002",
    )

    # -----------------------------------------------------
    # WH-001
    #
    # Enough PROD-001
    # Not enough PROD-002
    # -----------------------------------------------------

    create_inventory(
        db_session,
        product_id="PROD-001",
        warehouse_id="WH-001",
        total_quantity=10,
    )

    create_inventory(
        db_session,
        product_id="PROD-002",
        warehouse_id="WH-001",
        total_quantity=1,
    )

    # -----------------------------------------------------
    # WH-002
    #
    # Enough of BOTH products
    # -----------------------------------------------------

    create_inventory(
        db_session,
        product_id="PROD-001",
        warehouse_id="WH-002",
        total_quantity=10,
    )

    create_inventory(
        db_session,
        product_id="PROD-002",
        warehouse_id="WH-002",
        total_quantity=10,
    )

    request = CreateOrderRequest(
        customer_id="CUST-001",
        idempotency_key="IDEMP-FULL-WAREHOUSE",
        items=[
            OrderItemRequest(
                product_id="PROD-001",
                quantity=2,
            ),
            OrderItemRequest(
                product_id="PROD-002",
                quantity=2,
            ),
        ],
        shipping_address=ShippingAddress(
            recipient_name="Test Customer",
            phone_number="9999999999",
            address_line1="123 Test Road",
            address_line2=None,
            street="MG Road",
            city="Bengaluru",
            state="Karnataka",
            postal_code="560001",
            country="India",
        ),
    )

    service = OrderService(
        db_session,
        payment_gateway=FakePaymentGateway(
            should_succeed=True,
        ),
    )

    # Act

    response = service.create_order(request)

    # Assert

    assert response.warehouse_id == "WH-002"

    # -----------------------------------------------------
    # Verify WH-001 inventory remains untouched
    # -----------------------------------------------------

    wh1_inventory = list(
        db_session.scalars(
            select(Inventory).where(Inventory.warehouse_id == "WH-001")
        ).all()
    )

    for inventory in wh1_inventory:
        assert inventory.reserved_quantity == 0

    # -----------------------------------------------------
    # Verify WH-002 reserved both products
    # -----------------------------------------------------

    wh2_inventory = list(
        db_session.scalars(
            select(Inventory).where(Inventory.warehouse_id == "WH-002")
        ).all()
    )

    wh2_by_product = {inventory.product_id: inventory for inventory in wh2_inventory}

    assert wh2_by_product["PROD-001"].reserved_quantity == 2

    assert wh2_by_product["PROD-002"].reserved_quantity == 2


# =========================================================
# 13. GET ORDER SUCCESS
# =========================================================


def test_get_order_success(
    db_session: Session,
):
    # -----------------------------------------------------
    # Arrange
    # -----------------------------------------------------

    create_standard_order_data(
        db_session,
        total_quantity=10,
    )

    create_request = create_order_request(
        idempotency_key="IDEMP-GET-ORDER",
        quantity=2,
    )

    service = OrderService(
        db_session,
        payment_gateway=FakePaymentGateway(
            should_succeed=True,
        ),
    )

    created = service.create_order(create_request)

    # -----------------------------------------------------
    # Act
    # -----------------------------------------------------

    response = service.get_order(created.order_id)

    # -----------------------------------------------------
    # Assert - ORDER
    # -----------------------------------------------------

    assert response.order_id == created.order_id
    assert response.customer_id == "CUST-001"
    assert response.warehouse_id == "WH-001"

    assert response.status == OrderStatus.CONFIRMED.value

    assert response.created_at is not None

    # -----------------------------------------------------
    # Assert - ITEMS
    # -----------------------------------------------------

    assert len(response.items) == 1

    item = response.items[0]

    assert item.product_id == "PROD-001"
    assert item.product_name == "Test Product PROD-001"
    assert item.quantity == 2
    assert item.unit_price == Decimal("500.00")
    assert item.line_total == Decimal("1000.00")

    # -----------------------------------------------------
    # Assert - SHIPPING ADDRESS
    # -----------------------------------------------------

    shipping = response.shipping_address

    assert shipping is not None

    assert shipping.recipient_name == "Test Customer"
    assert shipping.phone_number == "9999999999"

    assert shipping.address_line1 == "123 Test Road"
    assert shipping.address_line2 is None

    assert shipping.street == "MG Road"
    assert shipping.city == "Bengaluru"
    assert shipping.state == "Karnataka"
    assert shipping.postal_code == "560001"
    assert shipping.country == "India"

    # -----------------------------------------------------
    # Assert - PRICING
    # -----------------------------------------------------

    assert response.pricing.subtotal_amount == Decimal("1000.00")

    assert response.pricing.tax_amount == Decimal("0.00")

    assert response.pricing.handling_amount == Decimal("0.00")

    assert response.pricing.discount_amount == Decimal("0.00")

    assert response.pricing.total_amount == Decimal("1000.00")

    # -----------------------------------------------------
    # Assert - STATUS HISTORY
    #
    # PAYMENT_PENDING -> CONFIRMED
    # -----------------------------------------------------

    assert len(response.status_history) == 2

    payment_pending = response.status_history[0]

    assert payment_pending.status == OrderStatus.PAYMENT_PENDING.value

    assert payment_pending.opened_at is not None
    assert payment_pending.closed_at is not None

    confirmed = response.status_history[1]

    assert confirmed.status == OrderStatus.CONFIRMED.value

    assert confirmed.opened_at is not None
    assert confirmed.closed_at is None

    assert payment_pending.closed_at == confirmed.opened_at


# =========================================================
# 14. GET ORDER - NOT FOUND
# =========================================================


def test_get_order_not_found(
    db_session: Session,
):
    # Arrange

    service = OrderService(
        db_session,
        payment_gateway=FakePaymentGateway(
            should_succeed=True,
        ),
    )

    # Act + Assert

    with pytest.raises(OrderNotFoundError):
        service.get_order("ORD-NOT-FOUND")


# =========================================================
# 15. GET ORDER - MULTIPLE ITEMS
# =========================================================


def test_get_order_returns_multiple_items(
    db_session: Session,
):
    # -----------------------------------------------------
    # Arrange
    # -----------------------------------------------------

    create_customer(db_session)

    create_product(
        db_session,
        product_id="PROD-001",
        mrp=Decimal("500.00"),
    )

    create_product(
        db_session,
        product_id="PROD-002",
        mrp=Decimal("300.00"),
    )

    create_warehouse(
        db_session,
        warehouse_id="WH-001",
    )

    create_inventory(
        db_session,
        product_id="PROD-001",
        warehouse_id="WH-001",
        total_quantity=10,
    )

    create_inventory(
        db_session,
        product_id="PROD-002",
        warehouse_id="WH-001",
        total_quantity=10,
    )

    request = CreateOrderRequest(
        customer_id="CUST-001",
        idempotency_key="IDEMP-MULTI-GET",
        items=[
            OrderItemRequest(
                product_id="PROD-001",
                quantity=2,
            ),
            OrderItemRequest(
                product_id="PROD-002",
                quantity=3,
            ),
        ],
        shipping_address=ShippingAddress(
            recipient_name="Test Customer",
            phone_number="9999999999",
            address_line1="123 Test Road",
            address_line2=None,
            street="MG Road",
            city="Bengaluru",
            state="Karnataka",
            postal_code="560001",
            country="India",
        ),
    )

    service = OrderService(
        db_session,
        payment_gateway=FakePaymentGateway(
            should_succeed=True,
        ),
    )

    created = service.create_order(request)

    # -----------------------------------------------------
    # Act
    # -----------------------------------------------------

    response = service.get_order(created.order_id)

    # -----------------------------------------------------
    # Assert
    # -----------------------------------------------------

    assert len(response.items) == 2

    items_by_product = {item.product_id: item for item in response.items}

    # PROD-001
    assert items_by_product["PROD-001"].quantity == 2

    assert items_by_product["PROD-001"].unit_price == Decimal("500.00")

    assert items_by_product["PROD-001"].line_total == Decimal("1000.00")

    # PROD-002
    assert items_by_product["PROD-002"].quantity == 3

    assert items_by_product["PROD-002"].unit_price == Decimal("300.00")

    assert items_by_product["PROD-002"].line_total == Decimal("900.00")

    # -----------------------------------------------------
    # Total:
    #
    # PROD-001 = 2 × 500 = 1000
    # PROD-002 = 3 × 300 =  900
    #                         ----
    #                         1900
    # -----------------------------------------------------

    assert response.pricing.subtotal_amount == Decimal("1900.00")

    assert response.pricing.total_amount == Decimal("1900.00")


# =========================================================
# 16. GET ORDER - STATUS HISTORY SORTING
# =========================================================


def test_get_order_sorts_status_history_by_open_date(
    db_session: Session,
):
    # -----------------------------------------------------
    # Arrange
    # -----------------------------------------------------

    create_standard_order_data(
        db_session,
        total_quantity=10,
    )

    service = OrderService(
        db_session,
        payment_gateway=FakePaymentGateway(
            should_succeed=True,
        ),
    )

    created = service.create_order(
        create_order_request(
            idempotency_key="IDEMP-HISTORY-SORT",
            quantity=1,
        )
    )

    # -----------------------------------------------------
    # Fetch existing histories explicitly.
    # -----------------------------------------------------

    payment_pending_history = db_session.scalar(
        select(OrderStatusHistory).where(
            OrderStatusHistory.order_id == created.order_id,
            OrderStatusHistory.status == OrderStatus.PAYMENT_PENDING.value,
        )
    )

    confirmed_history = db_session.scalar(
        select(OrderStatusHistory).where(
            OrderStatusHistory.order_id == created.order_id,
            OrderStatusHistory.status == OrderStatus.CONFIRMED.value,
        )
    )

    assert payment_pending_history is not None
    assert confirmed_history is not None

    # -----------------------------------------------------
    # Give each history a deliberately known timestamp.
    # -----------------------------------------------------

    from datetime import datetime, timezone

    payment_pending_history.status_open_date = datetime(
        2026,
        1,
        1,
        9,
        0,
        tzinfo=timezone.utc,
    )

    payment_pending_history.status_close_date = datetime(
        2026,
        1,
        1,
        10,
        0,
        tzinfo=timezone.utc,
    )

    confirmed_history.status_open_date = datetime(
        2026,
        1,
        1,
        10,
        0,
        tzinfo=timezone.utc,
    )

    confirmed_history.status_close_date = datetime(
        2026,
        1,
        1,
        11,
        0,
        tzinfo=timezone.utc,
    )

    # -----------------------------------------------------
    # Insert a later status.
    # -----------------------------------------------------

    later_history = OrderStatusHistory(
        status_history_id="OSH-LATER",
        order_id=created.order_id,
        status="TEST_LATER_STATUS",
        status_open_date=datetime(
            2026,
            1,
            1,
            11,
            0,
            tzinfo=timezone.utc,
        ),
        status_close_date=None,
    )

    db_session.add(later_history)
    db_session.commit()

    # -----------------------------------------------------
    # Act
    # -----------------------------------------------------

    response = service.get_order(created.order_id)

    # -----------------------------------------------------
    # Assert
    # -----------------------------------------------------

    assert len(response.status_history) == 3

    assert response.status_history[0].status == OrderStatus.PAYMENT_PENDING.value

    assert response.status_history[1].status == OrderStatus.CONFIRMED.value

    assert response.status_history[2].status == "TEST_LATER_STATUS"

    opened_dates = [history.opened_at for history in response.status_history]

    assert opened_dates == sorted(opened_dates)


# =========================================================
# 17. CANCEL ORDER SUCCESS
# =========================================================


def test_cancel_order_success(
    db_session: Session,
):
    # Arrange

    create_standard_order_data(
        db_session,
        total_quantity=10,
    )

    service = OrderService(
        db_session,
        payment_gateway=FakePaymentGateway(
            should_succeed=True,
        ),
    )

    created = service.create_order(
        create_order_request(
            idempotency_key="IDEMP-CANCEL-001",
            quantity=2,
        )
    )

    # Act

    response = service.cancel_order(created.order_id)

    # Assert response

    assert response.order_id == created.order_id
    assert response.status == OrderStatus.CANCELLED.value
    assert response.message == "Order cancelled successfully"

    # Verify database

    order = db_session.get(
        Order,
        created.order_id,
    )

    assert order is not None
    assert order.status == OrderStatus.CANCELLED.value


# =========================================================
# 18. CANCELLATION RELEASES INVENTORY
# =========================================================


def test_cancel_order_releases_inventory(
    db_session: Session,
):
    # Arrange

    create_standard_order_data(
        db_session,
        total_quantity=10,
    )

    service = OrderService(
        db_session,
        payment_gateway=FakePaymentGateway(
            should_succeed=True,
        ),
    )

    created = service.create_order(
        create_order_request(
            idempotency_key="IDEMP-CANCEL-INVENTORY",
            quantity=3,
        )
    )

    inventory = db_session.scalar(
        select(Inventory).where(
            Inventory.product_id == "PROD-001",
            Inventory.warehouse_id == "WH-001",
        )
    )

    assert inventory is not None

    # Order creation reserved 3.
    assert inventory.reserved_quantity == 3
    assert inventory.available_quantity == 7

    # Act

    service.cancel_order(created.order_id)

    # Refresh after cancellation

    db_session.refresh(inventory)

    # Reservation should be released.

    assert inventory.total_quantity == 10
    assert inventory.reserved_quantity == 0
    assert inventory.available_quantity == 10


# =========================================================
# 19. CANCELLATION UPDATES STATUS HISTORY
# =========================================================


def test_cancel_order_updates_status_history(
    db_session: Session,
):
    # Arrange

    create_standard_order_data(
        db_session,
        total_quantity=10,
    )

    service = OrderService(
        db_session,
        payment_gateway=FakePaymentGateway(
            should_succeed=True,
        ),
    )

    created = service.create_order(
        create_order_request(
            idempotency_key="IDEMP-CANCEL-HISTORY",
            quantity=2,
        )
    )

    # Act

    service.cancel_order(created.order_id)

    # -----------------------------------------------------
    # Get history directly from DB.
    # -----------------------------------------------------

    histories = list(
        db_session.scalars(
            select(OrderStatusHistory)
            .where(OrderStatusHistory.order_id == created.order_id)
            .order_by(OrderStatusHistory.status_open_date)
        ).all()
    )

    assert len(histories) == 3

    history_by_status = {history.status: history for history in histories}

    # -----------------------------------------------------
    # PAYMENT_PENDING should be CLOSED.
    # -----------------------------------------------------

    payment_pending = history_by_status[OrderStatus.PAYMENT_PENDING.value]

    assert payment_pending.status_open_date is not None
    assert payment_pending.status_close_date is not None

    # -----------------------------------------------------
    # CONFIRMED should also be CLOSED.
    # -----------------------------------------------------

    confirmed = history_by_status[OrderStatus.CONFIRMED.value]

    assert confirmed.status_open_date is not None
    assert confirmed.status_close_date is not None

    # -----------------------------------------------------
    # CANCELLED should be OPEN/current.
    # -----------------------------------------------------

    cancelled = history_by_status[OrderStatus.CANCELLED.value]

    assert cancelled.status_open_date is not None
    assert cancelled.status_close_date is None

    # -----------------------------------------------------
    # Verify lifecycle continuity.
    # -----------------------------------------------------

    assert payment_pending.status_close_date == confirmed.status_open_date

    assert confirmed.status_close_date == cancelled.status_open_date


# =========================================================
# 20. CANCELLATION IS IDEMPOTENT
# =========================================================


def test_cancel_order_is_idempotent(
    db_session: Session,
):
    # Arrange

    create_standard_order_data(
        db_session,
        total_quantity=10,
    )

    service = OrderService(
        db_session,
        payment_gateway=FakePaymentGateway(
            should_succeed=True,
        ),
    )

    created = service.create_order(
        create_order_request(
            idempotency_key="IDEMP-CANCEL-TWICE",
            quantity=2,
        )
    )

    # -----------------------------------------------------
    # First cancellation
    # -----------------------------------------------------

    first_response = service.cancel_order(created.order_id)

    assert first_response.status == OrderStatus.CANCELLED.value

    # Inventory should already be released.

    inventory = db_session.scalar(
        select(Inventory).where(
            Inventory.product_id == "PROD-001",
            Inventory.warehouse_id == "WH-001",
        )
    )

    assert inventory is not None
    assert inventory.reserved_quantity == 0

    # -----------------------------------------------------
    # Second cancellation
    # -----------------------------------------------------

    second_response = service.cancel_order(created.order_id)

    assert second_response.status == OrderStatus.CANCELLED.value

    assert second_response.message == "Order is already cancelled"

    # -----------------------------------------------------
    # Inventory must NOT be released again.
    # -----------------------------------------------------

    db_session.refresh(inventory)

    assert inventory.reserved_quantity == 0

    # -----------------------------------------------------
    # We should have exactly three history records:
    #
    # PAYMENT_PENDING
    # CONFIRMED
    # CANCELLED
    #
    # Calling cancel_order() for the second time must NOT
    # create another CANCELLED history record.
    # -----------------------------------------------------

    histories = list(
        db_session.scalars(
            select(OrderStatusHistory).where(
                OrderStatusHistory.order_id == created.order_id
            )
        ).all()
    )

    assert len(histories) == 3

    statuses = [history.status for history in histories]

    assert statuses.count(OrderStatus.PAYMENT_PENDING.value) == 1

    assert statuses.count(OrderStatus.CONFIRMED.value) == 1

    assert statuses.count(OrderStatus.CANCELLED.value) == 1


# =========================================================
# 21. CANCEL ORDER - NOT FOUND
# =========================================================


def test_cancel_order_not_found(
    db_session: Session,
):
    service = OrderService(
        db_session,
        payment_gateway=FakePaymentGateway(
            should_succeed=True,
        ),
    )

    with pytest.raises(OrderNotFoundError):
        service.cancel_order("ORD-NOT-FOUND")


# =========================================================
# 22. ORDER CANNOT BE CANCELLED FROM INVALID STATUS
# =========================================================


def test_cancel_order_invalid_status(
    db_session: Session,
):
    # Arrange

    create_standard_order_data(
        db_session,
        total_quantity=10,
    )

    service = OrderService(
        db_session,
        payment_gateway=FakePaymentGateway(
            should_succeed=True,
        ),
    )

    created = service.create_order(
        create_order_request(
            idempotency_key="IDEMP-INVALID-STATUS",
            quantity=2,
        )
    )

    # -----------------------------------------------------
    # Simulate an order that has already shipped.
    # -----------------------------------------------------

    order = db_session.get(
        Order,
        created.order_id,
    )

    assert order is not None

    order.status = OrderStatus.SHIPPED.value

    db_session.commit()

    # -----------------------------------------------------
    # Act + Assert
    # -----------------------------------------------------

    with pytest.raises(OrderCannotBeCancelledError):
        service.cancel_order(created.order_id)

    # -----------------------------------------------------
    # Inventory must remain reserved because cancellation
    # was rejected.
    # -----------------------------------------------------

    inventory = db_session.scalar(
        select(Inventory).where(
            Inventory.product_id == "PROD-001",
            Inventory.warehouse_id == "WH-001",
        )
    )

    assert inventory is not None
    assert inventory.reserved_quantity == 2


# =========================================================
# 23. CANCELLATION - INVENTORY RECORD MISSING
# =========================================================


def test_cancel_order_inventory_record_missing(
    db_session: Session,
):
    # Arrange

    create_standard_order_data(
        db_session,
        total_quantity=10,
    )

    service = OrderService(
        db_session,
        payment_gateway=FakePaymentGateway(
            should_succeed=True,
        ),
    )

    created = service.create_order(
        create_order_request(
            idempotency_key="IDEMP-MISSING-INVENTORY",
            quantity=2,
        )
    )

    # -----------------------------------------------------
    # Deliberately corrupt our database state.
    #
    # The order exists, but the inventory record required
    # to release the reservation disappears.
    # -----------------------------------------------------

    inventory = db_session.scalar(
        select(Inventory).where(
            Inventory.product_id == "PROD-001",
            Inventory.warehouse_id == "WH-001",
        )
    )

    assert inventory is not None

    db_session.delete(inventory)
    db_session.commit()

    # -----------------------------------------------------
    # Act + Assert
    # -----------------------------------------------------

    with pytest.raises(InventoryConsistencyError):
        service.cancel_order(created.order_id)

    # -----------------------------------------------------
    # Cancellation must have rolled back.
    # Order should still be CONFIRMED.
    # -----------------------------------------------------

    order = db_session.get(
        Order,
        created.order_id,
    )

    assert order is not None

    assert order.status == OrderStatus.CONFIRMED.value


# =========================================================
# 24. CANCELLATION - RESERVED QUANTITY TOO LOW
# =========================================================


def test_cancel_order_reserved_quantity_too_low(
    db_session: Session,
):
    # Arrange

    create_standard_order_data(
        db_session,
        total_quantity=10,
    )

    service = OrderService(
        db_session,
        payment_gateway=FakePaymentGateway(
            should_succeed=True,
        ),
    )

    created = service.create_order(
        create_order_request(
            idempotency_key="IDEMP-BAD-RESERVATION",
            quantity=3,
        )
    )

    inventory = db_session.scalar(
        select(Inventory).where(
            Inventory.product_id == "PROD-001",
            Inventory.warehouse_id == "WH-001",
        )
    )

    assert inventory is not None

    # Order expects 3 reserved units.
    assert inventory.reserved_quantity == 3

    # -----------------------------------------------------
    # Deliberately corrupt reservation state.
    #
    # Order says quantity 3,
    # but inventory says only 1 is reserved.
    # -----------------------------------------------------

    inventory.reserved_quantity = 1

    db_session.commit()

    # -----------------------------------------------------
    # Act + Assert
    # -----------------------------------------------------

    with pytest.raises(InventoryConsistencyError):
        service.cancel_order(created.order_id)

    # -----------------------------------------------------
    # Cancellation should have rolled back.
    # -----------------------------------------------------

    order = db_session.get(
        Order,
        created.order_id,
    )

    assert order is not None

    assert order.status == OrderStatus.CONFIRMED.value

    # -----------------------------------------------------
    # The corrupted value existed BEFORE cancellation.
    # Rollback should leave it at 1.
    # -----------------------------------------------------

    inventory_after = db_session.scalar(
        select(Inventory).where(
            Inventory.product_id == "PROD-001",
            Inventory.warehouse_id == "WH-001",
        )
    )

    assert inventory_after is not None
    assert inventory_after.reserved_quantity == 1


def test_create_order_with_successful_payment(
    db_session: Session,
):
    # Arrange
    create_standard_order_data(
        db_session,
        total_quantity=10,
    )

    gateway = FakePaymentGateway(
        should_succeed=True,
    )

    service = OrderService(
        db_session,
        payment_gateway=gateway,
    )

    request = create_order_request(
        idempotency_key="IDEMP-PAYMENT-SUCCESS",
        quantity=2,
    )

    # Act
    response = service.create_order(request)

    # Assert
    assert response.status == OrderStatus.CONFIRMED.value

    order = service.orders.get_by_id_for_update(response.order_id)

    assert order is not None
    assert order.status == OrderStatus.CONFIRMED.value

    payments = service.payments.get_for_order(response.order_id)

    assert len(payments) == 1

    payment = payments[0]

    assert payment.status == "SUCCESS"
    assert payment.amount == response.total_amount
    assert payment.provider_transaction_id is not None
    assert payment.failure_reason is None


def test_create_order_with_failed_payment(
    db_session: Session,
):
    # Arrange
    create_standard_order_data(
        db_session,
        total_quantity=10,
    )

    gateway = FakePaymentGateway(
        should_succeed=False,
    )

    service = OrderService(
        db_session,
        payment_gateway=gateway,
    )

    request = create_order_request(
        idempotency_key="IDEMP-PAYMENT-FAILED",
        quantity=2,
    )

    # Act
    response = service.create_order(request)

    # Assert order
    assert response.status == OrderStatus.CANCELLED.value

    order = service.orders.get_by_id_for_update(response.order_id)

    assert order is not None
    assert order.status == OrderStatus.CANCELLED.value

    # Assert payment
    payments = service.payments.get_for_order(response.order_id)

    assert len(payments) == 1

    payment = payments[0]

    assert payment.status == "FAILED"
    assert payment.amount == response.total_amount
    assert payment.provider_transaction_id is None
    assert payment.failure_reason is not None

    # Assert inventory was released
    inventory = db_session.scalar(
        select(Inventory).where(
            Inventory.product_id == "PROD-001",
            Inventory.warehouse_id == "WH-001",
        )
    )

    assert inventory is not None
    assert inventory.reserved_quantity == 0
    assert inventory.available_quantity == 10

    # Assert status history
    histories = sorted(
        order.status_history,
        key=lambda history: history.status_open_date,
    )

    assert len(histories) == 2

    assert histories[0].status == OrderStatus.PAYMENT_PENDING.value

    assert histories[0].status_close_date is not None

    assert histories[1].status == OrderStatus.CANCELLED.value

    assert histories[1].status_close_date is None


def test_payment_gateway_timeout_keeps_order_pending(
    db_session: Session,
):
    # -----------------------------------------------------
    # Arrange
    # -----------------------------------------------------

    create_standard_order_data(
        db_session,
        total_quantity=10,
    )

    request = create_order_request(
        idempotency_key="IDEMP-PAYMENT-TIMEOUT",
        quantity=2,
    )

    service = OrderService(
        db_session,
        payment_gateway=TimeoutPaymentGateway(),  # type: ignore
    )

    # -----------------------------------------------------
    # Act
    # -----------------------------------------------------

    with pytest.raises(
        TimeoutError,
        match="Payment provider timed out",
    ):
        service.create_order(request)

    # -----------------------------------------------------
    # The first transaction was already committed.
    #
    # Therefore the order must still exist.
    # -----------------------------------------------------

    order = db_session.scalar(
        select(Order).where(Order.idempotency_key == "IDEMP-PAYMENT-TIMEOUT")
    )

    assert order is not None

    assert order.status == OrderStatus.PAYMENT_PENDING.value

    # -----------------------------------------------------
    # Inventory must remain RESERVED.
    #
    # We do NOT know whether the provider charged the
    # customer, so releasing inventory would be unsafe.
    # -----------------------------------------------------

    inventory = db_session.scalar(
        select(Inventory).where(
            Inventory.product_id == "PROD-001",
            Inventory.warehouse_id == "WH-001",
        )
    )

    assert inventory is not None
    assert inventory.reserved_quantity == 2

    # -----------------------------------------------------
    # No payment result was received, so we should not
    # have a SUCCESS or FAILED payment row.
    # -----------------------------------------------------

    payments = list(
        db_session.scalars(
            select(Payment).where(Payment.order_id == order.order_id)
        ).all()
    )

    assert payments == []


def test_lost_payment_response_can_be_recovered():

    gateway = LostResponsePaymentGateway()

    payment_key = "PAYMENT-ORD-RECOVERY-001"

    # -------------------------------------------------
    # FIRST ATTEMPT
    #
    # Provider processes the payment successfully,
    # but our application loses the response.
    # -------------------------------------------------

    with pytest.raises(
        TimeoutError,
        match="Payment succeeded but response was lost",
    ):
        gateway.charge(
            order_id="ORD-RECOVERY-001",
            amount=Decimal("1000.00"),
            idempotency_key=payment_key,
        )

    # -------------------------------------------------
    # SECOND ATTEMPT
    #
    # Same payment idempotency key.
    #
    # Provider must NOT create another payment.
    # It returns the result remembered from attempt #1.
    # -------------------------------------------------

    recovered_result = gateway.charge(
        order_id="ORD-RECOVERY-001",
        amount=Decimal("1000.00"),
        idempotency_key=payment_key,
    )

    assert (
        recovered_result.status
        == PaymentStatus.SUCCESS
    )

    assert recovered_result.transaction_id is not None

def test_retry_recovers_payment_after_lost_response(
    db_session: Session,
):
    # -----------------------------------------------------
    # ARRANGE
    # -----------------------------------------------------

    create_standard_order_data(
        db_session,
        total_quantity=10,
    )

    request = create_order_request(
        idempotency_key="IDEMP-PAYMENT-RECOVERY",
        quantity=2,
    )

    gateway = LostResponsePaymentGateway()

    service = OrderService(
        db_session,
        payment_gateway=gateway,
    )

    # -----------------------------------------------------
    # ATTEMPT 1
    #
    # Payment succeeds at provider, but response is lost.
    # -----------------------------------------------------

    with pytest.raises(
        TimeoutError,
        match="Payment succeeded but response was lost",
    ):
        service.create_order(request)

    # -----------------------------------------------------
    # Verify our DB is uncertain.
    # -----------------------------------------------------

    order_after_timeout = db_session.scalar(
        select(Order).where(
            Order.idempotency_key
            == "IDEMP-PAYMENT-RECOVERY"
        )
    )

    assert order_after_timeout is not None

    assert (
        order_after_timeout.status
        == OrderStatus.PAYMENT_PENDING.value
    )

    original_order_id = order_after_timeout.order_id

    # -----------------------------------------------------
    # ATTEMPT 2
    #
    # Same order request.
    # Same order idempotency key.
    #
    # We expect the service to recover the pending payment.
    # -----------------------------------------------------

    response = service.create_order(request)

    # -----------------------------------------------------
    # It MUST be the original order.
    #
    # We must not create another order.
    # -----------------------------------------------------

    assert response.order_id == original_order_id

    # -----------------------------------------------------
    # Payment should now be recovered as SUCCESS.
    # -----------------------------------------------------

    assert response.status == OrderStatus.CONFIRMED.value

    # -----------------------------------------------------
    # Verify persisted order.
    # -----------------------------------------------------

    db_session.expire_all()

    recovered_order = db_session.scalar(
        select(Order).where(
            Order.order_id == original_order_id
        )
    )

    assert recovered_order is not None

    assert (
        recovered_order.status
        == OrderStatus.CONFIRMED.value
    )

    # -----------------------------------------------------
    # Exactly ONE payment should exist.
    # -----------------------------------------------------

    payments = list(
        db_session.scalars(
            select(Payment).where(
                Payment.order_id == original_order_id
            )
        ).all()
    )

    assert len(payments) == 1

    assert (
        payments[0].status
        == PaymentStatus.SUCCESS.value
    )

    # -----------------------------------------------------
    # Inventory must remain reserved.
    #
    # Successful payment does NOT release reservation.
    # Warehouse still needs those units for fulfillment.
    # -----------------------------------------------------

    inventory = db_session.scalar(
        select(Inventory).where(
            Inventory.product_id == "PROD-001",
            Inventory.warehouse_id == "WH-001",
        )
    )

    assert inventory is not None
    assert inventory.reserved_quantity == 2