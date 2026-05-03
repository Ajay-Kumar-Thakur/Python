# views.py
import re
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import HttpResponseForbidden
from django.views.decorators.http import require_POST
from django.views.decorators.cache import never_cache
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.conf import settings

from .imap_utils import fetch_inbox_emails, fetch_single_email, fetch_email_folders
from .forms import SingleEmailForm, BulkEmailForm
from .models import EmailMessage, BulkEmailCampaign
from .utils import send_single_email, send_bulk_emails

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

# Compile once — used to block email header injection characters
_HEADER_INJECTION_RE = re.compile(r'[\r\n]')

def _sanitize_header(value: str) -> str:
    """Strip CR/LF to prevent email header injection attacks."""
    return _HEADER_INJECTION_RE.sub('', value).strip()


def _is_allowed_recipient(email: str) -> bool:
    """
    Validate the recipient email and optionally enforce a domain allowlist.
    Returns False if the address is invalid or on a blocked domain.
    """
    try:
        validate_email(email)
    except ValidationError:
        return False

    allowed_domains = getattr(settings, 'ALLOWED_EMAIL_DOMAINS', [])
    if allowed_domains:
        domain = email.split('@')[-1].lower()
        return domain in allowed_domains

    return True


def _check_email_ownership(email_obj, user):
    """Raise 403 if the email record does not belong to the requesting user."""
    if email_obj.sender != user:
        raise PermissionError


# ─────────────────────────────────────────────
# test_email: REMOVED from production code.
#
# The original view sent an email to a hardcoded address with no
# authentication, making the server an open email relay accessible
# by anyone. Remove this endpoint entirely. For development testing
# use Django's console email backend instead:
#   EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
# ─────────────────────────────────────────────


# ── Send a single email ────────────────────────────────────────────────────────
@never_cache
@login_required
def send_email_view(request):
    form = SingleEmailForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        recipient = form.cleaned_data['recipient_email'].lower().strip()
        subject   = _sanitize_header(form.cleaned_data['subject'])
        body      = form.cleaned_data['body']  # Body is not a header; no injection risk

        # Validate recipient before attempting to send
        if not _is_allowed_recipient(recipient):
            messages.error(request, 'Recipient email address is not permitted.')
            return render(request, 'email_app/send_email.html', {'form': form})

        success, error = send_single_email(subject, body, recipient)

        # Log the attempt — never log the body (may contain PII)
        if success:
            logger.info("Email sent by user=%s to=%s subject=%r",
                        request.user.id, recipient, subject[:60])
        else:
            logger.warning("Email failed user=%s to=%s error=%s",
                           request.user.id, recipient, error)

        EmailMessage.objects.create(
            sender=request.user,
            recipient_email=recipient,
            subject=subject,
            body=body,
            status='sent' if success else 'failed',
            error_message=error or '',
            sent_at=timezone.now() if success else None,
        )

        if success:
            messages.success(request, f'Email sent to {recipient}.')
        else:
            # Never expose the raw SMTP error to the user
            messages.error(request, 'Failed to send email. Please try again later.')

        return redirect('email_app:send_email')

    return render(request, 'email_app/send_email.html', {'form': form})


# ── Send bulk emails ───────────────────────────────────────────────────────────
@never_cache
@login_required
def bulk_email_view(request):
    form = BulkEmailForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        raw_recipients: list[str] = form.cleaned_data['recipient_list']

        # Enforce hard cap from settings
        max_recipients = getattr(settings, 'BULK_EMAIL_MAX_RECIPIENTS', 500)
        if len(raw_recipients) > max_recipients:
            messages.error(request,
                f'Recipient list exceeds the maximum of {max_recipients} addresses.')
            return render(request, 'email_app/bulk_email.html', {'form': form})

        # Filter out invalid / disallowed addresses before creating the campaign
        valid_recipients = [r for r in raw_recipients if _is_allowed_recipient(r)]
        invalid_count = len(raw_recipients) - len(valid_recipients)

        if not valid_recipients:
            messages.error(request, 'No valid recipient addresses found.')
            return render(request, 'email_app/bulk_email.html', {'form': form})

        subject = _sanitize_header(form.cleaned_data['subject'])
        name    = _sanitize_header(form.cleaned_data['campaign_name'])

        campaign = BulkEmailCampaign.objects.create(
            created_by=request.user,
            name=name,
            subject=subject,
            body=form.cleaned_data['body'],
           recipient_list=','.join(valid_recipients),
        )

        sent, failed = send_bulk_emails(campaign)

        logger.info("Bulk campaign id=%s user=%s sent=%d failed=%d skipped=%d",
                    campaign.pk, request.user.id, sent, failed, invalid_count)

        if invalid_count:
            messages.warning(request,
                f'{invalid_count} address(es) were skipped (invalid or disallowed).')

        if failed == 0:
            messages.success(request, f'Campaign sent — {sent} emails delivered.')
        else:
            messages.warning(request, f'Sent: {sent}, Failed: {failed}. Check the history.')

        return redirect('email_app:email_history')

    return render(request, 'email_app/bulk_email.html', {'form': form})


