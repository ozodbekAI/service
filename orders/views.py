from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
from drf_spectacular.utils import extend_schema
from .models import Order, OrderProduct
from .serializers import OrderDetailSerializer, OrderListSerializer, OrderSerializer, OrderProductSerializer
from products.models import Product
from application.models import Notification
from application.permissions import IsClientOrReadOnly, IsManagerOrAdmin
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.conf import settings
from django.forms import ValidationError
from datetime import datetime

class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated, IsClientOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title']
    ordering_fields = ['created_at', 'updated_at', 'status']
    ordering = ['-created_at']

    def get_serializer_class(self):
        """
        Return different serializers based on the action
        """
        if self.action in ['list', 'my_orders', 'pending']:
            return OrderListSerializer
        # For retrieve, update, create, etc.
        return OrderDetailSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated:
            if user.role == 'admin':
                return Order.objects.all()
            elif user.role in ['admin', 'manager'] or user.is_staff or user.is_superuser:
                return Order.objects.filter(manager=user)
            return Order.objects.filter(client=user)
        return Order.objects.none()

    @extend_schema(tags=["Orders"], responses={200: OrderSerializer(many=True)})
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(tags=["Orders"], responses={200: OrderSerializer})
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(tags=["Orders"], responses={200: OrderSerializer})
    @action(detail=True, methods=['post'], permission_classes=[IsManagerOrAdmin])
    def add_product(self, request, pk=None):
        order = self.get_object()
        product_id = request.data.get('product_id')
        quantity = request.data.get('quantity')

        if not product_id or not quantity:
            return Response({'detail': 'Product ID and quantity are required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            product = Product.objects.get(id=product_id)
            if product.quantity < int(quantity):
                return Response({'detail': f'Not enough stock for {product.name}'}, status=status.HTTP_400_BAD_REQUEST)
            product.quantity -= int(quantity)
            product.save()

            order_product, created = OrderProduct.objects.get_or_create(
                order=order,
                product=product,
                defaults={'quantity': quantity}
            )
            if not created:
                order_product.quantity += int(quantity)
                order_product.save()

            if product.quantity <= 5:
                managers = User.objects.filter(Q(is_staff=True) | Q(is_superuser=True))
                for manager in managers:
                    Notification.objects.create(
                        user=manager,
                        title=f"Low Stock: {product.name}",
                        message=f"Only {product.quantity} units of {product.name} left.",
                        type='low_stock'
                    )

            serializer = self.get_serializer(order)
            return Response(serializer.data)
        except Product.DoesNotExist:
            return Response({'detail': 'Product not found.'}, status=status.HTTP_404_NOT_FOUND)

    @extend_schema(tags=["Orders"], responses={200: OrderSerializer})
    @action(detail=True, methods=['post'], permission_classes=[IsManagerOrAdmin])
    def remove_product(self, request, pk=None):
        order = self.get_object()
        product_id = request.data.get('product_id')

        if not product_id:
            return Response({'detail': 'Product ID is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            order_product = OrderProduct.objects.get(order=order, product_id=product_id)
            product = order_product.product
            product.quantity += order_product.quantity
            product.save()
            order_product.delete()
            serializer = self.get_serializer(order)
            return Response(serializer.data)
        except OrderProduct.DoesNotExist:
            return Response({'detail': 'Product not assigned to this order.'}, status=status.HTTP_404_NOT_FOUND)

    @extend_schema(tags=["Orders"], responses={200: OrderSerializer})
    @action(detail=True, methods=['post'], permission_classes=[IsManagerOrAdmin])
    def start_processing(self, request, pk=None):
        order = self.get_object()
        if order.status != 'client_approved':
            return Response({'detail': 'Only client-approved orders can be processed'}, status=status.HTTP_400_BAD_REQUEST)

        order.status = 'in_process'
        order.start_time = datetime.now()
        order.save()

        Notification.objects.create(
            user=order.client,
            title="Your Order is In Process",
            message=f"Your order '{order.title}' is now being processed. Estimated completion in {order.estimated_completion_time} hours.",
            type='order_in_process'
        )

        if order.client.email:
            send_mail(
                subject="Your Order is In Process",
                message=f"Dear {order.client.username},\n\nYour order '{order.title}' is now being processed.\nEstimated completion in {order.estimated_completion_time} hours.\n\nThank you!",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[order.client.email]
            )

        return Response({'detail': 'Order is now in process'})

    @extend_schema(tags=["Orders"], responses={200: OrderSerializer})
    @action(detail=True, methods=['post'], permission_classes=[IsManagerOrAdmin])
    def complete(self, request, pk=None):
        order = self.get_object()
        if order.status != 'in_process' or order.manager != request.user:
            return Response({'detail': 'Only in-process orders assigned to you can be completed'}, status=status.HTTP_400_BAD_REQUEST)

        order.status = 'completed'
        order.save()

        Notification.objects.create(
            user=order.client,
            title="Your Order is Completed",
            message=f"Your order '{order.title}' has been completed.",
            type='order_completed'
        )

        if order.client.email:
            send_mail(
                subject="Your Order is Completed",
                message=f"Dear {order.client.username},\n\nYour order '{order.title}' has been completed.\n\nThank you!",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[order.client.email]
            )

        return Response({'detail': 'Order completed successfully'})

    @extend_schema(
        tags=["Orders"],
        request={'rejection_reason': {'type': 'string'}},
        responses={200: OrderSerializer}
    )
    @action(detail=True, methods=['post'], permission_classes=[IsManagerOrAdmin])
    def reject(self, request, pk=None):
        order = self.get_object()
        if order.status != 'client_approved':
            return Response({'detail': 'Only client-approved orders can be rejected'}, status=status.HTTP_400_BAD_REQUEST)

        reason = request.data.get('rejection_reason')
        if not reason:
            return Response({'detail': 'Rejection reason is required'}, status=status.HTTP_400_BAD_REQUEST)

        order.status = 'rejected'
        order.rejection_reason = reason
        order.save()

        Notification.objects.create(
            user=order.client,
            title="Your Order has been Rejected",
            message=f"Your order '{order.title}' was rejected. Reason: {reason}",
            type='order_rejected'
        )

        if order.client.email:
            send_mail(
                subject="Your Order has been Rejected",
                message=f"Dear {order.client.username},\n\nYour order '{order.title}' was rejected.\nReason: {reason}\n\nThank you!",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[order.client.email]
            )

        return Response({'detail': 'Order rejected successfully'})

    @extend_schema(tags=["Orders"], responses={200: OrderSerializer(many=True)})
    @action(detail=False, methods=['get'], permission_classes=[IsManagerOrAdmin])
    def pending(self, request):
        queryset = self.get_queryset().filter(status='client_approved')
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @extend_schema(tags=["Orders"], responses={200: OrderListSerializer(many=True)})
    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def my_orders(self, request):
        try:
            # Safely get orders
            orders = Order.objects.filter(client=request.user).order_by('-created_at')[:1]
            print(f"Orders: {orders}")  # Debug
            
            # Use a simplified serializer to avoid complex relations
            serializer = OrderListSerializer(orders, many=True)
            print(f"Serialized data: {serializer.data}")  # Debug
            
            return Response(serializer.data)
        except Exception as e:
            # Log the error and return a graceful response
            print(f"Error in my_orders: {str(e)}")
            return Response(
                {"detail": "An error occurred while retrieving your orders."}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    

class OrderProductViewSet(viewsets.ModelViewSet):
    queryset = OrderProduct.objects.all()
    serializer_class = OrderProductSerializer
    permission_classes = [IsManagerOrAdmin]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['product__name', 'order__title']
    ordering_fields = ['added_at']
    ordering = ['-added_at']

    def get_queryset(self):
        order_id = self.request.query_params.get('order_id')
        if order_id:
            return OrderProduct.objects.filter(order_id=order_id)
        return super().get_queryset()

    def perform_create(self, serializer):
        product_id = self.request.data.get('product')
        quantity = int(self.request.data.get('quantity', 1))
        order_id = self.request.data.get('order_id')

        try:
            product = Product.objects.get(id=product_id)
            order = Order.objects.get(id=order_id)
            if product.quantity < quantity:
                raise ValidationError("Not enough product in stock")
            
            product.quantity -= quantity
            product.save()

            if product.quantity <= 5:
                managers = User.objects.filter(Q(is_staff=True) | Q(is_superuser=True))
                for manager in managers:
                    Notification.objects.create(
                        user=manager,
                        title=f"Low Stock: {product.name}",
                        message=f"Only {product.quantity} units of {product.name} left. Please restock.",
                        type='low_stock'
                    )

            serializer.save(order=order, product=product, quantity=quantity)
        except Product.DoesNotExist:
            raise ValidationError("Product not found")
        except Order.DoesNotExist:
            raise ValidationError("Order not found")