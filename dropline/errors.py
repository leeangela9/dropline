"""Domain errors raised by services.

Services know nothing about HTTP. `dropline.api.exception_handler` is the one place that
turns these into responses, so a new error only needs a subclass here or in its app.
"""


class DomainError(Exception):
    """A business rule was broken. Subclass one of the categories below, not this."""

    code = "domain_error"
    default_message = "The request could not be completed."

    def __init__(self, message: str | None = None):
        self.message = message or self.default_message
        super().__init__(self.message)


class NotFoundError(DomainError):
    """The object does not exist, or the caller is not allowed to know that it does."""

    code = "not_found"
    default_message = "Not found."


class ConflictError(DomainError):
    """The request is well-formed but conflicts with the current state of the data."""

    code = "conflict"
    default_message = "The request conflicts with the current state."
