from django.core.cache import cache
from django.utils.text import slugify
import re
import requests
import feedparser
import logging
import xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import parsedate_to_datetime
from django.conf import settings

logger = logging.getLogger(__name__)

# ── existing helpers (unchanged) ─────────────────────────────────────────────

def unique_slug(model_class, title: str, slug_field: str = 'slug') -> str:
    base = slugify(title)
    slug = base
    counter = 2
    while model_class.objects.filter(**{slug_field: slug}).exists():
        slug = f'{base}-{counter}'
        counter += 1
    return slug

def reading_time(text: str, wpm: int = 200) -> int:
    word_count = len(re.findall(r'\w+', text))
    return max(1, round(word_count / wpm))

TRENDING_CACHE_KEY = 'chronicle:trending_articles'
TRENDING_CACHE_TTL = 60 * 15

def get_trending_articles(limit: int = 5):
    from .models import Article
    cached = cache.get(TRENDING_CACHE_KEY)
    if cached is not None:
        return cached[:limit]
    qs = list(
        Article.objects
        .filter(status__in=['published', 'featured'])
        .order_by('-views')
        .select_related('category', 'author__user')[:20]
    )
    cache.set(TRENDING_CACHE_KEY, qs, TRENDING_CACHE_TTL)
    return qs[:limit]

def invalidate_trending_cache():
    cache.delete(TRENDING_CACHE_KEY)

def strip_html(html: str) -> str:
    return re.sub(r'<[^>]+>', '', html)

def auto_excerpt(content: str, word_limit: int = 40) -> str:
    plain = strip_html(content).strip()
    words = plain.split()
    if len(words) <= word_limit:
        return plain
    return ' '.join(words[:word_limit]) + '…'

def highlight_query(text: str, query: str, tag: str = 'mark') -> str:
    if not query:
        return text
    for word in query.split():
        pattern = re.compile(re.escape(word), re.IGNORECASE)
        text = pattern.sub(lambda m: f'<{tag}>{m.group()}</{tag}>', text)
    return text


# ── Nepali News RSS Feeds ─────────────────────────────────────────────────────

NEPALI_RSS_FEEDS = {
    # English-language Nepali outlets
    'himalayan_times': {
        'name': 'The Himalayan Times',
        'feeds': {
            'general':       'https://thehimalayantimes.com/feed/',
            'politics':      'https://thehimalayantimes.com/nepal/feed/',
            'business':      'https://thehimalayantimes.com/business/feed/',
            'sports':        'https://thehimalayantimes.com/sports/feed/',
            'technology':    'https://thehimalayantimes.com/technology/feed/',
            'world':         'https://thehimalayantimes.com/world/feed/',
        },
    },
    'myrepublica': {
        'name': 'My Republica',
        'feeds': {
            'general':       'https://myrepublica.nagariknetwork.com/feed/',
            'politics':      'https://myrepublica.nagariknetwork.com/category/politics/feed/',
            'business':      'https://myrepublica.nagariknetwork.com/category/business/feed/',
            'sports':        'https://myrepublica.nagariknetwork.com/category/sports/feed/',
            'world':         'https://myrepublica.nagariknetwork.com/category/world/feed/',
        },
    },
    'kathmandupost': {
        'name': 'The Kathmandu Post',
        'feeds': {
            'general':       'https://kathmandupost.com/rss',
            'politics':      'https://kathmandupost.com/politics/rss',
            'business':      'https://kathmandupost.com/money/rss',
            'sports':        'https://kathmandupost.com/sports/rss',
            'world':         'https://kathmandupost.com/world/rss',
        },
    },
    # Nepali-language outlets
    'kantipur': {
        'name': 'Kantipur',
        'feeds': {
            'general':       'https://ekantipur.com/rss',
            'politics':      'https://ekantipur.com/koseli/rss',  # closest public feed
        },
    },
    'onlinekhabar': {
        'name': 'Online Khabar',
        'feeds': {
            'general':       'https://www.onlinekhabar.com/feed',
            'politics':      'https://www.onlinekhabar.com/content/political-news/feed',
            'sports':        'https://www.onlinekhabar.com/content/sports/feed',
            'entertainment': 'https://www.onlinekhabar.com/content/entertainment/feed',
            'business':      'https://www.onlinekhabar.com/content/economy/feed',
        },
    },
    'setopati': {
        'name': 'Setopati',
        'feeds': {
            'general':       'https://www.setopati.com/rss.xml',
        },
    },
    'ratopati': {
        'name': 'Ratopati',
        'feeds': {
            'general':       'https://ratopati.com/rss',
        },
    },
}

