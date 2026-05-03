from django.urls import path
from .views import send_bulk_message

urlpatterns = [
    path('', send_bulk_message, name='send_bulk'),
]