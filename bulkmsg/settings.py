# settings.py
from pathlib import Path
from dotenv import load_dotenv
import os
import secrets

load_dotenv(Path(__file__).resolve().parent.parent / '.env')


BASE_DIR = Path(__file__).resolve().parent.parent

# ── Critical: never hardcode this. Generate once with:
#    python -c "import secrets; print(secrets.token_urlsafe(50))"
#    then store in your .env file as DJANGO_SECRET_KEY
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY')
if not SECRET_KEY:
    raise RuntimeError("DJANGO_SECRET_KEY environment variable is not set.")

# ── Never True in production
DEBUG = os.getenv('DEBUG', 'False') == 'True'

# ── Must list real hostnames; empty list accepts ANY Host header (HTTP Host injection)
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '').split(',')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'messaging',
    'captcha_app',
    'rest_framework',
    'newspaper',
    'users',
    'email_app',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    # ── Whitenoise serves static files securely (also sets immutable cache headers)
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # ── Rate limiting middleware (django-ratelimit or django-axes)
    # 'axes.middleware.AxesMiddleware',  # brute-force protection
]

ROOT_URLCONF = 'bulkmsg.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'newspaper' / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'bulkmsg.wsgi.application'

# ── Use PostgreSQL in production, never SQLite
_db_engine = os.getenv('DB_ENGINE', 'django.db.backends.sqlite3')

DATABASES = {
    'default': {
        'ENGINE': _db_engine,
        'NAME': os.getenv('DB_NAME', str(BASE_DIR / 'db.sqlite3')),
        'USER': os.getenv('DB_USER', ''),
        'PASSWORD': os.getenv('DB_PASSWORD', ''),
        'HOST': os.getenv('DB_HOST', ''),
        'PORT': os.getenv('DB_PORT', ''),
        # connect_timeout is only valid for PostgreSQL/MySQL, not SQLite
        'OPTIONS': {} if 'sqlite3' in _db_engine else {'connect_timeout': 10},
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
     'OPTIONS': {'min_length': 12}},  # Stronger minimum
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ── Session security
SESSION_COOKIE_HTTPONLY = True       # Blocks JS from reading the session cookie
SESSION_COOKIE_SECURE = not DEBUG    # HTTPS-only in production
SESSION_COOKIE_SAMESITE = 'Lax'      # CSRF protection for cross-site requests
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_AGE = 3600            # 1 hour idle timeout

# ── CSRF protection
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SAMESITE = 'Lax'

# ── Security headers (applied by SecurityMiddleware)
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# Enable HSTS only in production (tells browsers to always use HTTPS)
if not DEBUG:
    SECURE_HSTS_SECONDS = 31536000          # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_SSL_REDIRECT = True              # Redirect all HTTP → HTTPS

# ── Content Security Policy (install django-csp)
# CSP_DEFAULT_SRC = ("'self'",)
# CSP_STYLE_SRC = ("'self'",)
# CSP_SCRIPT_SRC = ("'self'",)
# CSP_IMG_SRC = ("'self'", "data:")

# ── Twilio — load from environment ONLY; never commit these values
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN  = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_NUMBER      = os.getenv('TWILIO_NUMBER')
TEST_RECIPIENT     = os.getenv('TEST_RECIPIENT')

if not DEBUG and not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_NUMBER]):
    raise RuntimeError("Twilio credentials are not fully configured.")

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

LOGIN_URL = '/users/login/'
LOGIN_REDIRECT_URL = '/users/profile/'
LOGOUT_REDIRECT_URL = '/users/login/'

# ── Email — credentials from .env only
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER     = os.getenv('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')

if not EMAIL_HOST_USER or not EMAIL_HOST_PASSWORD:
    raise RuntimeError("Email credentials (EMAIL_HOST_USER / EMAIL_HOST_PASSWORD) are not set.")

# IMAP settings
IMAP_HOST = 'imap.gmail.com'
IMAP_PORT = 993

# ── Allowed recipient domains (whitelist). Set in .env as comma-separated list.
#    Leave empty to allow all domains (not recommended for production).
ALLOWED_EMAIL_DOMAINS = [
    d.strip() for d in os.getenv('ALLOWED_EMAIL_DOMAINS', '').split(',') if d.strip()
]

# ── Max recipients per bulk campaign
BULK_EMAIL_MAX_RECIPIENTS = int(os.getenv('BULK_EMAIL_MAX_RECIPIENTS', '500'))

# ── Inbox fetch hard cap (prevents IMAP memory DoS)
INBOX_FETCH_MAX = int(os.getenv('INBOX_FETCH_MAX', '200'))

NEPALI_NEWS_SOURCES = [
    'himalayan_times', 'kathmandupost', 'myrepublica',
    'kantipur', 'onlinekhabar', 'setopati', 'ratopati',
]
NEPALI_NEWS_CACHE_TTL = 1800