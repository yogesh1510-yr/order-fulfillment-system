from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.product import Product
from app.repositories.products import ProductRepository


def test_get_products_by_ids(
    db_session: Session,
):
    # Arrange
    product_1 = Product(
        product_id="PROD-TEST-001",
        sku="SKU-001",
        product_name="Test Product 1",
        size="M",
        mrp=Decimal("499.00"),
    )

    product_2 = Product(
        product_id="PROD-TEST-002",
        sku="SKU-002",
        product_name="Test Product 2",
        size="L",
        mrp=Decimal("799.00"),
    )

    db_session.add_all([
        product_1,
        product_2,
    ])

    db_session.flush()

    repository = ProductRepository(db_session)

    # Act
    result = repository.get_by_ids([
        "PROD-TEST-001",
        "PROD-TEST-002",
    ])

    # Assert
    assert len(result) == 2

    product_ids = {
        product.product_id
        for product in result
    }

    assert product_ids == {
        "PROD-TEST-001",
        "PROD-TEST-002",
    }


def test_get_products_by_ids_returns_only_existing_products(
    db_session: Session,
):
    product = Product(
        product_id="PROD-TEST-001",
        sku="SKU-001",
        product_name="Test Product",
        size="M",
        mrp=Decimal("499.00"),
    )

    db_session.add(product)
    db_session.flush()

    repository = ProductRepository(db_session)

    result = repository.get_by_ids([
        "PROD-TEST-001",
        "PROD-DOES-NOT-EXIST",
    ])

    assert len(result) == 1
    assert result[0].product_id == "PROD-TEST-001"


def test_get_products_by_ids_returns_empty_list_when_none_exist(
    db_session: Session,
):
    repository = ProductRepository(db_session)

    result = repository.get_by_ids([
        "PROD-DOES-NOT-EXIST",
    ])

    assert result == []


def test_get_products_by_ids_with_empty_list(
    db_session: Session,
):
    repository = ProductRepository(db_session)

    result = repository.get_by_ids([])

    assert result == []