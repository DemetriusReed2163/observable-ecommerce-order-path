from commerce_observability import CheckoutRequest, OrderStage, process_order, schedule_health_check


class RecordingInfrai:
    def __init__(self) -> None:
        self.captured_exceptions: list[tuple[dict[str, object], str]] = []
        self.health_calls: list[tuple[str, str]] = []

    def capture_error(self, exception: dict[str, object], event_id: str) -> dict[str, object]:
        self.captured_exceptions.append((exception, event_id))
        return {}

    def create_health_check(self, cron_expr: str, task: str) -> dict[str, object]:
        self.health_calls.append((cron_expr, task))
        return {"job_id": "job-health-1"}


def test_completed_fulfillment_produces_receipt_and_customer_update() -> None:
    infrai = RecordingInfrai()

    result = process_order(CheckoutRequest("order-7", "ada@example.com", 4500), infrai)

    assert result.stage is OrderStage.CUSTOMER_UPDATED
    assert result.receipt_reference == "receipt-order-7"
    assert infrai.captured_exceptions == []


def test_rejected_checkout_is_captured_at_its_business_stage() -> None:
    infrai = RecordingInfrai()

    try:
        process_order(CheckoutRequest("order-8", "ada@example.com", 0), infrai)
    except ValueError:
        pass
    else:
        raise AssertionError("invalid checkout must be rejected")

    exception, event_id = infrai.captured_exceptions[0]
    assert exception["stage"] == "checkout_accepted"
    assert event_id == "order-order-8-checkout_accepted"


def test_health_check_targets_the_service_endpoint() -> None:
    infrai = RecordingInfrai()

    job_id = schedule_health_check(infrai, "https://shop.example.com")  # type: ignore[arg-type]

    assert job_id == "job-health-1"
    assert infrai.health_calls == [("*/5 * * * *", "https://shop.example.com/health")]
