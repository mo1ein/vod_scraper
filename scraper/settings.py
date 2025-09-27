from pathlib import Path
import os
from urllib.parse import urlparse

# Base path resolution and load .env from project root
BASE_DIR = Path(__file__).resolve().parent.parent
env_path = BASE_DIR / '.env'
if env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=env_path)

BOT_NAME = 'vod_scraper'

SPIDER_MODULES = ['scraper.spiders']
NEWSPIDER_MODULE = 'scraper.spiders'

# --- Scraper runtime flags & scheduling (from env) ---
SCRAPER_ENABLED = str(os.environ.get('SCRAPER_ENABLED', 'false')).lower() in ('1', 'true', 'yes')
try:
    SCRAPER_INTERVAL = int(os.environ.get('SCRAPER_INTERVAL', 120))
except ValueError:
    SCRAPER_INTERVAL = 120

# --- Scrapy throttle / concurrency from env ---
try:
    DOWNLOAD_DELAY = float(os.environ.get('SCRAPER_DOWNLOAD_DELAY', 1.0))
except ValueError:
    DOWNLOAD_DELAY = 1.0

try:
    CONCURRENT_REQUESTS = int(os.environ.get('SCRAPER_CONCURRENT_REQUESTS', 1))
except ValueError:
    CONCURRENT_REQUESTS = 1

try:
    CONCURRENT_REQUESTS_PER_DOMAIN = int(os.environ.get('SCRAPER_CONCURRENT_REQUESTS_PER_DOMAIN', 1))
except ValueError:
    CONCURRENT_REQUESTS_PER_DOMAIN = 1

# --- Retry + headers ---
RETRY_ENABLED = str(os.environ.get('SCRAPER_RETRY_ENABLED', 'true')).lower() in ('1', 'true', 'yes')
try:
    RETRY_TIMES = int(os.environ.get('SCRAPER_RETRY_TIMES', 2))
except ValueError:
    RETRY_TIMES = 2

DEFAULT_REQUEST_HEADERS = {
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'en-US,en;q=0.9,fa;q=0.8',
    'User-Agent': os.environ.get('SCRAPER_USER_AGENT', 'vod-scraper/1.0'),
}

# Logging
LOG_LEVEL = os.environ.get('SCRAPER_LOG_LEVEL', 'INFO')
LOG_FORMAT = '%(asctime)s [%(name)s] %(levelname)s: %(message)s'

# PostgreSQL Pipeline
ITEM_PIPELINES = {
    'scraper.pipelines.PostgreSQLPipeline': 300,
}

REDIS_URL = os.environ.get('REDIS_URL', None)

if REDIS_URL:
    parsed = urlparse(REDIS_URL)
    REDIS_HOST = parsed.hostname or 'localhost'
    try:
        REDIS_PORT = int(parsed.port) if parsed.port else 6379
    except (TypeError, ValueError):
        REDIS_PORT = 6379
    try:
        REDIS_DB = int(parsed.path.lstrip('/')) if parsed.path else 0
    except (TypeError, ValueError):
        REDIS_DB = 0
else:
    REDIS_HOST = os.environ.get('REDIS_HOST', 'redis')
    REDIS_PORT = int(os.environ.get('REDIS_PORT', 6379))
    REDIS_DB = int(os.environ.get('REDIS_DB', 0))


# Scrapy settings
ROBOTSTXT_OBEY = False
DOWNLOAD_DELAY = float(os.environ.get('SCRAPER_DOWNLOAD_DELAY', 1.0))
CONCURRENT_REQUESTS = int(os.environ.get('SCRAPER_CONCURRENT_REQUESTS', 1))
CONCURRENT_REQUESTS_PER_DOMAIN = int(os.environ.get('SCRAPER_CONCURRENT_REQUESTS_PER_DOMAIN', 1))

# AutoThrottle
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 2
AUTOTHROTTLE_MAX_DELAY = 10
AUTOTHROTTLE_TARGET_CONCURRENCY = 0.5

# Retry settings
RETRY_ENABLED = True
RETRY_TIMES = 2
RETRY_HTTP_CODES = [500, 502, 503, 504, 408]

# Headers
DEFAULT_REQUEST_HEADERS = {
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'en-US,en;q=0.9,fa;q=0.8',
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
}

# Logging
LOG_LEVEL = 'INFO'
LOG_FORMAT = '%(asctime)s [%(name)s] %(levelname)s: %(message)s'