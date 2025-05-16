from django.urls import path, include
from rest_framework.routers import DefaultRouter
from products.views import ProductViewSet, ProductCategoryViewSet, ProductImageViewSet

router = DefaultRouter()
router.register(r'products', ProductViewSet, basename='product')
router.register(r'categories', ProductCategoryViewSet, basename='product-category')
router.register(r'product-images', ProductImageViewSet, basename='product-image')

urlpatterns = [
    path('', include(router.urls)),
]