import json
from contextvars import ContextVar

from django.core.serializers.json import DjangoJSONEncoder


_current_actor_id = ContextVar('feed_audit_actor_id', default=None)
SENSITIVE_FIELD_NAMES = {'password', 'token', 'access', 'refresh', 'secret'}


def set_current_actor_id(user_id):
    _current_actor_id.set(str(user_id) if user_id else None)


def clear_current_actor_id():
    _current_actor_id.set(None)


def get_current_actor_id():
    return _current_actor_id.get()


def snapshot_instance(instance):
    data = {}
    for field in instance._meta.concrete_fields:
        if field.name.lower() in SENSITIVE_FIELD_NAMES:
            continue
        value = getattr(instance, field.attname, None)
        if hasattr(value, 'name'):
            value = value.name
        data[field.name] = value
    return json.loads(json.dumps(data, cls=DjangoJSONEncoder))
