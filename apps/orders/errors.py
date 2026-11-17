from dropline.errors import ConflictError, NotFoundError


class OrderNotFoundError(NotFoundError):
    code = "order_not_found"
    default_message = "Order not found."


class DuplicateOrderError(ConflictError):
    code = "duplicate_order"
    default_message = "An order with this external_po_number already exists."
