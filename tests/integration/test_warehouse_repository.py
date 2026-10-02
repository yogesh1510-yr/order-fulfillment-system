from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.warehouse import Warehouse
from app.repositories.warehouse import WarehouseRepository


def make_warehouse(
    warehouse_id: str,
    warehouse_name: str,
) -> Warehouse:
    return Warehouse(
        warehouse_id=warehouse_id,
        warehouse_name=warehouse_name,
        warehouse_number=f"NUM-{warehouse_id}",
        city="Bengaluru",
        state="Karnataka",
        postal_code="560001",
        country="India",
        latitude=Decimal("12.971599"),
        longitude=Decimal("77.594566"),
    )


def test_get_warehouses_by_ids(
    db_session: Session,
):
    warehouse_1 = make_warehouse(
        "WH-TEST-001",
        "Warehouse 1",
    )

    warehouse_2 = make_warehouse(
        "WH-TEST-002",
        "Warehouse 2",
    )

    db_session.add_all([
        warehouse_1,
        warehouse_2,
    ])
    db_session.flush()

    repository = WarehouseRepository(db_session)

    result = repository.get_by_ids([
        "WH-TEST-001",
        "WH-TEST-002",
    ])

    assert len(result) == 2

    warehouse_ids = {
        warehouse.warehouse_id
        for warehouse in result
    }

    assert warehouse_ids == {
        "WH-TEST-001",
        "WH-TEST-002",
    }


def test_get_warehouses_by_ids_returns_only_existing(
    db_session: Session,
):
    warehouse = make_warehouse(
        "WH-TEST-001",
        "Warehouse 1",
    )

    db_session.add(warehouse)
    db_session.flush()

    repository = WarehouseRepository(db_session)

    result = repository.get_by_ids([
        "WH-TEST-001",
        "WH-NOT-FOUND",
    ])

    assert len(result) == 1
    assert result[0].warehouse_id == "WH-TEST-001"


def test_get_warehouses_by_ids_returns_empty_list_when_none_exist(
    db_session: Session,
):
    repository = WarehouseRepository(db_session)

    result = repository.get_by_ids([
        "WH-NOT-FOUND",
    ])

    assert result == []


def test_get_warehouses_by_ids_with_empty_list(
    db_session: Session,
):
    repository = WarehouseRepository(db_session)

    result = repository.get_by_ids([])

    assert result == []