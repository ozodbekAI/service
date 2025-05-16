from django.conf import settings
from django.db import models
from django.contrib.auth.models import User
from application.models import Announcement
from products.models import Product

class Order(models.Model):
    STATUS_CHOICES = (
        ('client_approved', 'Client Approved'),
        ('in_process', 'In Process'),
        ('completed', 'Completed'),
        ('rejected', 'Rejected'),
    )

    client = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='orders')
    announcement = models.OneToOneField(Announcement, on_delete=models.CASCADE, related_name='order', null=True)
    title = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='client_approved')
    estimated_completion_time = models.IntegerField(null=True, blank=True)
    estimated_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    manager = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='managed_orders')
    start_time = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    rejection_reason = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.title

class OrderProduct(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='used_products')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.product.name} for {self.order.title}"