from django.urls import path
from . import views

app_name = 'email_app'

urlpatterns = [
    path('send/', views.send_email_view, name='send_email'),
    path('bulk/', views.bulk_email_view, name='bulk_email'),
    path('history/', views.email_history_view, name='email_history'),
    path('campaign/<int:pk>/', views.campaign_detail_view, name='campaign_detail'),
    path('campaign/<int:pk>/delete/', views.delete_campaign, name='delete_campaign'),
    path('campaign/delete-all/', views.delete_all_campaigns, name='delete_all_campaigns'),
    path('email/<int:pk>/delete/', views.delete_email, name='delete_email'),
    path('email/delete-all/', views.delete_all_emails, name='delete_all_emails'),
    path('inbox/', views.inbox_view, name='inbox'),
    path('inbox/<str:mail_id>/', views.inbox_detail_view, name='inbox_detail'),
    # 'test/' route removed — was an unauthenticated open email relay
]