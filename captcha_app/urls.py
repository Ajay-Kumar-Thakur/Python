# captcha_app/urls.py
from django.urls import path
from . import views

urlpatterns = [
      path('contact/', views.contact_view, name='contact'),
    path('captcha/image/', views.captcha_image_view, name='captcha_image'),
]