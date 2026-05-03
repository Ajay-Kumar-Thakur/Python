# captcha_app/models.py
from django.db import models


class ContactSubmission(models.Model):
    name = models.CharField(max_length=100)
    message = models.TextField()
    submitted_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ['-submitted_at']
        verbose_name = "Contact Submission"
        verbose_name_plural = "Contact Submissions"

    def __str__(self):
        return f"{self.name} — {self.submitted_at.strftime('%Y-%m-%d %H:%M')}"