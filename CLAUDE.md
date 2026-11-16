# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Current state

Phase 0 skeleton (T0.1) exists: Django project in `dropline/`, an empty `apps/` package, Docker Compose (`web` + Postgres 16 `db`), `GET /healthz`, pytest and ruff config in `pyproject.toml`. No models, auth, or `/api/` endpoints yet. Sections below that describe apps, services, and domain rules are still the intended design. Verify a file or command exists before relying on it, and update this file as the code lands.

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
- Endpoint tests cover the happy path, validation error (400), wrong retailer (404), and invalid state (409) where relevant.

## Workflow

- One ticket per branch and PR. Branch names look like `feat/T1.6-partial-shipments`.
- Never edit an applied migration; add a new one.
- Design decisions with real alternatives get a short ADR in `docs/adr/`.
- When an agent mistake is caught in review, it is recorded in `HARNESS_LOG.md` along with the harness fix.
