from rest_framework import serializers
from application.models import OrderProduct, Notification, Dashboard
from orders.serializers import OrderSerializer
from products.serializers import ProductSerializer
from users.serializers import UserSerializer

class OrderProductSerializer(serializers.ModelSerializer):
    product_details = ProductSerializer(source='product', read_only=True)
    order_details = OrderSerializer(source='order', read_only=True)
    
    class Meta:
        model = OrderProduct
        fields = ['id', 'order', 'order_details', 'product', 'product_details', 'quantity', 'added_at']

class NotificationSerializer(serializers.ModelSerializer):
    user_details = UserSerializer(source='user', read_only=True)
    
    class Meta:
        model = Notification
        fields = ['id', 'user', 'user_details', 'title', 'message', 'type', 'is_read', 'created_at']
        read_only_fields = ['user', 'created_at']

class DashboardSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dashboard
        fields = ['id', 'date', 'total_orders', 'accepted_orders', 'rejected_orders', 
                  'completed_orders', 'pending_orders', 'total_clients']
        read_only_fields = ['date']