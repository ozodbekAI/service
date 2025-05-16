from django.urls import path, include
from rest_framework.routers import DefaultRouter
from application.views import AnnouncementImageViewSet, AnnouncementViewSet, NotificationViewSet, DashboardViewSet

router = DefaultRouter()
router.register(r'announcements-image', AnnouncementImageViewSet)
router.register(r'notifications', NotificationViewSet)
router.register(r'announcements', AnnouncementViewSet)
router.register(r'dashboard', DashboardViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('announcements/pending/', AnnouncementViewSet.as_view({'get': 'pending'}), name='pending-announcements'),
    path('announcements/managed/', AnnouncementViewSet.as_view({'get': 'managed'}), name='managed-announcements'),
    path('announcements/my_announcements/', AnnouncementViewSet.as_view({'get': 'my_announcements'}), name='my-announcements'),
]