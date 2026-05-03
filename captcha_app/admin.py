# captcha_app/admin.py
from django.contrib import admin
from .models import ContactSubmission


@admin.register(ContactSubmission)
class ContactSubmissionAdmin(admin.ModelAdmin):
    list_display  = ('name', 'submitted_at', 'ip_address')
    list_filter   = ('submitted_at',)
    search_fields = ('name', 'message')
    readonly_fields = ('submitted_at', 'ip_address')
    ordering      = ('-submitted_at',)