from rest_framework import status, viewsets
from rest_framework.request import Request
from rest_framework.response import Response

from apps.orders.serializers import OrderCreateSerializer, OrderSerializer
from apps.orders.services import orders
from apps.partners.api import retailer_from_request


class OrderViewSet(viewsets.ViewSet):
    """Each action is: resolve the retailer, parse, call the service, serialize."""

    # Non-numeric ids do not match the route, so they are a 404 like any unknown id.
    lookup_value_regex = r"\d+"

    def create(self, request: Request) -> Response:
        retailer = retailer_from_request(request)
        serializer = OrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = orders.create_order(retailer=retailer, **serializer.validated_data)
        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)

    def retrieve(self, request: Request, pk: str) -> Response:
        retailer = retailer_from_request(request)
        order = orders.get_order(retailer=retailer, order_id=int(pk))
        return Response(OrderSerializer(order).data)
