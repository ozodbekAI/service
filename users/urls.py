from django.urls import include, path
from rest_framework.routers import DefaultRouter

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from users.views import UserViewSet

router = DefaultRouter(trailing_slash=False)
router.register(r'', UserViewSet)


urlpatterns = [
    path('', include(router.urls)),
    path('upload_profile_image/', UserViewSet.as_view({'post': 'upload_profile_image'}), name='user-upload-profile-image'),

]