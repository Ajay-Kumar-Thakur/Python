from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from django.conf import settings
import logging
import re

logger = logging.getLogger(__name__)

def strip_ansi(text):
    return re.sub(r'\x1b\[[0-9;]*m', '', str(text))

def format_phone(number):
    number = number.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    if not number.startswith("+"):
        number = "+977" + number
    return number

def send_sms(to, message):
    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    try:
        client.messages.create(
            body=message,
            from_=settings.TWILIO_NUMBER,
            to=format_phone(to)
        )
        return True, None
    except TwilioRestException as e:
        clean_error = strip_ansi(e.msg)  # e.msg is cleaner than str(e)
        logger.error(f"Twilio error sending to {to}: {clean_error}")
        return False, clean_error