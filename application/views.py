from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import timedelta, datetime
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse
from django.forms import ValidationError
from .models import Announcement, AnnouncementImage, Notification, Dashboard
from .serializers import AnnouncementSerializer, AnnouncementImageSerializer, NotificationSerializer, DashboardSerializer
from .permissions import IsClientOrReadOnly, IsManagerOrAdmin, IsAdminUser, IsOwnerOrManagerOrAdmin
from orders.models import Order, OrderProduct
from products.models import Product
from django.contrib.auth.models import User

class AnnouncementViewSet(viewsets.ModelViewSet):
    queryset = Announcement.objects.all()
    serializer_class = AnnouncementSerializer
    permission_classes = [permissions.IsAuthenticated, IsClientOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'description']
    ordering_fields = ['created_at', 'updated_at', 'status']
    ordering = ['-created_at']

    def get_queryset(self):
        user = self.request.user
        print(f"User: {user.username}, Role: {user.role}, Action: {self.action}")
        if user.is_authenticated:
            if user.role in ['admin', 'manager']:
                if self.action in ['pending', 'retrieve']:
                    return Announcement.objects.filter(status='pending')
                elif self.action == 'managed':
                    return Announcement.objects.filter(accepted_by=user)
                else:
                    return Announcement.objects.all()
            else:
                return Announcement.objects.filter(client=user)
        return Announcement.objects.none()

    def perform_create(self, serializer):
        serializer.save(client=self.request.user, status='pending')

    @extend_schema(
        tags=["Announcements"],
        request={
            'estimated_completion_time': {'type': 'integer'},
            'estimated_price': {'type': 'number'},
            'products': {
                'type': 'array',
                'items': {
                    'type': 'object',
                    'properties': {
                        'product_id': {'type': 'integer'},
                        'quantity': {'type': 'integer'}
                    }
                }
            }
        },
        responses={200: AnnouncementSerializer}
    )
    @action(detail=True, methods=['post'], permission_classes=[IsManagerOrAdmin])
    def accept(self, request, pk=None):
        announcement = self.get_object()
        if announcement.status != 'pending':
            return Response(
                {'detail': 'Only pending announcements can be accepted'},
                status=status.HTTP_400_BAD_REQUEST
            )

        estimated_time = request.data.get('estimated_completion_time')
        estimated_price = request.data.get('estimated_price')
        products = request.data.get('products', [])

        if not estimated_time or not estimated_price:
            return Response(
                {'detail': 'Estimated time and price are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Save estimated price and time to the announcement
        announcement.status = 'accepted'
        announcement.accepted_by = request.user
        announcement.estimated_completion_time = estimated_time
        announcement.estimated_price = estimated_price
        announcement.save()

        # Save products to AnnouncementProduct
        for product_data in products:
            product_id = product_data.get('product_id')
            quantity = product_data.get('quantity', 1)
            try:
                product = Product.objects.get(id=product_id)
                AnnouncementProduct.objects.create(
                    announcement=announcement,
                    product=product,
                    quantity=quantity
                )
            except Product.DoesNotExist:
                return Response(
                    {'detail': f"Product with ID {product_id} does not exist"},
                    status=status.HTTP_400_BAD_REQUEST
                )

        Notification.objects.create(
            user=announcement.client,
            title="Your Announcement has been Accepted",
            message=f"Your announcement '{announcement.title}' has been accepted. Estimated price: {estimated_price} сум, Estimated time: {estimated_time} hours. Please approve or reject.",
            type='announcement_accepted',
            related_id=announcement.id
        )

        if announcement.client.email:
            send_mail(
                subject="Your Announcement has been Accepted",
                message=f"Dear {announcement.client.username},\n\nYour announcement '{announcement.title}' has been accepted.\nEstimated price: {estimated_price} сум\nEstimated time: {estimated_time} hours.\nPlease approve or reject the order.\n\nThank you!",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[announcement.client.email]
            )

        return Response({'detail': 'Announcement accepted. Awaiting client approval'})

    @extend_schema(
        tags=["Announcements"],
        request={'rejection_reason': {'type': 'string'}},
        responses={200: AnnouncementSerializer}
    )
    @action(detail=True, methods=['post'], permission_classes=[IsManagerOrAdmin])
    def reject(self, request, pk=None):
        announcement = self.get_object()
        if announcement.status != 'pending':
            return Response(
                {'detail': 'Only pending announcements can be rejected'},
                status=status.HTTP_400_BAD_REQUEST
            )

        reason = request.data.get('rejection_reason')
        if not reason:
            return Response(
                {'detail': 'Rejection reason is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        announcement.status = 'rejected'
        announcement.rejection_reason = reason
        announcement.accepted_by = request.user
        announcement.save()

        Notification.objects.create(
            user=announcement.client,
            title="Your Announcement has been Rejected",
            message=f"Your announcement '{announcement.title}' was rejected. Reason: {reason}",
            type='announcement_rejected'
        )

        if announcement.client.email:
            send_mail(
                subject="Your Announcement has been Rejected",
                message=f"Dear {announcement.client.username},\n\nYour announcement '{announcement.title}' was rejected.\nReason: {reason}\n\nThank you!",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[announcement.client.email]
            )

        return Response({'detail': 'Announcement rejected successfully'})

    @extend_schema(
        tags=["Announcements"],
        responses={200: AnnouncementSerializer}
    )
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def client_approve(self, request, pk=None):
        announcement = self.get_object()
        if announcement.client != request.user:
            return Response(
                {'detail': 'You can only approve your own announcements'},
                status=status.HTTP_403_FORBIDDEN
            )
        if announcement.status != 'accepted':
            return Response(
                {'detail': 'Only accepted announcements can be approved'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if hasattr(announcement, 'order'):
            return Response(
                {'detail': 'An order for this announcement already exists'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create order
        order = Order.objects.create(
            client=announcement.client,
            announcement=announcement,
            title=announcement.title,
            status='client_approved',
            estimated_completion_time=announcement.estimated_completion_time,
            estimated_price=announcement.estimated_price,
            manager=announcement.accepted_by,
            start_time=timezone.now()
        )

        # Copy products from announcement
        for product_data in announcement.used_products.all():
            OrderProduct.objects.create(
                order=order,
                product=product_data.product,
                quantity=product_data.quantity
            )

        announcement.status = 'in_process'
        announcement.save()

        Notification.objects.create(
            user=order.manager,
            title="Client Approved Order",
            message=f"The client has approved the order '{order.title}'. Processing has started.",
            type='client_approved'
        )

        if order.manager.email:
            send_mail(
                subject="Client Approved Order",
                message=f"Dear {order.manager.username},\n\nThe client has approved the order '{order.title}'.\nProcessing has started.\n\nThank you!",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[order.manager.email]
            )

        return Response({'detail': 'Order approved by client and created'})

    @extend_schema(
        tags=["Announcements"],
        request={'rejection_reason': {'type': 'string'}},
        responses={200: AnnouncementSerializer}
    )
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def client_reject(self, request, pk=None):
        announcement = self.get_object()
        if announcement.client != request.user:
            return Response(
                {'detail': 'You can only reject your own announcements'},
                status=status.HTTP_403_FORBIDDEN
            )
        if announcement.status != 'accepted':
            return Response(
                {'detail': 'Only accepted announcements can be rejected'},
                status=status.HTTP_400_BAD_REQUEST
            )

        reason = request.data.get('rejection_reason')
        if not reason:
            return Response(
                {'detail': 'Rejection reason is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        announcement.status = 'rejected'
        announcement.rejection_reason = reason
        announcement.save()

        Notification.objects.create(
            user=announcement.accepted_by,
            title="Client Rejected Announcement",
            message=f"The client rejected the announcement '{announcement.title}'. Reason: {reason}",
            type='announcement_rejected'
        )

        if announcement.accepted_by.email:
            send_mail(
                subject="Client Rejected Announcement",
                message=f"Dear {announcement.accepted_by.username},\n\nThe client rejected the announcement '{announcement.title}'.\nReason: {reason}\n\nThank you!",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[announcement.accepted_by.email]
            )

        return Response({'detail': 'Announcement rejected by client'})

    @extend_schema(
        tags=["Announcements"],
        responses={200: AnnouncementSerializer}
    )
    @action(detail=True, methods=['post'], permission_classes=[IsManagerOrAdmin])
    def complete(self, request, pk=None):
        announcement = self.get_object()
        if announcement.status not in ['accepted', 'in_process']:
            return Response(
                {'detail': 'Only accepted or in-progress announcements can be completed'},
                status=status.HTTP_400_BAD_REQUEST
            )

        announcement.status = 'completed'
        announcement.save()

        try:
            order = announcement.order
            order.status = 'completed'
            order.save()

            Notification.objects.create(
                user=announcement.client,
                title="Your Announcement has been Completed",
                message=f"Your announcement '{announcement.title}' has been completed.",
                type='announcement_completed'
            )

            if announcement.client.email:
                send_mail(
                    subject="Your Announcement has been Completed",
                    message=f"Dear {announcement.client.username},\n\nYour announcement '{announcement.title}' has been completed.\n\nThank you!",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[announcement.client.email]
                )
        except Order.DoesNotExist:
            pass

        return Response({'detail': 'Announcement marked as completed'})

    @extend_schema(tags=["Announcements"], responses={200: AnnouncementSerializer(many=True)})
    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def my_announcements(self, request):
        announcements = Announcement.objects.filter(client=request.user).order_by('-created_at')
        serializer = self.get_serializer(announcements, many=True)
        return Response(serializer.data)

    @extend_schema(tags=["Announcements"], responses={200: AnnouncementSerializer(many=True)})
    @action(detail=False, methods=['get'], permission_classes=[IsManagerOrAdmin])
    def pending(self, request):
        announcements = Announcement.objects.filter(status='pending').order_by('-created_at')
        serializer = self.get_serializer(announcements, many=True)
        return Response(serializer.data)

    @extend_schema(tags=["Announcements"], responses={200: AnnouncementSerializer(many=True)})
    @action(detail=False, methods=['get'], permission_classes=[IsManagerOrAdmin])
    def managed(self, request):
        announcements = self.get_queryset()
        serializer = self.get_serializer(announcements, many=True)
        return Response(serializer.data)

class AnnouncementImageViewSet(viewsets.ModelViewSet):
    queryset = AnnouncementImage.objects.all()
    serializer_class = AnnouncementImageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        announcement_id = self.request.query_params.get('announcement_id')
        if announcement_id:
            return AnnouncementImage.objects.filter(announcement_id=announcement_id)
        return AnnouncementImage.objects.none()

    def perform_create(self, serializer):
        announcement_id = self.request.data.get('announcement_id')
        try:
            announcement = Announcement.objects.get(id=announcement_id, client=self.request.user)
            serializer.save(announcement=announcement)
        except Announcement.DoesNotExist:
            raise ValidationError("Announcement not found or not yours")

class NotificationViewSet(viewsets.ModelViewSet):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def mark_as_read(self, request, pk=None):
        notification = self.get_object()
        notification.read = True
        notification.save()
        return Response({'detail': 'Notification marked as read'})

    @action(detail=False, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def mark_all_as_read(self, request):
        Notification.objects.filter(user=request.user, read=False).update(read=True)
        return Response({'detail': 'All notifications marked as read'})

class DashboardViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Dashboard.objects.all()
    serializer_class = DashboardSerializer
    permission_classes = [IsAdminUser]

    @extend_schema(tags=["Dashboard"], responses={200: DashboardSerializer})
    @action(detail=False, methods=['get'], permission_classes=[IsAdminUser])
    def today_stats(self, request):
        today = timezone.now().date()
        dashboard, created = Dashboard.objects.get_or_create(date=today)

        dashboard.total_announcements = Announcement.objects.count()
        dashboard.accepted_announcements = Announcement.objects.filter(status='accepted').count()
        dashboard.rejected_announcements = Announcement.objects.filter(status='rejected').count()
        dashboard.total_orders = Order.objects.count()
        dashboard.completed_orders = Order.objects.filter(status='completed').count()
        dashboard.pending_orders = Order.objects.filter(status__in=['client_approved', 'in_process']).count()
        dashboard.total_clients = User.objects.filter(is_staff=False, is_superuser=False).count()
        dashboard.save()

        serializer = self.get_serializer(dashboard)
        return Response(serializer.data)

    @extend_schema(tags=["Dashboard"], responses={200: DashboardSerializer(many=True)})
    @action(detail=False, methods=['get'], permission_classes=[IsAdminUser])
    def weekly_stats(self, request):
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=6)

        dashboards = Dashboard.objects.filter(date__range=[start_date, end_date]).order_by('date')

        if dashboards.count() < 7:
            for i in range(7):
                current_date = start_date + timedelta(days=i)
                if not Dashboard.objects.filter(date=current_date).exists():
                    Dashboard.objects.create(
                        date=current_date,
                        total_announcements=Announcement.objects.filter(created_at__date=current_date).count(),
                        accepted_announcements=Announcement.objects.filter(status='accepted', updated_at__date=current_date).count(),
                        rejected_announcements=Announcement.objects.filter(status='rejected', updated_at__date=current_date).count(),
                        total_orders=Order.objects.filter(created_at__date=current_date).count(),
                        completed_orders=Order.objects.filter(status='completed', updated_at__date=current_date).count(),
                        pending_orders=Order.objects.filter(status__in=['client_approved', 'in_process'], created_at__date=current_date).count(),
                        total_clients=User.objects.filter(is_staff=False, is_superuser=False, date_joined__date__lte=current_date).count()
                    )
            dashboards = Dashboard.objects.filter(date__range=[start_date, end_date]).order_by('date')

        serializer = self.get_serializer(dashboards, many=True)
        return Response(serializer.data)

    @extend_schema(tags=["Dashboard"], responses={200: OpenApiResponse(description="User management stats")})
    @action(detail=False, methods=['get'], permission_classes=[IsAdminUser])
    def user_management(self, request):
        total_users = User.objects.count()
        clients = User.objects.filter(is_staff=False, is_superuser=False).count()
        managers = User.objects.filter(is_staff=True, is_superuser=False).count()
        admins = User.objects.filter(is_superuser=True).count()

        return Response({
            'total_users': total_users,
            'clients': clients,
            'managers': managers,
            'admins': admins
        })

    @extend_schema(
        tags=["Dashboard"],
        request={'user_id': {'type': 'integer'}},
        responses={200: OpenApiResponse(description="User promoted to manager")}
    )
    @action(detail=False, methods=['post'], permission_classes=[IsAdminUser])
    def make_manager(self, request):
        user_id = request.data.get('user_id')
        try:
            user = User.objects.get(id=user_id)
            if user.is_superuser:
                return Response({'detail': 'Cannot change admin role'}, status=status.HTTP_400_BAD_REQUEST)
            user.is_staff = True
            user.save()
            return Response({'detail': f'{user.username} promoted to manager'})
        except User.DoesNotExist:
            return Response({'detail': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

    @extend_schema(
        tags=["Dashboard"],
        request={'user_id': {'type': 'integer'}},
        responses={200: OpenApiResponse(description="Manager demoted to user")}
    )
    @action(detail=False, methods=['post'], permission_classes=[IsAdminUser])
    def remove_manager(self, request):
        user_id = request.data.get('user_id')
        try:
            user = User.objects.get(id=user_id)
            if user.is_superuser:
                return Response({'detail': 'Cannot change admin role'}, status=status.HTTP_400_BAD_REQUEST)
            user.is_staff = False
            user.save()
            return Response({'detail': f'{user.username} demoted to regular user'})
        except User.DoesNotExist:
            return Response({'detail': 'User not found'}, status=status.HTTP_404_NOT_FOUND)