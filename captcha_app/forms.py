# captcha_app/forms.py
from django import forms


class SecureForm(forms.Form):
    name = forms.CharField(
        max_length=100,
        label="Your Name",
        widget=forms.TextInput(attrs={
            'placeholder': 'e.g. Ajay Kumar Thakur',
            'autocomplete': 'name',
        })
    )
    message = forms.CharField(
        widget=forms.Textarea(attrs={
            'placeholder': 'Write your message here…',
            'rows': 5,
        }),
        label="Message"
    )
    captcha = forms.CharField(
        max_length=6,
        label="Enter the text in the image",
        widget=forms.TextInput(attrs={
            'placeholder': 'e.g.  A 3 b X 2',
            'autocomplete': 'off',
            'autocorrect': 'off',
            'autocapitalize': 'off',
            'spellcheck': 'false',
        })
    )