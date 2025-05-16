from rest_framework import serializers
from .models import Order, OrderProduct
from products.serializers import ProductSerializer
from django.contrib.auth.models import User

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']

# Basic serializer for product information
class BasicProductSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField(default='')
    price = serializers.DecimalField(max_digits=10, decimal_places=2, default=0)
    
# Simplified OrderProduct serializer to avoid deep nesting
class BasicOrderProductSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    product_id = serializers.IntegerField(source='product.id') 
    product_name = serializers.CharField(source='product.name', default='')
    quantity = serializers.IntegerField()
    
    class Meta:
        fields = ['id', 'product_id', 'product_name', 'quantity']

# Base serializer with all order fields except relationships
class BaseOrderSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    status = serializers.CharField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
    start_time = serializers.DateTimeField(allow_null=True)
    estimated_completion_time = serializers.IntegerField(default=0)
    estimated_price = serializers.DecimalField(max_digits=10, decimal_places=2, default=0)
    rejection_reason = serializers.CharField(allow_null=True, allow_blank=True)

# Serializer for list views (simplified to avoid relationship issues)
class OrderListSerializer(BaseOrderSerializer):
    # Flat representation of related entities
    client_id = serializers.IntegerField(source='client.id')
    client_username = serializers.CharField(source='client.username')
    manager_id = serializers.IntegerField(source='manager.id', allow_null=True)
    manager_username = serializers.CharField(source='manager.username', default='', allow_null=True)
    
    class Meta:
        fields = [
            'id', 'title', 'status', 'created_at', 'updated_at',
            'start_time', 'estimated_completion_time', 'estimated_price',
            'rejection_reason', 'client_id', 'client_username', 
            'manager_id', 'manager_username'
        ]

# Serializer for detail views
class OrderDetailSerializer(BaseOrderSerializer):
    # Manual serialization of related entities
    client = serializers.SerializerMethodField()
    manager = serializers.SerializerMethodField()
    used_products = serializers.SerializerMethodField()
    
    def get_client(self, obj):
        if not obj.client:
            return None
        return {
            'id': obj.client.id,
            'username': obj.client.username,
            'email': getattr(obj.client, 'email', '')
        }
    
    def get_manager(self, obj):
        if not obj.manager:
            return None
        return {
            'id': obj.manager.id,
            'username': obj.manager.username,
            'email': getattr(obj.manager, 'email', '')
        } if obj.manager else None
    
    def get_used_products(self, obj):
        try:
            # Safe querying of related products
            products = OrderProduct.objects.filter(order_id=obj.id)
            result = []
            for p in products:
                product_data = {
                    'id': p.id,
                    'quantity': p.quantity,
                    'product': {
                        'id': p.product.id,
                        'name': p.product.name,
                        'price': float(p.product.price) if hasattr(p.product, 'price') else 0
                    } if p.product else None
                }
                result.append(product_data)
            return result
        except Exception as e:
            print(f"Error getting used products: {str(e)}")
            return []

# Legacy serializer names for backward compatibility
class OrderProductSerializer(BasicOrderProductSerializer):
    pass

class OrderSerializer(OrderDetailSerializer):
    pass