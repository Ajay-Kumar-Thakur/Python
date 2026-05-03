from django.contrib import admin
from .models import EmailMessage, BulkEmailCampaign


@admin.register(EmailMessage)
class EmailMessageAdmin(admin.ModelAdmin):
    list_display = ('subject', 'recipient_email', 'sender', 'status', 'created_at', 'sent_at')
    list_filter = ('status', 'created_at')
    search_fields = ('subject', 'recipient_email', 'sender__username')
    readonly_fields = ('created_at', 'sent_at', 'error_message')
    ordering = ('-created_at',)


@admin.register(BulkEmailCampaign)
class BulkEmailCampaignAdmin(admin.ModelAdmin):
    list_display = ('name', 'subject', 'created_by', 'status', 'total_recipients', 'sent_count', 'failed_count', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('name', 'subject', 'created_by__username')
    readonly_fields = ('created_at', 'completed_at', 'total_recipients', 'sent_count', 'failed_count')
    ordering = ('-created_at',)