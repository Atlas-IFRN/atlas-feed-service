from rest_framework import serializers

from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = [
            'id',
            'table_name',
            'action',
            'record_id',
            'user_id',
            'payload',
            'created_at',
        ]
        read_only_fields = fields