# Maps your Category slugs/names → which feed key to pull
CATEGORY_FEED_MAP = {
    'politics':      'politics',
    'business':      'business',
    'sports':        'sports',
    'technology':    'technology',
    'world':         'world',
    'entertainment': 'entertainment',
    'health':        'general',
    'science':       'general',
    'culture':       'entertainment',
}
class NepaliNewsClient:
    def __init__(self):
        self.feeds = {
            'kantipur': 'https://ekantipur.com/feed',
            'onlinekhabar': 'https://english.onlinekhabar.com/feed', 
            'ratopati': 'https://english.ratopati.com/feed',
            'kathmandupost': 'https://kathmandupost.com/feed/',
            'setopati': 'https://www.setopati.com/feed', # Switched to Nepali feed as English is 500ing
        }
        
        # Enhanced headers to bypass strict security on Ekantipur/Kathmandu Post
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Referer': 'https://www.google.com/',
            'Connection': 'keep-alive',
        }

    def _fetch_feed(self, url):
        try:
            # Use a session for better persistence
            session = requests.Session()
            response = session.get(url, headers=self.headers, timeout=20)
            
            # If the site returns 500 or 404, just skip it quietly
            if response.status_code != 200:
                return []

            # Use response.text instead of content to handle encoding (fixes "invalid token")
            feed_data = response.text
            
            # Parse the text
            feed = feedparser.parse(feed_data)
            
            # If it fails to parse but we have data, try cleaning it
            if not feed.entries and '<?xml' in feed_data:
                # Basic fix for some common XML encoding issues
                feed_data = feed_data.strip()
                feed = feedparser.parse(feed_data)
                
            return feed.entries
            
        except Exception as e:
            # Silently handle connection errors to keep the console clean
            return []

    def _process_entries(self, entries, source_name, category='General', limit=10):
        articles = []
        for entry in entries[:limit]:
            title = getattr(entry, 'title', '').strip()
            if not title:
                continue
                
            description = getattr(entry, 'summary', '')
            
            # Extract content
            if hasattr(entry, 'content'):
                content = entry.content[0].get('value', description)
            else:
                content = description
            
            # Extract image URL logic
            image_url = ''
            if hasattr(entry, 'media_content'):
                image_url = entry.media_content[0].get('url', '')
            elif hasattr(entry, 'links'):
                for link in entry.links:
                    if 'image' in link.get('type', ''):
                        image_url = link.get('href', '')
                        break
            
            # If no image found, check the summary for <img> tags
            if not image_url and '<img' in description:
                try:
                    import re
                    img_match = re.search(r'<img.+?src=["\'](.+?)["\']', description)
                    if img_match:
                        image_url = img_match.group(1)
                except:
                    pass
                        
            articles.append({
                'title': title,
                'description': description,
                'content': content,
                'image_url': image_url,
                'category': category,
                'source': source_name,
            })
            
        return articles

    def fetch_top_headlines(self, page_size=30):
        all_articles = []
        # Try to get roughly equal articles from each source
        limit_per_feed = max(5, page_size // 4) 
        
        for source, url in self.feeds.items():
            entries = self._fetch_feed(url)
            if entries:
                articles = self._process_entries(entries, source, limit=limit_per_feed)
                all_articles.extend(articles)
                
        return all_articles[:page_size]

    def fetch_by_category(self, category, page_size=30):
        all_articles = []
        limit_per_feed = max(5, page_size // 4)
        
        for source, url in self.feeds.items():
            entries = self._fetch_feed(url)
            if entries:
                articles = self._process_entries(entries, source, category=category, limit=limit_per_feed)
                all_articles.extend(articles)
                
        return all_articles[:page_size]

    def search_news(self, query, page_size=20):
        """Search across cached general headlines (no server-side full-text search in RSS)."""
        cache_key = f'{self.CACHE_PREFIX}:search:{query.lower()}:{page_size}'
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        all_articles = self._fetch_multi('general', page_size * 3)
        q_lower = query.lower()
        results = [
            a for a in all_articles
            if q_lower in a['title'].lower() or q_lower in (a['description'] or '').lower()
        ][:page_size]

        cache.set(cache_key, results, self.cache_ttl // 2)   # shorter TTL for search
        return results

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _cached(self, key, loader):
        result = cache.get(key)
        if result is not None:
            return result
        result = loader()
        cache.set(key, result, self.cache_ttl)
        return result

    def _fetch_multi(self, feed_key: str, limit: int) -> list:
        """Fetch `feed_key` from all configured sources and merge/sort."""
        articles = []
        per_source = max(5, limit // len(self.sources) + 1)

        for source_key in self.sources:
            source = NEPALI_RSS_FEEDS.get(source_key)
            if not source:
                continue
            feeds = source['feeds']
            url = feeds.get(feed_key) or feeds.get('general')
            if not url:
                continue
            try:
                items = self._parse_rss(url, source['name'], per_source)
                articles.extend(items)
            except Exception as e:
                logger.warning(f"[NepaliNews] {source_key}/{feed_key} failed: {e}")

        # Sort newest-first, deduplicate by title
        seen, unique = set(), []
        for a in sorted(articles, key=lambda x: x.get('_ts', 0), reverse=True):
            key = a['title'].strip().lower()[:80]
            if key not in seen:
                seen.add(key)
                unique.append(a)

        return unique[:limit]

    def _parse_rss(self, url: str, source_name: str, limit: int) -> list:
        """Fetch and parse an RSS 2.0 / Atom feed."""
        headers = {'User-Agent': 'Mozilla/5.0 (compatible; TheChronicle/1.0)'}
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()

        root = ET.fromstring(resp.content)
        ns = {
            'media': 'http://search.yahoo.com/mrss/',
            'dc':    'http://purl.org/dc/elements/1.1/',
            'content': 'http://purl.org/rss/1.0/modules/content/',
        }

        # Support both RSS <channel><item> and Atom <entry>
        items = root.findall('.//item') or root.findall('.//{http://www.w3.org/2005/Atom}entry')
        results = []

        for item in items[:limit]:
            def g(tag, default=''):
                el = item.find(tag)
                return (el.text or '').strip() if el is not None else default

            title       = g('title') or g('{http://www.w3.org/2005/Atom}title')
            link        = g('link')  or g('{http://www.w3.org/2005/Atom}link')
            description = strip_html(g('description') or g('{http://www.w3.org/2005/Atom}summary'))
            pub_date    = g('pubDate') or g('pubdate') or g('{http://www.w3.org/2005/Atom}published')

            if not title or title == '[Removed]':
                continue

            # Parse timestamp for sorting
            ts = self._parse_date(pub_date)

            # Image: try <media:content>, <media:thumbnail>, <enclosure>, og in description
            image_url = None
            media_el = item.find('media:content', ns) or item.find('media:thumbnail', ns)
            if media_el is not None:
                image_url = media_el.get('url')
            if not image_url:
                enc = item.find('enclosure')
                if enc is not None and 'image' in (enc.get('type') or ''):
                    image_url = enc.get('url')
            if not image_url:
                # Try to pull first <img> from raw description HTML
                raw_desc = g('description')
                m = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', raw_desc)
                if m:
                    image_url = m.group(1)

            results.append({
                'title':        title,
                'description':  description[:300] if description else '',
                'content':      '',
                'url':          link or '#',
                'image_url':    image_url if image_url and image_url.startswith('http') else None,
                'source':       source_name,
                'author':       g('{http://purl.org/dc/elements/1.1/}creator') or source_name,
                'published_at': pub_date,
                'category':     self._guess_category({'title': title, 'description': description}),
                '_ts':          ts,   # internal sort key, stripped before returning
            })

        # Strip internal sort key
        for r in results:
            r.pop('_ts', None)

        return results

    @staticmethod
    def _parse_date(date_str: str):
        """Parse RFC 2822 or ISO 8601 date strings; fall back to epoch 0."""
        if not date_str:
            return datetime.min
        for parser in (parsedate_to_datetime, lambda s: datetime.fromisoformat(s.rstrip('Z'))):
            try:
                return parser(date_str)
            except Exception:
                continue
        return datetime.min

    @staticmethod
    def _guess_category(article: dict) -> str:
        text = f"{article.get('title','')} {article.get('description','')}".lower()
        checks = [
            ('politics',      ['politics', 'election', 'government', 'prime minister', 'parliament', 'rajniti']),
            ('business',      ['business', 'economy', 'stock', 'market', 'finance', 'arthik']),
            ('sports',        ['sports', 'cricket', 'football', 'khel']),
            ('technology',    ['technology', 'tech', 'digital', 'software', 'ai', 'app']),
            ('science',       ['science', 'research', 'climate', 'space', 'scientist']),
            ('entertainment', ['entertainment', 'music', 'film', 'movie', 'culture', 'manoranajan']),
            ('health',        ['health', 'hospital', 'covid', 'medical', 'swasthya']),
        ]
        for cat, keywords in checks:
            if any(kw in text for kw in keywords):
                return cat
        return 'world'


# ── Backwards-compat alias so views.py needs zero changes ────────────────────
NewsAPIClient = NepaliNewsClient