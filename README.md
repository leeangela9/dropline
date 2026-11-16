# Dropline

A small dropship order platform: a REST API that routes retailer orders to suppliers and carries acknowledgments, shipment notices, and invoices back.

Dropline is also an experiment in **AI-assisted engineering with guardrails**. The code is written together with Claude Code, and the repository includes the harness that keeps that work trustworthy: project instructions, hooks, skills, subagents, and CI gates.

> **Status: early.** The repository currently holds the design; the application code lands phase by phase. See the [roadmap](#roadmap) for what exists so far.

## The domain

In dropshipping, a retailer sells a product but the supplier ships it straight to the customer. A platform in the middle passes documents between the two. Dropline uses simplified JSON versions of the four core EDI (X12) documents:

| Doc | Name | Direction | Meaning |
|---|---|---|---|
| 850 | Purchase Order | Retailer → Supplier | Ship these items to this customer |
| 855 | PO Acknowledgment | Supplier → Retailer | Accepted, rejected, or partially accepted |
| 856 | Advance Ship Notice | Supplier → Retailer | Shipped: carrier, tracking, which lines |
| 810 | Invoice | Supplier → Retailer | Bill for what was shipped |

Each order moves through a state machine:

```
received → acknowledged → partially_shipped → shipped → invoiced → closed
        ↘ rejected                                   ↘ returned
        ↘ cancelled (only before shipped)
```

The problems worth solving here are the ones real integrations hit:

- **Duplicate messages.** Inbound documents are idempotent on `(partner, idempotency_key)`, enforced by a database constraint.
- **Partial shipments.** An order can ship across several shipments, and never more than was ordered.
- **Out-of-order messages.** A ship notice can arrive before its acknowledgment.
- **Inconsistent partner data.** Suppliers name fields and format dates differently, so a mapping layer normalizes them.
- **Money.** All amounts are integer cents. No floats.

## Stack

- Python 3.12, Django 5, Django REST Framework
- Postgres 16
- pytest, pytest-django, factory_boy, coverage
- ruff for lint and format
- drf-spectacular for the OpenAPI schema
- Docker Compose and GitHub Actions

## Architecture

```
dropline/
├── apps/
│   ├── partners/      Retailer, Supplier, credentials
│   ├── catalog/       Product, SupplierSKU, Inventory
│   ├── orders/        Order, OrderLine, state machine
│   ├── fulfillment/   Shipment, ShipmentLine
│   ├── invoicing/     Invoice, InvoiceLine
│   └── connectors/    Inbound and outbound EDI-style documents, webhooks
├── legacy/            An inherited parser, refactored behind characterization tests
├── docs/
│   ├── adr/           Decision records
│   ├── runbooks/      Operational runbooks
│   └── incidents/     Postmortems
├── .claude/           Agent settings, hooks, skills, subagents
└── .github/           CI workflows and PR template
```

One layering rule applies everywhere:

```
views (DRF ViewSets)  →  services (business logic, transactions)  →  models
```

- Serializers validate input and output shape. They don't change state.
- Business logic lives only in `apps/<app>/services/`.
- Every query on retailer data is scoped to the authenticated retailer.
- Changes that touch multiple rows run inside `transaction.atomic()`.
- Order status changes go through the state machine service, never by assigning `order.status` directly.

`apps/orders` is the reference implementation that the other apps copy.

## Roadmap

### Phase 0: Skeleton

- [ ] Django project, Docker Compose, Postgres, `/healthz`, settings from environment variables
- [ ] Partner and order models
- [ ] Reference endpoint: `POST /api/orders` and `GET /api/orders/{id}`
- [ ] API key auth per retailer, with retailer-scoped access
- [ ] CI for lint and tests

### Phase 1: Core features

- [ ] Order list with filters and cursor pagination
- [ ] Order state machine; invalid transitions return HTTP 409
- [ ] Order cancellation, allowed only before shipping
- [ ] Catalog: products and supplier SKUs
- [ ] Inventory check on order creation
- [ ] Shipments, including partial shipments
- [ ] Invoicing from shipped quantities
- [ ] Audit log of status changes at `GET /api/orders/{id}/history`

### Phase 2: Connectors

- [ ] Idempotent inbound 850 at `POST /api/inbound/850`
- [ ] Inbound 855 and 856, including out-of-order handling
- [ ] CSV supplier inventory import with row-level error reporting
- [ ] Outbound webhooks with HMAC signatures and retries with exponential backoff
- [ ] Partner-specific field mapping

### Phase 3: Legacy code and operations

- [ ] Characterization tests for an inherited X12 parser, then an incremental refactor into the connectors layer
- [ ] Debugging exercises worked from symptoms only, each starting with a failing test
- [ ] Incident drills with postmortems and runbooks

### Phase 4: Polish

- [ ] Structured logging with request IDs propagated into webhook calls
- [ ] Metrics endpoint
- [ ] Deploy from CI on merge to `main`

## Development

These commands apply once the Phase 0 skeleton is in place.

Start the app and database:

```bash
docker compose up
```

Run the tests:

```bash
docker compose exec web pytest -q
```

Lint and format:

```bash
ruff check . && ruff format .
```

## How the code gets written

Each feature is one ticket and one pull request:

1. Write the ticket with requirements, out-of-scope items, and exact verification steps.
2. Explore and plan before editing.
3. Write failing tests first for non-trivial logic.
4. Implement until green.
5. Review the diff by hand, then again with an independent reviewer agent in a fresh context.
6. Open a PR with pasted evidence of verification. CI must pass.

AI-generated code is treated as untrusted until it is verified. The harness makes that verification systematic rather than a matter of attention:

| Layer | What it does |
|---|---|
| `CLAUDE.md` | Project conventions, commands, and architecture rules |
| Hooks | Block edits to applied migrations, CI config, and the harness itself; block destructive shell commands; run lint after each edit and tests before the agent stops |
| Skills | Repeatable procedures such as adding an endpoint, adding a partner connector, triaging a bug, or writing a runbook |
| Subagents | Scoped roles: code reviewer, security reviewer, test author, read-only explorer, incident investigator |
| CI gates | Lint, tests with a coverage floor, missing-migration check, OpenAPI contract diff, dependency and static security scans |

The harness grows only when a real failure calls for it. [HARNESS_LOG.md](HARNESS_LOG.md) records each agent mistake, what caught it, the root cause, and the fix made to the harness so it doesn't recur.

Every pull request also includes an **AI usage** section: what was generated, what changed after review, and what was rejected and why.
