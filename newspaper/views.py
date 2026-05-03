from django.shortcuts import render, get_object_or_404
from django.views.generic import ListView, DetailView
from django.db.models import Q, F
from django.core.cache import cache
from django.utils import timezone
from django.http import JsonResponse
from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Article, Category, Tag, Comment
from .serializers import ArticleSerializer, CategorySerializer
from .utils import NewsAPIClient, get_trending_articles
from django.conf import settings


class HomeView(ListView):
    model = Article
    template_name = 'news/home.html'
    context_object_name = 'articles'

    def get_queryset(self):
        return Article.objects.filter(
            status__in=['published', 'featured']
        ).select_related('category', 'author__user')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        qs = self.get_queryset()

        # Database articles
        ctx['featured'] = qs.filter(status='featured').first()
        ctx['breaking'] = qs.filter(is_breaking=True)[:5]
        ctx['top_stories'] = qs[:4]
        ctx['latest'] = qs[4:14]
        ctx['categories'] = Category.objects.all()
        ctx['trending'] = get_trending_articles(limit=5)

        # Always try to fetch live RSS articles — shown in "Live Updates" section
        try:
            newsapi_client = NewsAPIClient()
            if newsapi_client.api_key:
                headlines = newsapi_client.fetch_top_headlines(page_size=6)
                ctx['newsapi_headlines'] = headlines or []
                world = newsapi_client.fetch_by_category('world', page_size=3)
                ctx['newsapi_world'] = world or []
        except Exception as e:
            ctx['newsapi_headlines'] = []
            ctx['newsapi_world'] = []

        return ctx


class ArticleDetailView(DetailView):
    model = Article
    template_name = 'news/article_detail.html'
    context_object_name = 'article'

    def get_object(self):
        obj = get_object_or_404(Article, slug=self.kwargs['slug'])
        Article.objects.filter(pk=obj.pk).update(views=F('views') + 1)
        return obj

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        article = self.get_object()
        ctx['related'] = Article.objects.filter(
            category=article.category, status__in=['published', 'featured']
        ).exclude(pk=article.pk)[:4]
        ctx['comments'] = article.comments.filter(approved=True)
        ctx['trending'] = get_trending_articles(limit=5)

        try:
            newsapi_client = NewsAPIClient()
            if newsapi_client.api_key:
                ctx['related_news'] = newsapi_client.search_news(
                    article.category.name if article.category else 'news',
                    page_size=3
                )
        except Exception:
            ctx['related_news'] = []

        return ctx


class CategoryView(ListView):
    model = Article
    template_name = 'news/category.html'
    context_object_name = 'articles'
    paginate_by = 10

    def get_queryset(self):
        self.category = get_object_or_404(Category, slug=self.kwargs['slug'])
        return Article.objects.filter(
            category=self.category, status__in=['published', 'featured']
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['category'] = self.category
        ctx['categories'] = Category.objects.all()

        try:
            newsapi_client = NewsAPIClient()
            if newsapi_client.api_key:
                ctx['newsapi_articles'] = newsapi_client.fetch_by_category(
                    self.category.name,
                    page_size=6
                )
        except Exception:
            ctx['newsapi_articles'] = []

        return ctx


class SearchView(ListView):
    model = Article
    template_name = 'news/search.html'
    context_object_name = 'articles'
    paginate_by = 10

    def get_queryset(self):
        q = self.request.GET.get('q', '')
        if q:
            return Article.objects.filter(
                Q(title__icontains=q) | Q(content__icontains=q) | Q(excerpt__icontains=q),
                status__in=['published', 'featured']
            )
        return Article.objects.none()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        query = self.request.GET.get('q', '')
        ctx['query'] = query
        ctx['categories'] = Category.objects.all()

        try:
            newsapi_client = NewsAPIClient()
            if newsapi_client.api_key and query:
                ctx['newsapi_results'] = newsapi_client.search_news(query, page_size=10)
        except Exception:
            ctx['newsapi_results'] = []

        return ctx


class ArticleViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Article.objects.filter(
        status__in=['published', 'featured']
    ).select_related('category', 'author__user')
    serializer_class = ArticleSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'excerpt', 'content']
    ordering_fields = ['published_at', 'views']

    @action(detail=False, methods=['get'])
    def breaking(self, request):
        breaking = self.get_queryset().filter(is_breaking=True)
        serializer = self.get_serializer(breaking, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def trending(self, request):
        trending = self.get_queryset().order_by('-views')[:10]
        serializer = self.get_serializer(trending, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def newsapi(self, request):
        """Fetch live news from Nepali RSS feeds"""
        category = request.GET.get('category', 'general')
        client = NewsAPIClient()
        articles = client.fetch_top_headlines(category=category, page_size=20)
        return Response(articles)


# ── Debug / diagnostic view (remove in production) ──────────────────────────

def debug_rss(request):
    """
    Visit /debug-rss/ to verify RSS fetching works.
    Shows count + first 2 articles from the Nepali RSS client.
    Remove this view before going to production.
    """
    from .utils import NepaliNewsClient
    client = NepaliNewsClient()
    result = {}
    try:
        articles = client.fetch_top_headlines(page_size=10)
        result['status'] = 'ok'
        result['count'] = len(articles)
        result['sample'] = [
            {
                'title': a.get('title'),
                'source': a.get('source'),
                'image_url': a.get('image_url'),
                'url': a.get('url'),
            }
            for a in articles[:3]
        ]
    except Exception as e:
        result['status'] = 'error'
        result['error'] = str(e)

    from django.db.models import Count
    from .models import Article, Category
    result['db_articles'] = Article.objects.count()
    result['db_categories'] = Category.objects.count()
    result['published'] = Article.objects.filter(
        status__in=['published', 'featured']
    ).count()

    return JsonResponse(result, json_dumps_params={'indent': 2})