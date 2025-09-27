import logging
import sys
import os
import time
from itemadapter import ItemAdapter
from redis import Redis, ConnectionPool, exceptions as redis_exceptions
from twisted.internet.threads import deferToThread

logger = logging.getLogger(__name__)


class PostgreSQLPipeline:
    def __init__(self, redis_client):
        self.redis = redis_client
        self.django_setup_done = False
        self.matcher = None
        self.stats = {
            'items_created': 0,
            'items_updated': 0,
            'sources_added': 0,
            'matches_found': 0,
            'errors': 0
        }
        self.genre_cache = {}

    @classmethod
    def from_crawler(cls, crawler):
        """
        Prefer REDIS_URL if present, otherwise use REDIS_HOST/PORT/DB.
        Uses a ConnectionPool to avoid creating too many connections.
        """
        redis_url = crawler.settings.get('REDIS_URL') or os.environ.get('REDIS_URL')
        try:
            if redis_url:
                pool = ConnectionPool.from_url(redis_url, decode_responses=True)
            else:
                host = crawler.settings.get('REDIS_HOST', 'redis')
                port = int(crawler.settings.get('REDIS_PORT', 6379))
                db = int(crawler.settings.get('REDIS_DB', 0))
                pool = ConnectionPool(host=host, port=port, db=db, decode_responses=True)
            redis_client = Redis(connection_pool=pool)
            # quick ping to validate connection (will raise if can't connect)
            try:
                redis_client.ping()
            except redis_exceptions.RedisError as e:
                logger.warning(f"Redis ping failed in pipeline init: {e}")
            return cls(redis_client)
        except Exception as e:
            logger.error(f"Failed to create redis client: {e}")
            fallback = Redis(host='localhost', port=6379, db=0, decode_responses=True)
            return cls(fallback)

    def _setup_django(self):
        if self.django_setup_done:
            return

        import django
        from django.conf import settings

        api_path = os.path.join(os.path.dirname(__file__), '..', 'api')
        sys.path.insert(0, api_path)

        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vod.settings')

        if not settings.configured:
            django.setup()

        self.django_setup_done = True

    def open_spider(self, spider):
        """Run setup in a thread to avoid async issues"""
        # Setup Django synchronously first
        self._setup_django()

        # Then load genres in a thread
        return deferToThread(self._open_spider_sync, spider)

    def _open_spider_sync(self, spider):
        """Synchronous spider opening"""
        from api.catalog.models import Movie, Source, Genre, Platform
        from api.catalog.matching_engine import ContentMatcher
        from django.db import transaction

        self.Item = Movie
        self.Source = Source
        self.Genre = Genre
        self.Platform = Platform
        self.transaction = transaction
        self.matcher = ContentMatcher()

        logger.info("PostgreSQL pipeline with content matching opened")
        self.stats = {'items_created': 0, 'items_updated': 0, 'sources_added': 0, 'matches_found': 0, 'errors': 0}

        # Load genre cache
        for genre in self.Genre.objects.all():
            self.genre_cache[genre.name] = genre
        logger.info(f"Loaded {len(self.genre_cache)} genres into cache")

    def close_spider(self, spider):
        logger.info(f"Pipeline stats: {self.stats}")

    def process_item(self, item, spider):
        """Use deferToThread to process items in threads"""
        return deferToThread(self._process_item_sync, item, spider)

    def _process_item_sync(self, item, spider):
        """Synchronous item processing"""
        if not self.django_setup_done:
            self._setup_django()

        try:
            adapter = ItemAdapter(item)

            with self.transaction.atomic():
                item_obj = self._find_or_create_item_with_matching(adapter, spider.name)
                self._create_source(item_obj, adapter, spider.name)

            return item
        except Exception as e:
            logger.exception(f"Error processing item: {e}")
            self.stats['errors'] += 1
            return item

    def _find_or_create_item_with_matching(self, adapter, spider_name):
        title = adapter.get('title', '').strip()
        year = adapter.get('release_year') or adapter.get('year')

        if not title or not year:
            raise ValueError("Missing title or year")

        platform = self._get_platform_from_spider(spider_name)
        source_id = adapter.get('source_id')

        matching_item = self.matcher.find_matching_item(title, year, platform, source_id)

        if matching_item:
            self.stats['matches_found'] += 1
            self.stats['items_updated'] += 1
            logger.info(f"Content matched: '{title}' -> '{matching_item.title}'")
            return matching_item

        # Create new movie
        movie = self.Item.objects.create(
            title=title,
            year=year,
            type=adapter.get('type', 'movie'),
        )

        # Process genres
        for genre_name in adapter.get('genres', []):
            if genre_name and genre_name.strip():
                genre_name = genre_name.strip()
                if genre_name not in self.genre_cache:
                    genre, created = self.Genre.objects.get_or_create(name=genre_name)
                    self.genre_cache[genre_name] = genre
                movie.genres.add(self.genre_cache[genre_name])

        self.stats['items_created'] += 1
        logger.info(f"Created new item: {title} ({year})")

        cache_key = f"match:{title}:{year}"
        # safe setex with very small retry loop in case Redis fluctuates
        for attempt in range(2):
            try:
                self.redis.setex(cache_key, 3600, str(movie.id))
                break
            except redis_exceptions.ConnectionError as e:
                logger.warning(f"Redis setex failed (attempt {attempt+1}): {e}")
                time.sleep(0.1)

        return movie

    def _create_source(self, movie, adapter, spider_name):
        platform = self._get_platform_from_spider(spider_name)
        source_id = adapter.get('source_id')

        if not source_id:
            raise ValueError("Missing source_id")

        source, created = self.Source.objects.get_or_create(
            platform=platform,
            source_id=source_id,
            defaults={
                'movie': movie,
                'url': adapter.get('url', ''),
                'raw_payload': adapter.get('raw_data'),
            }
        )

        if created:
            self.stats['sources_added'] += 1
            logger.debug(f"Added source: {platform}:{source_id}")

            sources_key = f"item_sources:{movie.id}"
            # safe incr with retry
            for attempt in range(2):
                try:
                    self.redis.incr(sources_key)
                    break
                except redis_exceptions.ConnectionError as e:
                    logger.warning(f"Redis incr failed (attempt {attempt+1}): {e}")
                    time.sleep(0.1)

    def _get_platform_from_spider(self, spider_name):
        spider_to_platform = {
            'filimo': self.Platform.FILIMO,
            'namava': self.Platform.NAMAVA,
        }
        return spider_to_platform.get(spider_name, self.Platform.FILIMO)