# ── Email history ──────────────────────────────────────────────────────────────
@never_cache
@login_required
def email_history_view(request):
    # Filter strictly by the authenticated user — never expose other users' data
    emails    = EmailMessage.objects.filter(sender=request.user).order_by('-created_at')
    campaigns = BulkEmailCampaign.objects.filter(created_by=request.user).order_by('-created_at')
    return render(request, 'email_app/email_history.html', {
        'emails': emails,
        'campaigns': campaigns,
    })


# ── Campaign detail ────────────────────────────────────────────────────────────
@never_cache
@login_required
def campaign_detail_view(request, pk):
    campaign = get_object_or_404(BulkEmailCampaign, pk=pk, created_by=request.user)

    # Filter strictly by this user + this campaign's subject + created after campaign start
    # (Until a proper FK is added to EmailMessage, this is the safest available query)
    logs = EmailMessage.objects.filter(
        sender=request.user,
        subject=campaign.subject,
        created_at__gte=campaign.created_at,
    ).order_by('-created_at')

    return render(request, 'email_app/campaign_detail.html', {
        'campaign': campaign,
        'logs': logs,
    })


# ── Delete a single campaign ───────────────────────────────────────────────────
@login_required
@require_POST
def delete_campaign(request, pk):
    campaign = get_object_or_404(BulkEmailCampaign, pk=pk, created_by=request.user)
    campaign.delete()
    messages.success(request, 'Campaign deleted.')
    return redirect('email_app:email_history')


# ── Delete a single email record ──────────────────────────────────────────────
@login_required
@require_POST
def delete_email(request, pk):
    email = get_object_or_404(EmailMessage, pk=pk, sender=request.user)
    email.delete()
    messages.success(request, 'Email record deleted.')
    return redirect('email_app:email_history')


# ── Delete ALL campaigns for this user ────────────────────────────────────────
@login_required
@require_POST
def delete_all_campaigns(request):
    count, _ = BulkEmailCampaign.objects.filter(created_by=request.user).delete()
    messages.success(request, f'{count} campaign(s) deleted.')
    return redirect('email_app:email_history')


# ── Delete ALL individual email records for this user ─────────────────────────
@login_required
@require_POST
def delete_all_emails(request):
    count, _ = EmailMessage.objects.filter(sender=request.user).delete()
    messages.success(request, f'{count} email record(s) deleted.')
    return redirect('email_app:email_history')


# ── Gmail Inbox ────────────────────────────────────────────────────────────────
@never_cache
@login_required
def inbox_view(request):
    folder = request.GET.get('folder', 'INBOX')
    # Hard cap prevents a user from issuing a huge IMAP fetch as a DoS vector
    max_limit = getattr(settings, 'INBOX_FETCH_MAX', 200)
    try:
        limit = min(int(request.GET.get('limit', 50)), max_limit)
    except (ValueError, TypeError):
        limit = 50

    # Validate folder name — only allow alphanumeric, dots, slashes, brackets, spaces
    if not re.match(r'^[\w\s./\[\]-]{1,100}$', folder):
        messages.error(request, 'Invalid folder name.')
        return redirect('email_app:inbox')

    result  = fetch_inbox_emails(limit=limit, folder=folder)
    folders = fetch_email_folders()

    error  = None
    emails = []

    if isinstance(result, dict) and 'error' in result:
        # Log the real error internally; show a generic message to the user
        logger.error("IMAP fetch error for user=%s: %s", request.user.id, result['error'])
        error = 'Could not load inbox. Please try again later.'
    else:
        emails = result

    return render(request, 'email_app/inbox.html', {
        'emails': emails,
        'folders': folders,
        'current_folder': folder,
        'limit': limit,
        'error': error,
        'limit_choices': [25, 50, 100, 200],
        # Never expose the raw email address in the template if avoidable;
        # use the authenticated user's display name instead.
        'connected_email': settings.EMAIL_HOST_USER,
    })


# ── Single Email Detail ────────────────────────────────────────────────────────
@never_cache
@login_required
def inbox_detail_view(request, mail_id):
    folder = request.GET.get('folder', 'INBOX')

    # Validate mail_id is numeric before passing to IMAP
    if not str(mail_id).isdigit():
        messages.error(request, 'Invalid email ID.')
        return redirect('email_app:inbox')

    # Validate folder name as above
    if not re.match(r'^[\w\s./\[\]-]{1,100}$', folder):
        messages.error(request, 'Invalid folder name.')
        return redirect('email_app:inbox')

    email_data = fetch_single_email(mail_id, folder=folder)

    if not email_data or 'error' in email_data:
        logger.warning("Could not load email id=%s user=%s", mail_id, request.user.id)
        messages.error(request, 'Could not load that email.')
        return redirect('email_app:inbox')

    return render(request, 'email_app/inbox_detail.html', {
        'email': email_data,
        'folder': folder,
    })