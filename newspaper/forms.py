from django import forms
from .models import Comment


class CommentForm(forms.ModelForm):
    """Submitted via the Leave a Comment section on article detail pages."""

    name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'placeholder': 'Your Name *',
            'class': 'comment-input',
        })
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'placeholder': 'Email Address *',
            'class': 'comment-input',
        })
    )
    content = forms.CharField(
        widget=forms.Textarea(attrs={
            'placeholder': 'Share your thoughts…',
            'class': 'comment-textarea',
            'rows': 5,
        })
    )

    class Meta:
        model = Comment
        fields = ['name', 'email', 'content']


class SearchForm(forms.Form):
    """Used by SearchView; mirrors the nav search input."""

    q = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Search headlines, topics, reporters…',
        })
    )