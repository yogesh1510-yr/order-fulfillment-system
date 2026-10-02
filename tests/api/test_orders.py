from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.main import app
from app.models.customer import Customer
from app.models.inventory import Inventory
from app.models.order import Order
from app.models.product import Product
from app.models.warehouse import Warehouse


# =========================================================
# CLIENT
# =========================================================


@pytest.fixture
def client(
    db_session: Session,
):
    """
    Replace the application's normal database dependency
    with our pytest database session.

    This means:

        HTTP request
            ↓
        FastAPI
            ↓
        get_db()
            ↓
        TEST database session

    The API test must never use our normal application DB.
    """

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


# =========================================================
# TEST DATA HELPERS
# =========================================================


def create_customer(
    db_session: Session,
    customer_id: str = "CUST-001",
):
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
):
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
):
    warehouse = Warehouse(
        warehouse_id=warehouse_id,
        warehouse_name=f"Warehouse {warehouse_id}",
        warehouse_number=f"NUM-{warehouse_id}",
        city="Bengaluru",
        state="Karnataka",
        postal_code="560001",
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
):
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


def create_standard_data(
    db_session: Session,
    *,
    total_quantity: int = 10,
    reserved_quantity: int = 0,
):
    create_customer(db_session)

    create_product(
        db_session,
        product_id="PROD-001",
        mrp=Decimal("500.00"),
    )

    create_warehouse(
        db_session,
        warehouse_id="WH-001",
    )

    return create_inventory(
        db_session,
        product_id="PROD-001",
        warehouse_id="WH-001",
        total_quantity=total_quantity,
        reserved_quantity=reserved_quantity,
    )


def valid_order_payload(
    *,
    customer_id: str = "CUST-001",
    product_id: str = "PROD-001",
    quantity: int = 2,
    idempotency_key: str = "IDEMP-API-001",
):
    return {
        "customer_id": customer_id,
        "idempotency_key": idempotency_key,
        "items": [
            {
                "product_id": product_id,
                "quantity": quantity,
            }
        ],
        "shipping_address": {
            "recipient_name": "Test Customer",
            "phone_number": "9999999999",
            "address_line1": "123 Test Road",
            "address_line2": None,
            "street": "MG Road",
            "city": "Bengaluru",
            "state": "Karnataka",
            "postal_code": "560001",
            "country": "India",
        },
    }


# =========================================================
# 1. CREATE ORDER - SUCCESS
# =========================================================


def test_create_order_api_success(
    client: TestClient,
    db_session: Session,
):
    create_standard_data(db_session)

    response = client.post(
        "/api/v1/orders",
        json=valid_order_payload(),
    )

    assert response.status_code == 201

    data = response.json()

    assert data["order_id"].startswith("ORD-")
    assert data["status"] == "CONFIRMED"
    assert data["warehouse_id"] == "WH-001"

    # Decimal is serialized to JSON.
    assert Decimal(str(data["total_amount"])) == Decimal(
        "1000.00"
    )

    assert data["message"] == "Order created successfully"

    # Verify actual database state.

    order = db_session.get(
        Order,
        data["order_id"],
    )

    assert order is not None
    assert order.status == "CONFIRMED"


# =========================================================
# 2. CREATE ORDER - INVENTORY RESERVED
# =========================================================


def test_create_order_api_reserves_inventory(
    client: TestClient,
    db_session: Session,
):
    inventory = create_standard_data(
        db_session,
        total_quantity=10,
    )

    response = client.post(
        "/api/v1/orders",
        json=valid_order_payload(
            quantity=3,
            idempotency_key="IDEMP-API-INVENTORY",
        ),
    )

    assert response.status_code == 201

    db_session.refresh(inventory)

    assert inventory.reserved_quantity == 3
    assert inventory.available_quantity == 7


# =========================================================
# 3. CREATE ORDER - IDEMPOTENCY
# =========================================================


def test_create_order_api_idempotency(
    client: TestClient,
    db_session: Session,
):
    inventory = create_standard_data(
        db_session,
        total_quantity=10,
    )

    payload = valid_order_payload(
        quantity=2,
        idempotency_key="IDEMP-API-RETRY",
    )

    first = client.post(
        "/api/v1/orders",
        json=payload,
    )

    assert first.status_code == 201

    second = client.post(
        "/api/v1/orders",
        json=payload,
    )

    assert second.status_code == 201

    first_data = first.json()
    second_data = second.json()

    assert (
        second_data["order_id"]
        == first_data["order_id"]
    )

    assert (
        second_data["message"]
        == "Order already exists"
    )

    db_session.refresh(inventory)

    # Must not reserve twice.
    assert inventory.reserved_quantity == 2


# =========================================================
# 4. CREATE ORDER - CUSTOMER NOT FOUND
# =========================================================


def test_create_order_api_customer_not_found(
    client: TestClient,
):
    response = client.post(
        "/api/v1/orders",
        json=valid_order_payload(
            customer_id="CUST-NOT-FOUND",
        ),
    )

    assert response.status_code == 404


# =========================================================
# 5. CREATE ORDER - PRODUCT NOT FOUND
# =========================================================


def test_create_order_api_product_not_found(
    client: TestClient,
    db_session: Session,
):
    create_customer(db_session)

    response = client.post(
        "/api/v1/orders",
        json=valid_order_payload(
            product_id="PROD-NOT-FOUND",
        ),
    )

    assert response.status_code == 404


