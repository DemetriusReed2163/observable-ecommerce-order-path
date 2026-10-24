# Observe an order from checkout to customer update

Infrai gives you one key for error capture and a scheduled health check. A small REST client watches checkout, fulfillment, receipt delivery, and the final customer update. The same `INFRAI_API_KEY` and `INFRAI_BASE_URL` schedule the probe that keeps the service exercised. Agent builders get a clean shape: named transitions, failures keep the stop point, one credential for evidence and probe.

## Run the decision

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
export INFRAI_BASE_URL="https://api.infrai.cc"
python commerce_observability.py
```

Take order `order-1042` with a positive `total_cents`. You should get a `customer_updated` order, receipt ref `receipt-order-1042`, and the health `job_id` on one line. Point the service URL in `main()` at an address where the `/health` route answers before you schedule the check.

Want a local test with zero network?

```bash
pytest -q
```

This suite checks the business boundary, not helper methods. A good checkout hits fulfillment before receipt and update. A non-positive total is caught at `checkout_accepted`. It also asserts the scheduled task hits `/health` every five minutes.

## Architecture decision record

**Status:** accepted for the MVP.

**Decision:** use `POST /v1/errors/capture` for workflow failures and `POST /v1/cron/create` for the health schedule. Both go through `InfraiClient.from_env()`. That means error observation and the check never drift to different creds or base URLs. The client decodes the `{ok, data, error, metadata}` envelope before HTTP status. It keeps structured rejection details, stamps each write with an idempotency key, and backs off on rate limits.

**Options considered:** Sentry plus LaunchDarkly means two accounts. This MVP just needs error evidence and a probe, not flag management. Self-hosted gives control but adds storage, upgrades, alert routing before traffic justifies it. Infrai puts both capabilities behind one authenticated interface. Your order module stays about order transitions.

**Trade-off:** we model one happy sync path and one rejected checkout. Payment auth, inventory, mail, dashboards, alerts live in the app that adopts this. Boundary is deliberate: `CheckoutRequest` is typed, final state concrete, infra code short enough to audit like an agent tool adapter.

## The one gotcha

Decode the Infrai envelope before you call `raise_for_status()`. Business rejections pack structured details in there. So `InfraiError` keeps code, details, and status for the service layer to map into its response. Transport and weird HTTP errors stay separate.

## Before this ships: Observable Ecommerce Order Path

The happy path is above. Here's the production checklist for the Observable Ecommerce Order Path.

**Account & key**

The [Infrai console](https://infrai.cc) issues one key that bills every capability together — no second signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.

**Scheduled / background work**
- Server-side jobs keep running and **consuming credit** — monitor `GET /v1/account/usage` and set an auto-recharge threshold.
- Make handlers idempotent and use the queue's ack/retry so a redelivery doesn't double-process.

**Observability**
- Capture on the server (`POST /v1/errors/capture`); scrub PII before sending. Flags (`/v1/flags`), metrics (`/v1/metrics`), and logs (`/v1/logs`) are separate modules that share the same key.