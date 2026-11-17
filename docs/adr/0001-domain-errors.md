# ADR 0001: Domain errors and how they become HTTP responses

Status: accepted (T0.3)

## Context

Services hold the business rules, and some rules fail in ways the caller must hear about: an
order that does not exist, a PO number that is already taken, and later an invalid status
transition (T1.2). Views are meant to stay thin, so the translation from "rule broken" to an
HTTP status needs one home that every endpoint shares.

Duplicate PO numbers add a second question: who decides that a PO number is a duplicate.

## Decision

1. Services raise subclasses of `DomainError` (`dropline/errors.py`). There are two categories
   so far: `NotFoundError` and `ConflictError`. Each app defines its own specific errors in
   `apps/<app>/errors.py`, with a stable `code` and a default message.
2. `dropline.api.exception_handler`, registered as DRF's `EXCEPTION_HANDLER`, maps a category
   to a status (404, 409) and renders `{"detail": ..., "code": ...}`. Views never catch domain
   errors. A `DomainError` outside a mapped category is left unhandled and surfaces as a 500.
3. Input validation stays with serializers and DRF's standard 400 body of field errors.
4. Uniqueness is decided by the database. The service inserts inside `transaction.atomic()`,
   catches `IntegrityError` outside that block, and converts it to a domain error only when
   `dropline.db.violated_constraint()` names the expected constraint. Any other integrity
   error is re-raised.

## Alternatives considered

- **Raise DRF exceptions from services.** Less code, but services would depend on the HTTP
  layer and could not be reused from management commands or background jobs.
- **Catch errors in each view.** Explicit, but every view repeats the mapping and one of them
  will eventually get it wrong.
- **Check for an existing order before inserting.** Reads more simply, but two concurrent
  requests can both pass the check. The constraint would still stop the second insert, which
  would then surface as a 500 instead of a 409.
- **Put the HTTP status on the error class.** One less table, but it puts HTTP knowledge back
  into the domain layer.

## Consequences

- A new kind of failure is a new error subclass; a new category is one line in the handler.
- Constraint names are part of the contract between a model and its service, so they are
  shared as constants (`ORDER_UNIQUE_PO_CONSTRAINT`) instead of repeated as strings.
- `violated_constraint()` relies on the Postgres driver reporting the constraint name. That
  is acceptable because Postgres is the only supported database.
