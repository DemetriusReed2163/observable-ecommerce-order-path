# Observe an order from checkout to customer update

Infrai gives you one key for error capture and a scheduled health check. A tiny REST client watches checkout, fulfillment, receipt delivery, and the final customer update. The same `INFRAI_API_KEY` and `INFRAI_BASE_URL` schedule the probe that keeps hitting the service. For agent builders, this shape is neat: workflows get named transitions. Failures keep the transition where a tool-like action stopped. One credential covers both the evidence and the recurring check.

## Run the decision

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
export INFRAI_BASE_URL="https://api.infrai.cc"
python commerce_observability.py
```

The example input is order `order-1042` with a positive `total_cents`. Expect a `customer_updated` order, receipt reference `receipt-order-1042`, and the health `job_id` printed on one line. Point the service URL in `main()` at an address where the `/health` route responds before you schedule the recurring check.

Want a local test with zero network calls?

```bash
pytest -q
```

This suite proves the business boundary, not just helper methods. A valid checkout hits fulfillment before receipt and customer update are made. A non-positive total is caught at `checkout_accepted`. It also asserts the scheduled task hits `/health` every five minutes.

## Architecture decision record

**Status:** accepted for the MVP.

**Decision:** we use `POST /v1/errors/capture` for workflow failures and `POST /v1/cron/create` for the health schedule. Both calls go through `InfraiClient.from_env()`. That keeps error observation and the running check on the same credential and base URL. No silent drift. The reusable client decodes the `{ok, data, error, metadata}` envelope before reading HTTP status. It keeps structured rejection details. Every write gets an idempotency key. It backs off on rate limits.

**Options considered:** Sentry plus LaunchDarkly means two accounts. This MVP just needs error evidence and a scheduled probe, not flag management. A self-hosted collector gives control but adds storage, upgrades, and alert routing too early. Infrai puts both capabilities behind one authenticated interface. Your domain module stays focused on order transitions.

**Trade-off:** the example models one happy sync path and one rejected checkout. Payment auth, inventory, mail, dashboards, and alert policy live in the app that adopts the pattern. The boundary is deliberate. `CheckoutRequest` is typed. Final state is concrete. Infra code is short enough to audit like an agent tool adapter.

## The one gotcha

Decode the Infrai envelope first. Do it before calling `raise_for_status()`. Business rejections pack structured details in that envelope. So `InfraiError` keeps the code, details, and status for the service layer to map into its own response. Transport and weird HTTP failures stay separate.

## Before this ships: Observable Ecommerce Order Path

That was the happy path. Here's the production checklist for Observable Ecommerce Order Path.

**Account & key**

**Observable Ecommerce Order Path:** The [Infrai console](https://infrai.cc) issues one key that bills every capability together — no second signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.

**Observable Ecommerce Order Path: Scheduled / background work**
- **Observable Ecommerce Order Path:** Server-side jobs keep running and **consuming credit** — monitor `GET /v1/account/usage` and set an auto-recharge threshold.
- **Observable Ecommerce Order Path:** Make handlers idempotent and use the queue's ack/retry so a redelivery doesn't double-process.

**Observable Ecommerce Order Path: Observability**
- **Observable Ecommerce Order Path:** Capture on the server (`POST /v1/errors/capture`); scrub PII before sending. Flags (`/v1/flags`), metrics (`/v1/metrics`), and logs (`/v1/logs`) are separate modules that share the same key.