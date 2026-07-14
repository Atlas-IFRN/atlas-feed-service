from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import BannerViewSet, CommentViewSet, PostViewSet

router = DefaultRouter()
router.register(r'posts', PostViewSet, basename='post')
router.register(r'comments', CommentViewSet, basename='comment')
router.register(r'banners', BannerViewSet, basename='banner')

urlpatterns = [
    path('', include(router.urls)),
]
