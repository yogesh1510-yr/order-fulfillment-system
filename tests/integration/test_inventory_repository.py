from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.inventory import Inventory
from app.models.product import Product
from app.models.warehouse import Warehouse
from app.repositories.inventory import InventoryRepository


def create_product(
    db_session: Session,
    product_id: str,
) -> Product:
    product = Product(
        product_id=product_id,
        sku=f"SKU-{product_id}",
        product_name=f"Product {product_id}",
        size="M",
        mrp=Decimal("500.00"),
    )

    db_session.add(product)

    return product


def create_warehouse(
    db_session: Session,
    warehouse_id: str,
) -> Warehouse:
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

    return warehouse


def create_inventory(
    db_session: Session,
    inventory_id: str,
    product_id: str,
    warehouse_id: str,
    total_quantity: int,
    reserved_quantity: int = 0,
) -> Inventory:
    inventory = Inventory(
        inventory_id=inventory_id,
        product_id=product_id,
        warehouse_id=warehouse_id,
        total_quantity=total_quantity,
        reserved_quantity=reserved_quantity,
    )

    db_session.add(inventory)

    return inventory


def test_get_inventory_for_products(
    db_session: Session,
):
    create_product(db_session, "PROD-001")
    create_product(db_session, "PROD-002")

    create_warehouse(db_session, "WH-001")

    create_inventory(
        db_session,
        "INV-001",
        "PROD-001",
        "WH-001",
        100,
    )

    create_inventory(
        db_session,
        "INV-002",
        "PROD-002",
        "WH-001",
        50,
    )

    db_session.flush()

    repository = InventoryRepository(db_session)

    result = repository.get_for_products([
        "PROD-001",
        "PROD-002",
    ])

    assert len(result) == 2

    product_ids = {
        inventory.product_id
        for inventory in result
    }

    assert product_ids == {
        "PROD-001",
        "PROD-002",
    }


def test_get_inventory_for_products_returns_empty_list(
    db_session: Session,
):
    repository = InventoryRepository(db_session)

    result = repository.get_for_products([
        "PROD-NOT-FOUND",
    ])

    assert result == []


def test_get_inventory_for_products_for_update(
    db_session: Session,
):
    create_product(db_session, "PROD-001")
    create_warehouse(db_session, "WH-001")

    create_inventory(
        db_session,
        "INV-001",
        "PROD-001",
        "WH-001",
        100,
        20,
    )

    db_session.flush()

    repository = InventoryRepository(db_session)

    result = repository.get_for_products_for_update([
        "PROD-001",
    ])

    assert len(result) == 1

    inventory = result[0]

    assert inventory.product_id == "PROD-001"
    assert inventory.total_quantity == 100
    assert inventory.reserved_quantity == 20
    assert inventory.available_quantity == 80


def test_get_inventory_for_order_cancellation(
    db_session: Session,
):
    create_product(db_session, "PROD-001")

    create_warehouse(db_session, "WH-001")
    create_warehouse(db_session, "WH-002")

    create_inventory(
        db_session,
        "INV-001",
        "PROD-001",
        "WH-001",
        100,
        20,
    )

    create_inventory(
        db_session,
        "INV-002",
        "PROD-001",
        "WH-002",
        100,
        30,
    )

    db_session.flush()

    repository = InventoryRepository(db_session)

    result = repository.get_for_order_cancellation(
        warehouse_id="WH-001",
        product_ids=["PROD-001"],
    )

    assert len(result) == 1

    inventory = result[0]

    assert inventory.warehouse_id == "WH-001"
    assert inventory.product_id == "PROD-001"
    assert inventory.reserved_quantity == 20