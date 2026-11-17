from dropline.api import exception_handler
from dropline.errors import ConflictError, DomainError, NotFoundError


def test_conflict_error_maps_to_409_with_its_code_and_message():
    class OutOfStockError(ConflictError):
        code = "out_of_stock"
        default_message = "Not enough stock."

    response = exception_handler(OutOfStockError(), context={})

    assert response.status_code == 409
    assert response.data == {"detail": "Not enough stock.", "code": "out_of_stock"}


def test_not_found_error_maps_to_404():
    response = exception_handler(NotFoundError("No such thing."), context={})

    assert response.status_code == 404
    assert response.data == {"detail": "No such thing.", "code": "not_found"}


def test_domain_error_without_a_category_is_left_unhandled():
    assert exception_handler(DomainError(), context={}) is None
