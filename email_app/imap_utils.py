import imaplib
import email
from email.header import decode_header
from email.utils import parsedate_to_datetime
from django.conf import settings


def decode_mime_header(value):
    """Decode encoded email headers."""
    if not value:
        return ""
    decoded_parts = decode_header(value)
    result = []
    for part, charset in decoded_parts:
        if isinstance(part, bytes):
            try:
                result.append(part.decode(charset or 'utf-8', errors='replace'))
            except Exception:
                result.append(part.decode('utf-8', errors='replace'))
        else:
            result.append(part)
    return "".join(result)


def get_email_body(msg):
    """Extract plain text or HTML body from email message."""
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            disposition = str(part.get("Content-Disposition", ""))
            if "attachment" in disposition:
                continue
            if content_type == "text/plain":
                try:
                    body = part.get_payload(decode=True).decode(
                        part.get_content_charset() or 'utf-8', errors='replace'
                    )
                    break
                except Exception:
                    pass
            elif content_type == "text/html" and not body:
                try:
                    body = part.get_payload(decode=True).decode(
                        part.get_content_charset() or 'utf-8', errors='replace'
                    )
                except Exception:
                    pass
    else:
        try:
            body = msg.get_payload(decode=True).decode(
                msg.get_content_charset() or 'utf-8', errors='replace'
            )
        except Exception:
            body = ""
    return body


def fetch_inbox_emails(limit=50, folder="INBOX"):
    """
    Connect to Gmail via IMAP and fetch emails.
    Returns a list of dicts with email metadata and body.
    """
    username = settings.EMAIL_HOST_USER
    password = settings.EMAIL_HOST_PASSWORD

    emails = []

    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
        mail.login(username, password)
        mail.select(folder)

        # Search all emails, newest first
        status, data = mail.search(None, "ALL")
        if status != "OK":
            return []

        mail_ids = data[0].split()
        mail_ids = mail_ids[::-1][:limit]  # reverse for newest first, limit

        for mail_id in mail_ids:
            try:
                status, msg_data = mail.fetch(mail_id, "(RFC822)")
                if status != "OK":
                    continue

                raw_email = msg_data[0][1]
                msg = email.message_from_bytes(raw_email)

                # Parse date
                date_str = msg.get("Date", "")
                try:
                    date = parsedate_to_datetime(date_str)
                except Exception:
                    date = None

                emails.append({
                    "id": mail_id.decode(),
                    "from": decode_mime_header(msg.get("From", "")),
                    "to": decode_mime_header(msg.get("To", "")),
                    "subject": decode_mime_header(msg.get("Subject", "(No Subject)")),
                    "date": date,
                    "body": get_email_body(msg),
                    "is_read": "\\Seen" in (msg.get("Flags", "") or ""),
                })
            except Exception:
                continue

        mail.logout()

    except imaplib.IMAP4.error as e:
        return {"error": str(e)}

    return emails


def fetch_email_folders():
    """Return list of Gmail folders/labels."""
    username = settings.EMAIL_HOST_USER
    password = settings.EMAIL_HOST_PASSWORD
    folders = []
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
        mail.login(username, password)
        status, folder_list = mail.list()
        if status == "OK":
            for f in folder_list:
                parts = f.decode().split('"/"')
                if parts:
                    name = parts[-1].strip().strip('"')
                    folders.append(name)
        mail.logout()
    except Exception:
        pass
    return folders


def fetch_single_email(mail_id, folder="INBOX"):
    """Fetch a single email by ID."""
    username = settings.EMAIL_HOST_USER
    password = settings.EMAIL_HOST_PASSWORD
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
        mail.login(username, password)
        mail.select(folder)

        status, msg_data = mail.fetch(mail_id.encode(), "(RFC822)")
        if status != "OK":
            return None

        raw_email = msg_data[0][1]
        msg = email.message_from_bytes(raw_email)

        date_str = msg.get("Date", "")
        try:
            date = parsedate_to_datetime(date_str)
        except Exception:
            date = None

        result = {
            "id": mail_id,
            "from": decode_mime_header(msg.get("From", "")),
            "to": decode_mime_header(msg.get("To", "")),
            "cc": decode_mime_header(msg.get("Cc", "")),
            "subject": decode_mime_header(msg.get("Subject", "(No Subject)")),
            "date": date,
            "body": get_email_body(msg),
        }
        mail.logout()
        return result
    except Exception as e:
        return {"error": str(e)}