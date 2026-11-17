# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Current state

Phase 0 skeleton (T0.1) exists: Django project in `dropline/`, Docker Compose (`web` + Postgres 16 `db`), `GET /healthz`, Django admin at `/admin/`, pytest and ruff config in `pyproject.toml`. T0.2 added the models: `apps/partners` (`Retailer`, `Supplier`) and `apps/orders` (`Order`, `OrderLine`, `OrderStatus`). T0.3 added the reference endpoint in `apps/orders`: `POST /api/orders` and `GET /api/orders/{id}`, with serializers, `services/orders.py`, a ViewSet, factories, and tests. There is no real auth yet: `retailer_from_request()` in `apps/partners/api.py` trusts a temporary `X-Retailer-Id` header until T0.4. No status transitions, catalog, fulfillment, invoicing, or connectors yet. Sections below that describe those are still the intended design. Verify a file or command exists before relying on it, and update this file as the code lands.

All config comes from env vars via helpers in `dropline/env.py`; a missing required var raises `ImproperlyConfigured` at startup. Dependencies are pinned in `requirements.txt` (runtime) and `requirements-dev.txt` (test/lint); pin transitive deps too. Project-level tests live in `tests/`; app tests go in `apps/<app>/tests/`.

`dropline-practice-project.md` is a private, git-ignored planning doc with the ticket backlog (IDs like `T0.3`, `T1.6`), the data model, and the harness plan. Read it for ticket details, but never copy its contents into committed files or make it tracked.

## What Dropline is

A dropship order platform API: Django 5 + Django REST Framework on Postgres 16, Python 3.12. It routes retailer orders to suppliers and carries simplified-JSON versions of EDI documents back: 850 (purchase order), 855 (acknowledgment), 856 (ship notice), 810 (invoice).

## Commands

Run everything in the container; the host Python is not 3.12.

- First run: `cp .env.example .env`
- Run: `docker compose up`
- Test: `docker compose exec web pytest -q`
- Single test file: `docker compose exec web pytest tests/test_healthz.py -q`
- Lint and format: `docker compose exec web sh -c 'ruff check . && ruff format .'`
- Migrations: `docker compose exec web python manage.py makemigrations <app>`
- OpenAPI schema check (planned, needs drf-spectacular): `python manage.py spectacular --file <path> --validate`

## Architecture

Django apps live under `apps/`: `partners`, `catalog`, `orders`, `fulfillment`, `invoicing`, `connectors`. Project settings live in `dropline/`.

Strict layering, the same in every app:

```
views (DRF ViewSets)  →  services (business logic, transactions)  →  models
```

- Business logic lives only in `apps/<app>/services/`. Views stay thin.
- Serializers validate input and output shape. They never change state.
- Every query on retailer data is scoped by `request.retailer`. A retailer requesting another retailer's object gets a 404.
- Multi-row state changes run inside `transaction.atomic()`.
- `apps/orders` is the reference implementation (ticket T0.3). New endpoints copy its structure: serializer, service, view, URL, factory, tests.
- Views get the caller from `retailer_from_request(request)` and pass it to the service as an argument. Services never read the request.
- Services report broken rules by raising a `DomainError` subclass from `apps/<app>/errors.py` (`NotFoundError` → 404, `ConflictError` → 409). `dropline.api.exception_handler` does the mapping; views do not catch these. See `docs/adr/0001-domain-errors.md`.
- Uniqueness is decided by the database: insert, then turn the specific `IntegrityError` into a domain error using `dropline.db.violated_constraint()`. No check-then-insert.
- Input serializers are plain `Serializer` classes with no `save()`; output serializers are read-only.

## Domain rules

- Money is always integer cents (`*_cents` fields). Never floats.
- Order status is a `TextChoices` enum. Status changes go through `order_state.transition()` in `apps/orders/services/order_state.py`, never `order.status = ...`. Invalid transitions raise a domain error that maps to HTTP 409.
- State machine: `received → acknowledged → partially_shipped → shipped → invoiced → closed`, with `rejected` from `received`, `cancelled` only before `shipped`, and `returned` after `shipped`.
- Inbound documents are idempotent on `(partner, idempotency_key)`, enforced by a database unique constraint rather than an in-memory check. A repeated key returns the original result.
- Orders are unique on `(retailer, external_po_number)`.
- A shipment can never ship more than was ordered; partial shipments are normal.
- Partner-specific field differences go through the mapping layer in `apps/connectors`, not `if supplier == ...` branches.

## Testing

- pytest + pytest-django, with factory_boy factories in `apps/<app>/tests/factories.py`.
- Build test data with the factories, not `Model.objects.create()`. API tests use the `api_client` fixture from the root `conftest.py`.
- Endpoint tests cover the happy path, validation error (400), wrong retailer (404), and invalid state (409) where relevant.

## Workflow

- One ticket per branch and PR. Branch names look like `feat/T1.6-partial-shipments`.
- Never edit an applied migration; add a new one.
- After implementing or changing a feature, run the `test-writer` subagent (`.claude/agents/test-writer.md`), then run the tests it wrote. It does not fix production code; a failing test it wrote is either a real bug or a wrong test, so decide which before changing anything.
- Design decisions with real alternatives get a short ADR in `docs/adr/`.
- When an agent mistake is caught in review, it is recorded in `HARNESS_LOG.md` along with the harness fix.
