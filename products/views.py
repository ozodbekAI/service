from rest_framework import viewsets, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.forms import ValidationError
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample, OpenApiResponse
from .models import Product, ProductCategory, ProductImage
from .serializers import ProductSerializer, ProductCategorySerializer, ProductImageSerializer
from .permissions import IsManagerOrAdmin

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'price', 'quantity']
    ordering = ['name']

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            permission_classes = [permissions.AllowAny]
        else:
            permission_classes = [IsManagerOrAdmin]
        return [permission() for permission in permission_classes]

    @extend_schema(tags=["Products"], responses={200: ProductSerializer(many=True)})
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(tags=["Products"], responses={200: ProductSerializer})
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(tags=["Products"], request=ProductSerializer, responses={201: ProductSerializer})
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(tags=["Products"], request=ProductSerializer, responses={200: ProductSerializer})
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(tags=["Products"], request=ProductSerializer, responses={200: ProductSerializer})
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(tags=["Products"], responses={204: None})
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    @extend_schema(
        tags=["Products"],
        responses={200: ProductSerializer(many=True)},
        examples=[OpenApiExample('Low Stock Response', value=[{"id": 1, "name": "Product Name", "quantity": 3}])]
    )
    @action(detail=False, methods=['get'], permission_classes=[IsManagerOrAdmin])
    def low_stock(self, request):
        products = Product.objects.filter(quantity__lt=5).order_by('quantity')
        serializer = self.get_serializer(products, many=True)
        return Response(serializer.data)

class ProductCategoryViewSet(viewsets.ModelViewSet):
    queryset = ProductCategory.objects.all()
    serializer_class = ProductCategorySerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'description']

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            permission_classes = [permissions.AllowAny]
        else:
            permission_classes = [IsManagerOrAdmin]
        return [permission() for permission in permission_classes]

    @extend_schema(tags=["Products"], responses={200: ProductCategorySerializer(many=True)})
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(tags=["Products"], responses={200: ProductCategorySerializer})
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(tags=["Products"], request=ProductCategorySerializer, responses={201: ProductCategorySerializer})
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(tags=["Products"], request=ProductCategorySerializer, responses={200: ProductCategorySerializer})
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(tags=["Products"], request=ProductCategorySerializer, responses={200: ProductCategorySerializer})
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(tags=["Products"], responses={204: None})
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

class ProductImageViewSet(viewsets.ModelViewSet):
    queryset = ProductImage.objects.all()
    serializer_class = ProductImageSerializer
    permission_classes = [IsManagerOrAdmin]
    parser_classes = (MultiPartParser, FormParser)

    def get_queryset(self):
        product_id = self.request.query_params.get('product_id')
        if product_id:
            return ProductImage.objects.filter(product_id=product_id)
        return ProductImage.objects.none()

    @extend_schema(tags=["Products"], responses={200: ProductImageSerializer(many=True)})
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(tags=["Products"], responses={200: ProductImageSerializer})
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(tags=["Products"], request=ProductImageSerializer, responses={201: ProductImageSerializer})
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(tags=["Products"], request=ProductImageSerializer, responses={200: ProductImageSerializer})
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(tags=["Products"], request=ProductImageSerializer, responses={200: ProductImageSerializer})
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(tags=["Products"], responses={204: None})
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    def perform_create(self, serializer):
        print("Request data:", self.request.data)
        product_id = self.request.data.get('product')
        print("Product ID:", product_id)
        
        try:
            product = Product.objects.get(id=product_id)
            if self.request.data.get('is_main', False) == 'true':
                ProductImage.objects.filter(product=product, is_main=True).update(is_main=False)
            serializer.save(product=product)
        except Product.DoesNotExist:
            raise ValidationError("Product not found")