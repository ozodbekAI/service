from django.urls import include, path
from rest_framework.routers import DefaultRouter

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from users.views import ProfileImageViewSet, UserViewSet

router = DefaultRouter()
router.register(r'', UserViewSet)
router.register(r'upload_profile_image', ProfileImageViewSet, basename='profile-image')


urlpatterns = [
    path('', include(router.urls)),
]