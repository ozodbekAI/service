from rest_framework import serializers
from .models import Announcement, AnnouncementImage, Notification, Dashboard
from orders.serializers import OrderSerializer
from django.contrib.auth.models import User

from rest_framework import serializers
from .models import Announcement, AnnouncementImage, User

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'role']

class AnnouncementImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnnouncementImage
        fields = ['id', 'image', 'created_at']

class AnnouncementSerializer(serializers.ModelSerializer):
    client = UserSerializer(read_only=True)
    client_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source='client', write_only=True, required=False
    )
    accepted_by = UserSerializer(read_only=True)
    accepted_by_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source='accepted_by', write_only=True, allow_null=True, required=False
    )

    class Meta:
        model = Announcement
        fields = [
            'id', 'title', 'description', 'status', 'created_at', 'updated_at',
            'client', 'client_id', 'accepted_by', 'accepted_by_id', 'rejection_reason'
        ]

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'title', 'message', 'type', 'read', 'created_at', 'related_id']

class DashboardSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dashboard
        fields = ['id', 'date', 'total_announcements', 'accepted_announcements', 
                  'rejected_announcements', 'total_orders', 'completed_orders', 
                  'pending_orders', 'total_clients']
        read_only_fields = ['date']