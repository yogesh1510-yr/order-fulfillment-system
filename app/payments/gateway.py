from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum


class PaymentStatus(str, Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


@dataclass(frozen=True)
class PaymentResult:
    status: PaymentStatus
    transaction_id: str | None = None
    failure_reason: str | None = None


class PaymentGateway(ABC):

    @abstractmethod
    def charge(
        self,
        *,
        order_id: str,
        amount: Decimal,
        idempotency_key: str,
    ) -> PaymentResult:
        raise NotImplementedError
