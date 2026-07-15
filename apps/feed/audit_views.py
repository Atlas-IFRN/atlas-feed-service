from rest_framework import pagination, viewsets
from rest_framework.permissions import IsAuthenticated

from .audit_serializers import AuditLogSerializer
from .models import AuditLog
from .permissions import IsTeacher


class AuditLogPagination(pagination.PageNumberPagination):
    page_size = 100
    page_size_query_param = 'page_size'
    max_page_size = 100


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated, IsTeacher]
    serializer_class = AuditLogSerializer
    pagination_class = AuditLogPagination

    def get_queryset(self):
        queryset = AuditLog.objects.all()
        action_name = self.request.query_params.get('action')
        table_name = self.request.query_params.get('table_name')
        if action_name:
            queryset = queryset.filter(action=action_name.upper())
        if table_name:
            queryset = queryset.filter(table_name=table_name)
        return queryset
