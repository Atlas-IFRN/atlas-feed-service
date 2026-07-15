"""Invalidação de cache e auditoria das alterações do Feed Service."""

from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from .audit import get_current_actor_id, snapshot_instance
from .cache import invalidate_active_banners_cache
from .models import (
    AuditAction,
    AuditLog,
    Banner,
    Comment,
    CommentLike,
    Post,
    PostLike,
)


AUDITED_MODELS = {
    Post: 'post',
    Banner: 'banner',
    Comment: 'comment',
    PostLike: 'post_like',
    CommentLike: 'comment_like',
}


def _instance_actor_id(instance):
    return get_current_actor_id()


def _write_log(instance, action, payload):
    AuditLog.objects.create(
        table_name=AUDITED_MODELS[type(instance)],
        action=action,
        record_id=instance.pk,
        user_id=_instance_actor_id(instance),
        payload=payload,
    )


def capture_before_save(sender, instance, **kwargs):
    instance._audit_before = None
    if instance.pk:
        previous = sender._default_manager.filter(pk=instance.pk).first()
        if previous is not None:
            instance._audit_before = snapshot_instance(previous)


def audit_after_save(sender, instance, created, **kwargs):
    after = snapshot_instance(instance)
    if created:
        _write_log(instance, AuditAction.CREATE, {'after': after})
    else:
        _write_log(
            instance,
            AuditAction.UPDATE,
            {'before': getattr(instance, '_audit_before', None), 'after': after},
        )


def audit_after_delete(sender, instance, **kwargs):
    _write_log(instance, AuditAction.DELETE, {'before': snapshot_instance(instance)})


for audited_model in AUDITED_MODELS:
    pre_save.connect(
        capture_before_save,
        sender=audited_model,
        dispatch_uid=f'feed_audit_pre_save_{audited_model._meta.label_lower}',
    )
    post_save.connect(
        audit_after_save,
        sender=audited_model,
        dispatch_uid=f'feed_audit_post_save_{audited_model._meta.label_lower}',
    )
    post_delete.connect(
        audit_after_delete,
        sender=audited_model,
        dispatch_uid=f'feed_audit_post_delete_{audited_model._meta.label_lower}',
    )


@receiver(post_save, sender=Banner)
def _invalidate_on_banner_save(sender, **kwargs):
    invalidate_active_banners_cache()


@receiver(post_delete, sender=Banner)
def _invalidate_on_banner_delete(sender, **kwargs):
    invalidate_active_banners_cache()
