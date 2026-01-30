"""
Unified Pagination
==================
Standard pagination implementation for all list endpoints.
"""

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from collections import OrderedDict


class StandardPagination(PageNumberPagination):
    """
    Standard pagination for all list endpoints.
    Returns consistent format with metadata.
    """

    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100
    page_query_param = 'page'

    def get_paginated_response(self, data):
        return Response(
            OrderedDict([
                ('success', True),
                ('status_code', 200),
                ('message', 'Data retrieved successfully'),
                ('data', data),
                ('meta', OrderedDict([
                    ('pagination', OrderedDict([
                        ('count', self.page.paginator.count),
                        ('next', self.get_next_link()),
                        ('previous', self.get_previous_link()),
                        ('page', self.page.number),
                        ('page_size', self.page_size),
                        ('total_pages', self.page.paginator.num_pages),
                    ])),
                ])),
            ])
        )


class LargePagination(PageNumberPagination):
    """For large datasets"""
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 200


class SmallPagination(PageNumberPagination):
    """For small datasets"""
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 50
