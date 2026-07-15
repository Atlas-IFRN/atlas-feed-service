from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import BannerViewSet, CommentViewSet, PostViewSet
from .audit_views import AuditLogViewSet

router = DefaultRouter()
router.register(r'audit-logs', AuditLogViewSet, basename='audit-log')
router.register(r'posts', PostViewSet, basename='post')
router.register(r'comments', CommentViewSet, basename='comment')
router.register(r'banners', BannerViewSet, basename='banner')

urlpatterns = [
    path('', include(router.urls)),
]
