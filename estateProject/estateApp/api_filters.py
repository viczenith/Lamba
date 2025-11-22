"""
Advanced filtering for multi-tenant API.
Provides company-aware filtering and search capabilities.
"""
import logging
from django_filters import rest_framework as filters
from django.db.models import Q
from rest_framework import serializers

logger = logging.getLogger(__name__)


class CompanyFilterBackend(filters.BaseInFilter, filters.CharFilter):
    """
    Filter results by company.
    Can use comma-separated IDs or single ID.
    """
    pass


class CompanyAwareFilterBackend:
    """
    Base filter backend that automatically filters by company.
    """
    
    def filter_queryset(self, request, queryset, view):
        """Filter queryset by company"""
        
        company = getattr(request, 'company', None)
        if not company:
            return queryset
        
        # Filter by company
        if 'company' in [f.name for f in queryset.model._meta.fields]:
            return queryset.filter(company=company)
        
        return queryset


class DateRangeFilterBackend:
    """
    Filter by date range.
    Query params: start_date, end_date (format: YYYY-MM-DD)
    """
    
    date_field = 'created_at'
    
    def filter_queryset(self, request, queryset, view):
        """Filter by date range"""
        
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if start_date:
            filter_kwargs = {f'{self.date_field}__gte': start_date}
            queryset = queryset.filter(**filter_kwargs)
        
        if end_date:
            filter_kwargs = {f'{self.date_field}__lte': end_date}
            queryset = queryset.filter(**filter_kwargs)
        
        return queryset


class StatusFilterBackend:
    """
    Filter by status field.
    Query param: status
    """
    
    status_field = 'status'
    
    def filter_queryset(self, request, queryset, view):
        """Filter by status"""
        
        status = request.query_params.get('status')
        
        if status:
            filter_kwargs = {self.status_field: status}
            queryset = queryset.filter(**filter_kwargs)
        
        return queryset


class SearchFilterBackend:
    """
    Full-text search across multiple fields.
    Query param: search
    """
    
    search_fields = ['name', 'description']
    
    def filter_queryset(self, request, queryset, view):
        """Apply search filter"""
        
        search_query = request.query_params.get('search')
        
        if not search_query:
            return queryset
        
        # Build Q object for OR queries
        q_object = Q()
        
        for field in self.search_fields:
            q_object |= Q(**{f'{field}__icontains': search_query})
        
        return queryset.filter(q_object)


class OrderingFilterBackend:
    """
    Order results by field(s).
    Query param: ordering (e.g., "created_at,-updated_at")
    """
    
    ordering_fields = ['created_at', 'updated_at', 'name']
    default_ordering = ['-created_at']
    
    def filter_queryset(self, request, queryset, view):
        """Apply ordering"""
        
        ordering = request.query_params.get('ordering')
        
        if not ordering:
            return queryset.order_by(*self.default_ordering)
        
        # Parse ordering parameter
        fields = ordering.split(',')
        valid_fields = [
            f'-{field}' if field.startswith('-') else field
            for field in fields
            if field.lstrip('-') in self.ordering_fields
        ]
        
        if valid_fields:
            return queryset.order_by(*valid_fields)
        
        return queryset.order_by(*self.default_ordering)


class OwnerFilterBackend:
    """
    Filter by owner/created_by.
    Query param: owner_id
    """
    
    owner_field = 'created_by'
    
    def filter_queryset(self, request, queryset, view):
        """Filter by owner"""
        
        owner_id = request.query_params.get('owner_id')
        
        if owner_id:
            filter_kwargs = {f'{self.owner_field}__id': owner_id}
            queryset = queryset.filter(**filter_kwargs)
        
        return queryset


class RelationshipFilterBackend:
    """
    Filter by related model.
    Query param: category_id, tag_id, etc.
    """
    
    def filter_queryset(self, request, queryset, view):
        """Filter by relationships"""
        
        # Get all related field IDs from query params
        for key, value in request.query_params.items():
            if key.endswith('_id') and key not in ['owner_id', 'company_id']:
                # Remove _id suffix to get field name
                field_name = key[:-3]
                
                # Check if field exists
                try:
                    queryset = queryset.filter(**{field_name: value})
                except Exception as e:
                    logger.warning(f"Filter error on {field_name}: {e}")
        
        return queryset


class PaginationFilterBackend:
    """
    Handle pagination parameters.
    Query params: page, page_size
    """
    
    default_page_size = 20
    max_page_size = 100
    
    def filter_queryset(self, request, queryset, view):
        """Note: This just validates params, actual pagination in paginator"""
        return queryset
    
    def paginate_queryset(self, queryset, request, view=None):
        """Paginate queryset"""
        
        try:
            page = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('page_size', self.default_page_size))
        except ValueError:
            page = 1
            page_size = self.default_page_size
        
        # Enforce max page size
        page_size = min(page_size, self.max_page_size)
        
        # Calculate offset
        offset = (page - 1) * page_size
        
        # Return paginated queryset
        return queryset[offset:offset + page_size]


class BulkOperationFilterBackend:
    """
    Filter for bulk operations.
    Query param: ids (comma-separated)
    """
    
    def filter_queryset(self, request, queryset, view):
        """Filter by multiple IDs"""
        
        ids = request.query_params.get('ids')
        
        if ids:
            id_list = [int(id_) for id_ in ids.split(',') if id_.isdigit()]
            return queryset.filter(id__in=id_list)
        
        return queryset


class AggregationFilterBackend:
    """
    Support for aggregation queries.
    Query param: aggregate (e.g., "count,sum:price")
    """
    
    def filter_queryset(self, request, queryset, view):
        """Apply aggregation"""
        # This would be handled by the view/serializer
        return queryset


class FilterChain:
    """
    Chain multiple filters together.
    """
    
    def __init__(self, *filters):
        self.filters = filters
    
    def filter_queryset(self, request, queryset, view):
        """Apply all filters in sequence"""
        
        for filter_backend in self.filters:
            if hasattr(filter_backend, 'filter_queryset'):
                queryset = filter_backend.filter_queryset(request, queryset, view)
        
        return queryset


def get_default_filters():
    """Get default filter chain for API views"""
    return FilterChain(
        CompanyAwareFilterBackend(),
        SearchFilterBackend(),
        StatusFilterBackend(),
        DateRangeFilterBackend(),
        OrderingFilterBackend(),
        RelationshipFilterBackend(),
    )
