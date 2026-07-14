"""Invalidação do cache de banners.

Qualquer escrita no model `Banner` (criar, editar, ativar/desativar, reordenar
ou excluir) descarta o cache da listagem pública, de modo que o próximo GET
reconstrói a resposta a partir do banco. Ligamos nos signals do model (e não
só nas ações da view) para cobrir também edições feitas pelo admin ou pelo
shell.
"""
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .cache import invalidate_active_banners_cache
from .models import Banner


@receiver(post_save, sender=Banner)
def _invalidate_on_banner_save(sender, **kwargs):
    invalidate_active_banners_cache()


@receiver(post_delete, sender=Banner)
def _invalidate_on_banner_delete(sender, **kwargs):
    invalidate_active_banners_cache()
