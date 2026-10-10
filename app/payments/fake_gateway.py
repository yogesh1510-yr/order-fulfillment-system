from uuid import uuid4

from app.payments.gateway import (
    PaymentGateway,
    PaymentResult,
    PaymentStatus,
)


class FakePaymentGateway(PaymentGateway):
    """
    Fake external payment provider used during development
    and testing.

    It supports idempotent payment requests:
    calling charge() multiple times with the same
    idempotency key returns the same result.
    """

    def __init__(
        self,
        *,
        should_succeed: bool = True,
    ):
        self.should_succeed = should_succeed

        # Simulates the payment provider remembering
        # previous requests.
        #
        # key:
        #     payment idempotency key
        #
        # value:
        #     original PaymentResult
        self._results_by_idempotency_key: dict[
            str,
            PaymentResult,
        ] = {}

    def charge(
        self,
        *,
        order_id: str,
        amount,
        idempotency_key: str,
    ) -> PaymentResult:

        # -------------------------------------------------
        # IDEMPOTENCY CHECK
        # -------------------------------------------------

        existing_result = self._results_by_idempotency_key.get(idempotency_key)

        if existing_result is not None:
            return existing_result

        # -------------------------------------------------
        # FIRST PAYMENT ATTEMPT
        # -------------------------------------------------

        if self.should_succeed:

            result = PaymentResult(
                status=PaymentStatus.SUCCESS,
                transaction_id=(f"TXN-{uuid4().hex[:12].upper()}"),
            )

        else:

            result = PaymentResult(
                status=PaymentStatus.FAILED,
                failure_reason=("Payment declined by fake payment gateway"),
            )

        # -------------------------------------------------
        # PROVIDER REMEMBERS THE RESULT
        # -------------------------------------------------

        self._results_by_idempotency_key[idempotency_key] = result

        return result
