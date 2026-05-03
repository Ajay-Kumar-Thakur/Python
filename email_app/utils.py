from django.core.mail import send_mail
from django.utils import timezone
from django.conf import settings


def send_single_email(subject, message, recipient_email, from_email=None):
    """
    Send a single email. Returns (success: bool, error: str|None)
    """
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=from_email or settings.EMAIL_HOST_USER,
            recipient_list=[recipient_email],
            fail_silently=False,
        )
        return True, None
    except Exception as e:
        return False, str(e)


def send_bulk_emails(campaign):
    """
    Send emails for a BulkEmailCampaign instance.
    Updates campaign stats in place.
    """
    from .models import EmailMessage

    recipients = campaign.get_recipient_list()
    campaign.status = 'sending'
    campaign.total_recipients = len(recipients)
    campaign.save()

    sent = 0
    failed = 0

    for email in recipients:
        success, error = send_single_email(
            subject=campaign.subject,
            message=campaign.body,
            recipient_email=email,
        )

        EmailMessage.objects.create(
            sender=campaign.created_by,
            recipient_email=email,
            subject=campaign.subject,
            body=campaign.body,
            status='sent' if success else 'failed',
            error_message=error,
            sent_at=timezone.now() if success else None,
        )

        if success:
            sent += 1
        else:
            failed += 1

    campaign.sent_count = sent
    campaign.failed_count = failed
    campaign.status = 'completed' if failed == 0 else 'failed'
    campaign.completed_at = timezone.now()
    campaign.save()

    return sent, failed