# =========================================================
# 6. CREATE ORDER - INSUFFICIENT INVENTORY
# =========================================================


def test_create_order_api_insufficient_inventory(
    client: TestClient,
    db_session: Session,
):
    create_standard_data(
        db_session,
        total_quantity=2,
    )

    # Commit setup because the service performs rollback
    # when InsufficientInventoryError occurs.
    db_session.commit()

    response = client.post(
        "/api/v1/orders",
        json=valid_order_payload(
            quantity=3,
            idempotency_key="IDEMP-API-NO-STOCK",
        ),
    )

    assert response.status_code == 409

    orders = list(
        db_session.scalars(
            select(Order)
        ).all()
    )

    assert orders == []


# =========================================================
# 7. CREATE ORDER - INVALID QUANTITY
# =========================================================


def test_create_order_api_rejects_zero_quantity(
    client: TestClient,
):
    payload = valid_order_payload(
        quantity=1,
    )

    payload["items"][0]["quantity"] = 0

    response = client.post(
        "/api/v1/orders",
        json=payload,
    )

    # Request fails at Pydantic/FastAPI validation layer.
    # OrderService is never called.

    assert response.status_code == 422


# =========================================================
# 8. CREATE ORDER - EMPTY ITEMS
# =========================================================


def test_create_order_api_rejects_empty_items(
    client: TestClient,
):
    payload = valid_order_payload()

    payload["items"] = []

    response = client.post(
        "/api/v1/orders",
        json=payload,
    )

    assert response.status_code == 422


# =========================================================
# 9. GET ORDER - SUCCESS
# =========================================================


def test_get_order_api_success(
    client: TestClient,
    db_session: Session,
):
    create_standard_data(db_session)

    create_response = client.post(
        "/api/v1/orders",
        json=valid_order_payload(
            idempotency_key="IDEMP-API-GET",
        ),
    )

    assert create_response.status_code == 201

    order_id = create_response.json()["order_id"]

    response = client.get(
        f"/api/v1/orders/{order_id}"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["order_id"] == order_id
    assert data["customer_id"] == "CUST-001"
    assert data["warehouse_id"] == "WH-001"
    assert data["status"] == "CONFIRMED"

    assert len(data["items"]) == 1

    item = data["items"][0]

    assert item["product_id"] == "PROD-001"
    assert item["product_name"] == "Test Product PROD-001"
    assert item["quantity"] == 2

    assert Decimal(
        str(item["unit_price"])
    ) == Decimal("500.00")

    assert Decimal(
        str(item["line_total"])
    ) == Decimal("1000.00")

    assert (
        data["shipping_address"]["city"]
        == "Bengaluru"
    )

    assert Decimal(
        str(data["pricing"]["total_amount"])
    ) == Decimal("1000.00")

    assert len(data["status_history"]) == 1

    assert (
        data["status_history"][0]["status"]
        == "CONFIRMED"
    )

    assert (
        data["status_history"][0]["closed_at"]
        is None
    )


# =========================================================
# 10. GET ORDER - NOT FOUND
# =========================================================


def test_get_order_api_not_found(
    client: TestClient,
):
    response = client.get(
        "/api/v1/orders/ORD-NOT-FOUND"
    )

    assert response.status_code == 404


# =========================================================
# 11. CANCEL ORDER - SUCCESS
# =========================================================


def test_cancel_order_api_success(
    client: TestClient,
    db_session: Session,
):
    inventory = create_standard_data(
        db_session,
        total_quantity=10,
    )

    create_response = client.post(
        "/api/v1/orders",
        json=valid_order_payload(
            quantity=3,
            idempotency_key="IDEMP-API-CANCEL",
        ),
    )

    assert create_response.status_code == 201

    order_id = create_response.json()["order_id"]

    db_session.refresh(inventory)

    assert inventory.reserved_quantity == 3

    response = client.post(
        f"/api/v1/orders/{order_id}/cancel"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["order_id"] == order_id
    assert data["status"] == "CANCELLED"
    assert data["message"] == "Order cancelled successfully"

    db_session.refresh(inventory)

    assert inventory.reserved_quantity == 0


# =========================================================
# 12. CANCEL ORDER - IDEMPOTENT
# =========================================================


def test_cancel_order_api_idempotent(
    client: TestClient,
    db_session: Session,
):
    create_standard_data(db_session)

    create_response = client.post(
        "/api/v1/orders",
        json=valid_order_payload(
            idempotency_key="IDEMP-API-CANCEL-TWICE",
        ),
    )

    assert create_response.status_code == 201

    order_id = create_response.json()["order_id"]

    first = client.post(
        f"/api/v1/orders/{order_id}/cancel"
    )

    assert first.status_code == 200

    second = client.post(
        f"/api/v1/orders/{order_id}/cancel"
    )

    assert second.status_code == 200

    assert second.json()["status"] == "CANCELLED"

    assert (
        second.json()["message"]
        == "Order is already cancelled"
    )


# =========================================================
# 13. CANCEL ORDER - NOT FOUND
# =========================================================


def test_cancel_order_api_not_found(
    client: TestClient,
):
    response = client.post(
        "/api/v1/orders/ORD-NOT-FOUND/cancel"
    )

    assert response.status_code == 404