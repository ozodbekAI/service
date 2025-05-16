from django.urls import include, path
from rest_framework.routers import DefaultRouter

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from users.views import UserViewSet

router = DefaultRouter()
router.register(r'', UserViewSet)


urlpatterns = [
    path('', include(router.urls)),

]