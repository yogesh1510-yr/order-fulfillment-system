from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.repositories.customers import CustomerRepository


def test_get_customer_by_id(
    db_session: Session,
):
    # Arrange
    customer = Customer(
        customer_id="CUST-TEST-001",
        name="Test Customer",
        phone_number="9999999999",
    )

    db_session.add(customer)
    db_session.flush()

    repository = CustomerRepository(db_session)

    # Act
    result = repository.get_by_id(
        "CUST-TEST-001"
    )

    # Assert
    assert result is not None
    assert result.customer_id == "CUST-TEST-001"
    assert result.name == "Test Customer"


def test_get_customer_by_id_returns_none_when_missing(
    db_session: Session,
):
    repository = CustomerRepository(db_session)

    result = repository.get_by_id(
        "CUSTOMER-DOES-NOT-EXIST"
    )

    assert result is None