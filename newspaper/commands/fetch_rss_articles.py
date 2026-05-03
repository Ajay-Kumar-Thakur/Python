"""
Management command: fetch_rss_articles
Pulls articles from Nepali RSS feeds and saves them to the Article model.

Usage:
    python manage.py fetch_rss_articles
    python manage.py fetch_rss_articles --limit 20
    python manage.py fetch_rss_articles --category politics
    python manage.py fetch_rss_articles --featured   # marks first article as featured
"""

from django.core.management.base import BaseCommand
from django.utils.text import slugify
from django.utils import timezone
from django.contrib.auth.models import User

import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Fetch articles from Nepali RSS feeds and save to the database'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=30,
                            help='Max articles to import (default: 30)')
        parser.add_argument('--category', type=str, default=None,
                            help='Only fetch this category (e.g. politics, sports)')
        parser.add_argument('--featured', action='store_true',
                            help='Mark the most recent article as Featured')
        parser.add_argument('--breaking', type=int, default=3,
                            help='Mark first N articles as Breaking (default: 3)')
        parser.add_argument('--clear', action='store_true',
                            help='Delete all existing articles before importing')

    def handle(self, *args, **options):
        from newspaper.utils import NepaliNewsClient
        from newspaper.models import Article, Category, Author

        if options['clear']:
            count = Article.objects.count()
            Article.objects.all().delete()
            self.stdout.write(self.style.WARNING(f'Deleted {count} existing articles.'))

        # Ensure a default author exists
        author = self._get_or_create_author()

        client = NepaliNewsClient()
        limit = options['limit']
        category_filter = options['category']

        self.stdout.write('Fetching articles from RSS feeds...')

        if category_filter:
            raw_articles = client.fetch_by_category(category_filter, page_size=limit)
        else:
            raw_articles = client.fetch_top_headlines(page_size=limit)

        self.stdout.write(f'Fetched {len(raw_articles)} articles from RSS.')

        created = 0
        skipped = 0

        for i, data in enumerate(raw_articles):
            title = (data.get('title') or '').strip()
            if not title:
                skipped += 1
                continue

            # Generate a unique slug
            base_slug = slugify(title)[:200] or f'article-{i}'
            slug = base_slug
            counter = 2
            while Article.objects.filter(slug=slug).exists():
                slug = f'{base_slug}-{counter}'
                counter += 1

            # Get or create category
            cat_name = data.get('category') or 'world'
            category = self._get_or_create_category(cat_name)

            # Determine status
            if options['featured'] and i == 0:
                status = 'featured'
            else:
                status = 'published'

            # Mark breaking
            is_breaking = i < options['breaking']

            article = Article(
                title=title,
                slug=slug,
                excerpt=(data.get('description') or '')[:500],
                content=data.get('content') or data.get('description') or title,
                image_url=data.get('image_url') or '',
                category=category,
                author=author,
                status=status,
                is_breaking=is_breaking,
                published_at=timezone.now(),
            )
            article.save()
            created += 1

            if created % 5 == 0:
                self.stdout.write(f'  Saved {created} articles...')

        self.stdout.write(self.style.SUCCESS(
            f'\nDone! Created {created} articles, skipped {skipped}.'
        ))
        if created > 0:
            self.stdout.write(self.style.SUCCESS(
                'Visit http://127.0.0.1:8000/ to see your articles.'
            ))

    def _get_or_create_author(self):
        from newspaper.models import Author
        # Try to get existing author
        author = Author.objects.first()
        if author:
            return author

        # Create a staff user + author
        user, _ = User.objects.get_or_create(
            username='staff',
            defaults={
                'first_name': 'Staff',
                'last_name': 'Writer',
                'email': 'staff@thechronicle.com',
            }
        )
        author, _ = Author.objects.get_or_create(
            user=user,
            defaults={'bio': 'Staff writer at The Chronicle.'}
        )
        return author

    def _get_or_create_category(self, name: str):
        from newspaper.models import Category
        slug = slugify(name)
        category, _ = Category.objects.get_or_create(
            slug=slug,
            defaults={'name': name.title()}
        )
        return category