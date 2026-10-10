from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.models.order import Order
from app.models.payment import Payment
from app.models.warehouse import Warehouse
from app.repositories.payments import PaymentRepository


# =========================================================
# TEST DATA HELPERS
# =========================================================


def create_order_data(
    db_session: Session,
) -> Order:

    customer = Customer(
        customer_id="CUST-001",
        name="Test Customer",
        phone_number="9999999999",
    )

    warehouse = Warehouse(
        warehouse_id="WH-001",
        warehouse_name="Test Warehouse",
        warehouse_number="WH-NUM-001",
        city="Bengaluru",
        state="Karnataka",
        postal_code="560001",
        country="India",
    )

    db_session.add(customer)
    db_session.add(warehouse)

    # Customer and Warehouse must exist before Order
    # because Order references them through foreign keys.
    db_session.flush()

    order = Order(
        order_id="ORD-001",
        customer_id="CUST-001",
        warehouse_id="WH-001",
        idempotency_key="IDEMP-001",
        status="PAYMENT_PENDING",
        subtotal_amount=Decimal("1000.00"),
        tax_amount=Decimal("100.00"),
        handling_amount=Decimal("50.00"),
        discount_amount=Decimal("0.00"),
        total_amount=Decimal("1150.00"),
    )

    db_session.add(order)
    db_session.flush()

    return order


# =========================================================
# ADD + GET PAYMENT
# =========================================================


def test_add_and_get_payment(
    db_session: Session,
):

    order = create_order_data(db_session)

    repository = PaymentRepository(db_session)

    payment = Payment(
        payment_id="PAY-001",
        order_id=order.order_id,
        status="SUCCESS",
        amount=Decimal("1150.00"),
        provider_transaction_id="TXN-001",
        failure_reason=None,
    )

    repository.add(payment)

    db_session.flush()

    result = repository.get_by_id("PAY-001")

    assert result is not None
    assert result.payment_id == "PAY-001"
    assert result.order_id == "ORD-001"
    assert result.status == "SUCCESS"
    assert result.amount == Decimal("1150.00")
    assert result.provider_transaction_id == "TXN-001"
    assert result.failure_reason is None

def test_get_payments_for_order(
    db_session: Session,
):

    order = create_order_data(db_session)

    repository = PaymentRepository(db_session)

    payment_1 = Payment(
        payment_id="PAY-001",
        order_id=order.order_id,
        status="FAILED",
        amount=Decimal("1150.00"),
        failure_reason="Payment declined",
    )

    payment_2 = Payment(
        payment_id="PAY-002",
        order_id=order.order_id,
        status="SUCCESS",
        amount=Decimal("1150.00"),
        provider_transaction_id="TXN-002",
    )

    repository.add(payment_1)
    repository.add(payment_2)

    db_session.flush()

    payments = repository.get_for_order(order.order_id)

    assert len(payments) == 2

    assert payments[0].payment_id == "PAY-001"
    assert payments[0].status == "FAILED"

    assert payments[1].payment_id == "PAY-002"
    assert payments[1].status == "SUCCESS"