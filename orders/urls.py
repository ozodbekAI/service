from django.urls import path, include
from rest_framework.routers import DefaultRouter
from orders.views import OrderProductViewSet, OrderViewSet

router = DefaultRouter()
router.register(r'product', OrderProductViewSet, basename='order-product')
router.register(r'', OrderViewSet)

urlpatterns = [
    path('', include(router.urls)),
]