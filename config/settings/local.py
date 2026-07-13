"""
Configurações de desenvolvimento local.
"""
from .base import *  # noqa: F401,F403
from .base import env

# ------------------------------------------------------------------------------
# CORE
# ------------------------------------------------------------------------------
DEBUG = env.bool("DJANGO_DEBUG", default=True)

ALLOWED_HOSTS = env.list(
    "DJANGO_ALLOWED_HOSTS",
    default=["localhost", "127.0.0.1"],
)
