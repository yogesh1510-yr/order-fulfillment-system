from decimal import Decimal

from app.payments.fake_gateway import FakePaymentGateway
from app.payments.gateway import PaymentStatus


def test_fake_payment_gateway_success():

    gateway = FakePaymentGateway(
        should_succeed=True,
    )

    result = gateway.charge(
        order_id="ORD-TEST-001",
        amount=Decimal("1000.00"),
        idempotency_key="PAYMENT-ORD-TEST-001",
    )

    assert result.status == PaymentStatus.SUCCESS
    assert result.transaction_id is not None
    assert result.transaction_id.startswith("TXN-")
    assert result.failure_reason is None


def test_fake_payment_gateway_failure():

    gateway = FakePaymentGateway(
        should_succeed=False,
    )

    result = gateway.charge(
        order_id="ORD-TEST-002",
        amount=Decimal("1000.00"),
        idempotency_key="PAYMENT-ORD-TEST-002",
    )

    assert result.status == PaymentStatus.FAILED
    assert result.transaction_id is None
    assert result.failure_reason is not None

def test_fake_payment_gateway_is_idempotent():

    gateway = FakePaymentGateway(
        should_succeed=True,
    )

    first_result = gateway.charge(
        order_id="ORD-TEST-003",
        amount=Decimal("1000.00"),
        idempotency_key="PAYMENT-ORD-TEST-003",
    )

    second_result = gateway.charge(
        order_id="ORD-TEST-003",
        amount=Decimal("1000.00"),
        idempotency_key="PAYMENT-ORD-TEST-003",
    )

    assert first_result.status == PaymentStatus.SUCCESS
    assert second_result.status == PaymentStatus.SUCCESS

    assert (
        first_result.transaction_id
        == second_result.transaction_id
    )
