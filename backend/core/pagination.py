"""Cursor pagination with the docs/03 §3 envelope: {results, next, prev}."""

from rest_framework.pagination import CursorPagination
from rest_framework.response import Response


class DefaultCursorPagination(CursorPagination):
    page_size = 50
    max_page_size = 200
    page_size_query_param = "page_size"
    ordering = "-created_at"

    def get_paginated_response(self, data: list) -> Response:
        return Response(
            {
                "results": data,
                "next": self.get_next_link(),
                "prev": self.get_previous_link(),
            }
        )
