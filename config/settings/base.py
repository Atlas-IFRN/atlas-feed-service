"""
Configurações base — comuns a todos os ambientes.
"""
import os
from pathlib import Path

import environ

# ------------------------------------------------------------------------------
# PATHS
# ------------------------------------------------------------------------------
# config/settings/base.py -> config/settings -> config -> <project_root>
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# ------------------------------------------------------------------------------
# ENVIRONMENT VARIABLES
# ------------------------------------------------------------------------------
env = environ.Env(
    DEBUG=(bool, False),
)
environ.Env.read_env(os.path.join(BASE_DIR, ".env"))

# ------------------------------------------------------------------------------
# CORE
# ------------------------------------------------------------------------------
SECRET_KEY = env(
    "DJANGO_SECRET_KEY",
    default="django-insecure-p6^ped7h!8lxdm0f7pw%u0p!$h--b6lpi7aae5eli4(g)a+u@6"
)

DEBUG = env.bool("DJANGO_DEBUG", default=False)

ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=[])

# ==============================================================================
# DATABASE CONFIGURATION
# ==============================================================================

DATABASES = {
    # O método env.db() lê a variável DATABASE_URL do seu .env.
    # Se ela não existir, ele usa o SQLite como fallback (valor padrão).
    'default': env.db(
        'DATABASE_URL',
        default=f'sqlite:///{BASE_DIR}/db.sqlite3'
    )
}

# ------------------------------------------------------------------------------
# APPS
# ------------------------------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    'rest_framework',

    # Local apps
    "apps.feed",

    # biblioteca responsável por gerar a documentação Swagger da API
    'drf_spectacular',
]

# ------------------------------------------------------------------------------
# MIDDLEWARE
# ------------------------------------------------------------------------------
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',

    'DEFAULT_AUTHENTICATION_CLASSES': [
        'config.authentication.AtlasJWTAuthentication',
    ],
    # O feed exige usuário autenticado por padrão (posts/comentários/curtidas
    # sempre pertencem a alguém). Ações de leitura pública, se necessárias no
    # futuro, podem relaxar isso por view.
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}

# ------------------------------------------------------------------------------
# SIMPLE JWT
# ------------------------------------------------------------------------------
# Validação local do token pelo header, sem chamar o auth-service.
#
# Chave de assinatura: por padrão usa a SECRET_KEY (que hoje é compartilhada
# entre os serviços via DJANGO_SECRET_KEY). Para separar o segredo de assinatura
# do JWT do SECRET_KEY do Django, defina JWT_SIGNING_KEY no .env — MAS ele
# precisa ser o MESMO valor no auth-service (que assina) e em TODOS os serviços
# que validam (track, scholarship, notification, feed); do contrário os tokens
# deixam de ser aceitos. Enquanto não definido, o comportamento é idêntico.
JWT_SIGNING_KEY = env("JWT_SIGNING_KEY", default=SECRET_KEY)

SIMPLE_JWT = {
    'AUTH_HEADER_TYPES': ('Bearer',),
    'TOKEN_USER_CLASS': 'config.authentication.AtlasTokenUser',
    'SIGNING_KEY': JWT_SIGNING_KEY,
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'Feed Service API',
    'DESCRIPTION': 'Microsserviço responsável pelas postagens e interações (curtidas e comentários) do feed.',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
}

# ------------------------------------------------------------------------------
# TEMPLATES
# ------------------------------------------------------------------------------
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# ------------------------------------------------------------------------------
# PASSWORD VALIDATION
# ------------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ------------------------------------------------------------------------------
# INTERNATIONALIZATION
# ------------------------------------------------------------------------------
LANGUAGE_CODE = "pt-br"

TIME_ZONE = "America/Sao_Paulo"

USE_I18N = True

USE_TZ = True

# ------------------------------------------------------------------------------
# STATIC & MEDIA FILES
# ------------------------------------------------------------------------------
STATIC_URL = "/api/feed/static/"

# Imagens anexadas aos posts são guardadas DENTRO do diretório `static/` do
# serviço (subpasta `uploads/`). Assim são servidas pela mesma rota pública
# /api/feed/static/ que o Nginx já roteia para o feed-service — sem exigir uma
# rota nova nem atravessar a barreira de JWT (imagens em <img> não mandam
# Authorization). Em dev (runserver + DEBUG=True) o handler de staticfiles serve
# arquivos escritos em STATICFILES_DIRS em tempo de execução.
STATICFILES_DIRS = [BASE_DIR / "static"]

MEDIA_URL = "/api/feed/static/uploads/"
MEDIA_ROOT = BASE_DIR / "static" / "uploads"

# ------------------------------------------------------------------------------
# DEFAULTS
# ------------------------------------------------------------------------------
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ==============================================================================
# CELERY (RabbitMQ broker) — feed é apenas PRODUTOR
# ==============================================================================
# Publica o evento `notifications.create` na fila do notification-service quando
# há interações (curtidas/comentários). Não roda worker. Timeout curto + sem
# retry de publicação para que um broker indisponível nunca segure a interação
# do usuário (a publicação é best-effort).
NOTIFICATIONS_QUEUE = env("NOTIFICATIONS_QUEUE", default="notifications")

CELERY_BROKER_URL = env(
    'CELERY_BROKER_URL',
    default='amqp://guest:guest@rabbitmq:5672//',
)
CELERY_TASK_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TIMEZONE = TIME_ZONE
# Publicação best-effort: se o broker estiver fora, falha rápido (~2×timeout)
# e é capturada, sem segurar a request. Não descarta se o broker só estiver lento.
CELERY_BROKER_CONNECTION_TIMEOUT = 2
CELERY_BROKER_CONNECTION_RETRY = False
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = False
CELERY_BROKER_CONNECTION_MAX_RETRIES = 0
