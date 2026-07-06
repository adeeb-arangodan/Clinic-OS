from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthView(APIView):
    authentication_classes = []
    permission_classes = []

    @extend_schema(responses=OpenApiResponse(description="Service is up"))
    def get(self, request: Request) -> Response:
        return Response({"status": "ok"})
