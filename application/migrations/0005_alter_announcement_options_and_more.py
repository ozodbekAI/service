# Generated by Django 5.2.1 on 2025-05-16 15:28

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('application', '0004_alter_notification_options_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='announcement',
            options={'ordering': ['-created_at']},
        ),
        migrations.AddField(
            model_name='announcement',
            name='estimated_completion_time',
            field=models.IntegerField(blank=True, help_text='Estimated completion time in hours', null=True),
        ),
        migrations.AddField(
            model_name='announcement',
            name='estimated_price',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
        migrations.AlterField(
            model_name='announcement',
            name='accepted_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='accepted_announcements', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='announcement',
            name='status',
            field=models.CharField(choices=[('pending', 'Pending'), ('accepted', 'Accepted'), ('in_process', 'In Process'), ('completed', 'Completed'), ('rejected', 'Rejected')], default='pending', max_length=20),
        ),
    ]
