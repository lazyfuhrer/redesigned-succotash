from rest_framework import pagination
from rest_framework.response import Response


class CustomPagination(pagination.PageNumberPagination):
    page_size_query_param = 'page_size'

    def get_paginated_response(self, data):
        return Response({
            'pagination': {
                'next': True if self.get_next_link() else False,
                'previous': True if self.get_previous_link() else False,
                'count': self.page.paginator.count,
                'page_size': self.page.paginator.per_page,
                'current_page': self.page.number,
                'pages': self.page.paginator.num_pages
            },
            'results': data
        })
