"""Run an observable checkout-to-receipt workflow and schedule its health check."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from infrai_client import InfraiClient


class OrderStage(str, Enum):
    CHECKOUT_ACCEPTED = "checkout_accepted"
    FULFILLMENT_COMPLETE = "fulfillment_complete"
    RECEIPT_SENT = "receipt_sent"
    CUSTOMER_UPDATED = "customer_updated"


@dataclass(frozen=True)
class CheckoutRequest:
    order_id: str
    customer_email: str
    total_cents: int


@dataclass(frozen=True)
class OrderResult:
    order_id: str
    stage: OrderStage
    receipt_reference: str


class ErrorSink(Protocol):
    def capture_error(self, exception: dict[str, object], event_id: str) -> dict[str, object]:
        """Record a workflow exception."""


def process_order(request: CheckoutRequest, error_sink: ErrorSink) -> OrderResult:
    """Move a paid order through fulfillment, receipt, and customer update."""
    stage = OrderStage.CHECKOUT_ACCEPTED
    try:
        if request.total_cents <= 0:
            raise ValueError("checkout total must be positive")

        stage = OrderStage.FULFILLMENT_COMPLETE
        receipt_reference = f"receipt-{request.order_id}"
        stage = OrderStage.RECEIPT_SENT

        # The customer update follows the receipt, making the visible decision explicit.
        stage = OrderStage.CUSTOMER_UPDATED
        return OrderResult(request.order_id, stage, receipt_reference)
    except ValueError as exc:
        error_sink.capture_error(
            exception={
                "type": type(exc).__name__,
                "message": str(exc),
                "order_id": request.order_id,
                "stage": stage.value,
            },
            event_id=f"order-{request.order_id}-{stage.value}",
        )
        raise


def schedule_health_check(client: InfraiClient, service_url: str) -> str:
    result = client.create_health_check("*/5 * * * *", f"{service_url}/health")
    return str(result["job_id"])


def main() -> None:
    client = InfraiClient.from_env()
    result = process_order(
        CheckoutRequest(
            order_id="order-1042",
            customer_email="buyer@example.com",
            total_cents=12900,
        ),
        client,
    )
    job_id = schedule_health_check(client, "https://shop.example.com")
    print(
        f"{result.order_id}: {result.stage.value}; "
        f"{result.receipt_reference}; health job {job_id}"
    )


if __name__ == "__main__":
    main()
