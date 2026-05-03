from django.db import models
from django.contrib.auth.models import User
import re


class BulkEmailCampaign(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('sending', 'Sending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='campaigns')
    name = models.CharField(max_length=255)
    subject = models.CharField(max_length=255)
    body = models.TextField()
    recipient_list = models.TextField(help_text="Comma-separated email addresses")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft')
    total_recipients = models.IntegerField(default=0)
    sent_count = models.IntegerField(default=0)
    failed_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} [{self.status}]"

    def get_recipient_list(self):          # ← indented inside the class
        return [e.strip() for e in re.split(r'[\n\r,]+', self.recipient_list) if e.strip()]


class EmailMessage(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
    ]

    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_emails')
    campaign = models.ForeignKey(
        BulkEmailCampaign,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='email_logs',
    )
    recipient_email = models.EmailField()
    subject = models.CharField(max_length=255)
    body = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    error_message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.subject} → {self.recipient_email} [{self.status}]"