from django.db import models
from django.contrib.auth.models import AbstractUser

# Create your models here.


class User(AbstractUser):   
    username = models.CharField(max_length=100, blank=True, null=True)
    phone = models.CharField(max_length=13, blank=True, null=True)
    email = models.EmailField(unique=True)
    company_name = models.CharField(max_length=255, blank=True, null=True)
    is_legal = models.BooleanField(default=False)
    password = models.CharField(max_length=100)
    profile_image = models.ImageField(upload_to='profile_images/', blank=True, null=True)
    role = models.CharField(max_length=10, default='client')

    groups = models.ManyToManyField(
        'auth.Group',
        related_name='custom_user_set',
        blank=True,
        help_text='The groups this user belongs to.',
        verbose_name='groups',
    )
    
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='custom_user_set',
        blank=True,
        help_text='Specific permissions for this user.',
        verbose_name='user permissions',
    )

    USERNAME_FIELD = 'email' 
    REQUIRED_FIELDS = ['fullname', 'password']

    def __str__(self):
        return self.fullname