# captcha_app/views.py
from django.shortcuts import render
from django.http import HttpResponse
from .utils import generate_random_string, generate_captcha_image
from .forms import SecureForm
from .models import ContactSubmission


def get_client_ip(request):
    """Extract the real client IP, handling proxies."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def captcha_image_view(request):
    """Generates a fresh CAPTCHA image and stores the answer in the session."""
    captcha_text = generate_random_string()
    request.session['captcha_text'] = captcha_text

    image_bytes = generate_captcha_image(captcha_text)
    return HttpResponse(image_bytes, content_type="image/png")


def contact_view(request):
    """
    Displays the contact form.
    Data is saved to the database ONLY after CAPTCHA is verified.
    """
    success_message = None
    error_message = None

    if request.method == 'POST':
        form = SecureForm(request.POST)

        if form.is_valid():
            user_captcha = form.cleaned_data.get('captcha', '').strip()

            # Pop removes the key after one use — prevents replay attacks
            real_captcha = request.session.pop('captcha_text', None)

            if not real_captcha:
                # Session expired or captcha was never generated
                error_message = "Session expired. Please refresh the CAPTCHA and try again."

            elif user_captcha.lower() != real_captcha.lower():
                # Wrong answer — do NOT save anything
                error_message = "Incorrect security code. Please try again."

            else:
                # ✅ CAPTCHA verified — now safe to save to the database
                ContactSubmission.objects.create(
                    name=form.cleaned_data['name'],
                    message=form.cleaned_data['message'],
                    ip_address=get_client_ip(request),
                )
                success_message = "Your message has been received. We'll be in touch soon."
                form = SecureForm()  # Reset form after successful submission
        else:
            error_message = "Please correct the errors below."

    else:
        form = SecureForm()

    return render(request, 'captcha_app/contact.html', {
        'form': form,
        'success_message': success_message,
        'error_message': error_message,
    })