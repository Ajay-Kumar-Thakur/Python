from django.shortcuts import render
from .models import Contact, Message
from .utils import send_sms

def send_bulk_message(request):
    if request.method == "POST":
        message_text = request.POST.get("message", "").strip()
        send_bulk = request.POST.get("send_bulk")

        errors = []

        if send_bulk:
            contacts = Contact.objects.all()
            for contact in contacts:
                success, error = send_sms(contact.phone, message_text)
                if not success:
                    errors.append({"phone": contact.phone, "error": error})
        else:
            phone = request.POST.get("phone_local", "").strip()
            if phone:
                success, error = send_sms(phone, message_text)
                if not success:
                    errors.append({"phone": phone, "error": error})

        Message.objects.create(content=message_text)

        if errors:
            return render(request, "messaging/success.html", {
                "errors": errors,
                "partial_success": True
            })

        return render(request, "messaging/success.html", {"partial_success": False})

    return render(request, "messaging/send.html")