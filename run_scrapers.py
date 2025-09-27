#!/usr/bin/env python3
"""
Run both Namava and Filimo scrapers with PostgreSQL pipeline and Redis cache
Optimized for Docker environment
"""

import logging
import os
import sys
import time
from pathlib import Path

import redis
from django.db import connection
from scraper.spiders.filimo_spider import FilimoSpider
from scraper.spiders.namava_spider import NamavaSpider
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Add project root to path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

# Set environment variables for Docker
os.environ.setdefault("DATABASE_URL", "postgres://voduser:vodpass@localhost:5433/vod")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "api.vod.settings")

try:
    # Set up Django BEFORE importing scrapy
    import django

    django.setup()
    logger.info("Django setup completed successfully")
except Exception as e:
    logger.error(f"Failed to setup Django: {e}")
    sys.exit(1)

# Now set reactor and import scrapy
os.environ.setdefault("TWISTED_REACTOR", "twisted.internet.asyncioreactor.AsyncioSelectorReactor")


def wait_for_services():
    """Wait for database and Redis to be ready"""
    max_retries = 30
    retry_count = 0

    while retry_count < max_retries:
        try:
            # Test database connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            logger.info("Database connection successful")

            # Test Redis connection
            redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
            redis_client = redis.from_url(redis_url)
            redis_client.ping()
            logger.info("Redis connection successful")

            return True

        except Exception as e:
            retry_count += 1
            logger.warning(f"Service connection failed (attempt {retry_count}/{max_retries}): {e}")
            time.sleep(2)

    logger.error("Failed to connect to services after maximum retries")
    return False


def main():
    logger.info("🚀 Starting both Namava and Filimo scrapers with PostgreSQL pipeline...")

    if not wait_for_services():
        sys.exit(1)

    # Get project settings
    settings = get_project_settings()

    # Configure settings for Docker environment
    settings.setdict(
        {
            "LOG_LEVEL": "INFO",
            "DOWNLOAD_DELAY": 0.5,
            "AUTOTHROTTLE_ENABLED": True,
            "CONCURRENT_REQUESTS": 2,
            "TWISTED_REACTOR": "twisted.internet.asyncioreactor.AsyncioSelectorReactor",
            # Pipeline settings
            "ITEM_PIPELINES": {
                "scraper.pipelines.PostgreSQLPipeline": 300,
            },
            # Redis settings for Docker
            "REDIS_URL": "redis://redis:6379/0",
            # Playwright settings
            "DOWNLOAD_HANDLERS": {
                "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
                "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
            },
            "PLAYWRIGHT_LAUNCH_OPTIONS": {
                "headless": True,
                "args": ["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
            },
        },
        priority="cmdline",
    )

    try:
        # Create crawler process
        process = CrawlerProcess(settings=settings)

        logger.info("🕷️ Starting Filimo spider...")
        process.crawl(FilimoSpider)

        logger.info("🕷️ Starting Namava spider...")
        process.crawl(NamavaSpider)

        # Start crawling
        process.start()

        logger.info("✅ Both scrapers completed successfully!")
        return True

    except Exception as e:
        logger.error(f"❌ Error running scrapers: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
