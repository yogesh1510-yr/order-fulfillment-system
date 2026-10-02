from app.models.inventory import Inventory


def make_inventory(
    total_quantity: int = 100,
    reserved_quantity: int = 30,
) -> Inventory:
    return Inventory(
        inventory_id="INV-001",
        product_id="PROD-001",
        warehouse_id="WH-001",
        total_quantity=total_quantity,
        reserved_quantity=reserved_quantity,
    )


def test_available_quantity():
    inventory = make_inventory(
        total_quantity=100,
        reserved_quantity=30,
    )

    assert inventory.available_quantity == 70


def test_available_quantity_when_nothing_reserved():
    inventory = make_inventory(
        total_quantity=100,
        reserved_quantity=0,
    )

    assert inventory.available_quantity == 100


def test_available_quantity_when_everything_reserved():
    inventory = make_inventory(
        total_quantity=100,
        reserved_quantity=100,
    )

    assert inventory.available_quantity == 0


def test_can_fulfill_when_stock_is_available():
    inventory = make_inventory(
        total_quantity=100,
        reserved_quantity=30,
    )

    assert inventory.can_fulfill(50) is True


def test_cannot_fulfill_when_stock_is_insufficient():
    inventory = make_inventory(
        total_quantity=100,
        reserved_quantity=30,
    )

    assert inventory.can_fulfill(80) is False


def test_can_fulfill_exact_available_quantity():
    inventory = make_inventory(
        total_quantity=100,
        reserved_quantity=30,
    )

    assert inventory.can_fulfill(70) is True


def test_cannot_fulfill_when_no_stock_available():
    inventory = make_inventory(
        total_quantity=100,
        reserved_quantity=100,
    )

    assert inventory.can_fulfill(1) is False