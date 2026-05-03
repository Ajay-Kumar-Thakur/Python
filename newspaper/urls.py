from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'news'

router = DefaultRouter()
router.register(r'articles', views.ArticleViewSet, basename='article')

urlpatterns = [
    # This handles the main root URL: http://127.0.0.1:8000/
    path('', views.HomeView.as_view(), name='home'),          

    # Add this line to handle: http://127.0.0.1:8000/home/
    path('home/', views.HomeView.as_view()), 

    path('article/<slug:slug>/', views.ArticleDetailView.as_view(), name='article_detail'),
    path('category/<slug:slug>/', views.CategoryView.as_view(), name='category'),
    path('search/', views.SearchView.as_view(), name='search'),

    # REST API
    path('api/', include(router.urls)),

    # Debug (remove before production)
    path('debug-rss/', views.debug_rss, name='debug_rss'),
]