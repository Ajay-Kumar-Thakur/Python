from django import forms
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
import re


class SingleEmailForm(forms.Form):
    recipient_email = forms.EmailField(
        label='Recipient Email',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'receiver@example.com'
        })
    )
    subject = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email Subject'
        })
    )
    body = forms.CharField(
        label='Message',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 6,
            'placeholder': 'Write your message here...'
        })
    )


class BulkEmailForm(forms.Form):
    campaign_name = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Campaign Name'
        })
    )
    subject = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email Subject'
        })
    )
    recipient_list = forms.CharField(
        label='Recipients',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 6,
            'placeholder': 'One email per line or comma-separated:\najaythakurjhabrahman@gmail.com\najaythakurniit1@gmail.com',
        }),
        help_text='Enter one email per line, or separate with commas.'
    )
    body = forms.CharField(
        label='Message',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 6,
            'placeholder': 'Write your message here...'
        })
    )

    def clean_recipient_list(self):
        raw = self.cleaned_data.get('recipient_list', '')

        # Split on commas, newlines, or both mixed together
        emails = [e.strip() for e in re.split(r'[\n\r,]+', raw) if e.strip()]

        if not emails:
            raise forms.ValidationError(
                'Please enter at least one recipient email address.'
            )

        valid = []
        invalid = []
        seen = set()

        for email in emails:
            email = email.lower()
            try:
                validate_email(email)
                if email not in seen:          # silently deduplicate
                    valid.append(email)
                    seen.add(email)
            except ValidationError:
                invalid.append(email)

        if invalid:
            raise forms.ValidationError(
                f"Invalid email address(es): {', '.join(invalid)}"
            )

        return valid  # views.py receives a clean Python list