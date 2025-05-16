from django.conf import settings
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

from django.contrib.auth import get_user_model

from products.models import Product

User = get_user_model()

class Announcement(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('in_process', 'In Process'),
        ('completed', 'Completed'),
        ('rejected', 'Rejected'),
    )

    client = models.ForeignKey(User, on_delete=models.CASCADE, related_name='announcements')
    title = models.CharField(max_length=255)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    accepted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='accepted_announcements')
    rejection_reason = models.TextField(blank=True, null=True)
    estimated_completion_time = models.IntegerField(null=True, blank=True, help_text="Estimated completion time in hours")
    estimated_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-created_at']

class AnnouncementProduct(models.Model):
    announcement = models.ForeignKey(Announcement, on_delete=models.CASCADE, related_name='used_products')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.product.name} for {self.announcement.title}"

class AnnouncementImage(models.Model):
    announcement = models.ForeignKey(Announcement, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='announcements/')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Image for {self.announcement.title}"

class Notification(models.Model):
    TYPE_CHOICES = [
        ('low_stock', 'Low Stock'),
        ('announcement_accepted', 'Announcement Accepted'),
        ('announcement_rejected', 'Announcement Rejected'),
        ('client_approved', 'Client Approved'),
        ('announcement_completed', 'Announcement Completed'),
        ('order_in_process', 'Order In Process'),
        ('order_completed', 'Order Completed'),
        ('order_rejected', 'Order Rejected'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=255)
    message = models.TextField()
    type = models.CharField(max_length=50, choices=TYPE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    read = models.BooleanField(default=False)
    related_id = models.IntegerField(null=True, blank=True)  # Links to announcement ID

    def __str__(self):
        return self.title

class Dashboard(models.Model):
    date = models.DateField(unique=True, default=timezone.now)
    total_announcements = models.IntegerField(default=0)
    accepted_announcements = models.IntegerField(default=0)
    rejected_announcements = models.IntegerField(default=0)
    total_orders = models.IntegerField(default=0)
    completed_orders = models.IntegerField(default=0)
    pending_orders = models.IntegerField(default=0)
    total_clients = models.IntegerField(default=0)

    def __str__(self):
        return f"Dashboard for {self.date}"

    class Meta:
        verbose_name = "Dashboard"
        verbose_name_plural = "Dashboards"
        ordering = ['-date']