from django.apps import AppConfig


class FeedConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.feed'

    def ready(self):
        # Registra os receivers que invalidam o cache de banners.
        from . import signals  # noqa: F401
