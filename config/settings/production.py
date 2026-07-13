"""
Configurações de produção.
"""
from .base import *  # noqa: F401,F403
from .base import env

# ------------------------------------------------------------------------------
# CORE
# ------------------------------------------------------------------------------
DEBUG = False

SECRET_KEY = env("DJANGO_SECRET_KEY")

ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS")
