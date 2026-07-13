from django.conf import settings
from django.contrib import admin
from django.http import HttpResponse
from django.urls import include, path, re_path
from django.views.static import serve
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView


def health_check(request):
    return HttpResponse("OK", status=200)


urlpatterns = [
    path('api/feed/admin/', admin.site.urls),
    path('health/', health_check),

    # Rotas públicas (exigem JWT)
    path('api/feed/', include('apps.feed.urls')),

    path('api/feed/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/feed/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]

# Imagens anexadas (MEDIA). Em dev (DEBUG=True) o handler de staticfiles do
# runserver já serve os arquivos escritos sob static/uploads; esta rota é a
# rede de segurança para quando DEBUG=False (ex.: gunicorn) e o handler não
# está ativo. O prefixo bate com MEDIA_URL (/api/feed/static/uploads/).
_media_prefix = settings.MEDIA_URL.lstrip('/')
urlpatterns += [
    re_path(
        rf'^{_media_prefix}(?P<path>.*)$',
        serve,
        {'document_root': settings.MEDIA_ROOT},
    ),
]
