import logging
import os
import sys

import django
from api.catalog.matching_engine import ContentManager  # NEW: Import ContentManager
from api.catalog.models import Genre, Movie, Platform, Source
from django.conf import settings
from django.db import transaction
from itemadapter import ItemAdapter
from redis import ConnectionPool, Redis, exceptions as redis_exceptions
from twisted.internet.threads import deferToThread

logger = logging.getLogger(__name__)


class PostgreSQLPipeline:
	def __init__(self, redis_client):
		self.redis = redis_client
		self.django_setup_done = False
		self.content_manager = None
		self.stats = {
			"items_created": 0,
			"items_updated": 0,
			"sources_added": 0,
			"matches_found": 0,
			"errors": 0,
			"sources_updated": 0
		}
		self.genre_cache = {}

	@classmethod
	def from_crawler(cls, crawler):
		"""
		Prefer REDIS_URL if present, otherwise use REDIS_HOST/PORT/DB.
		Uses a ConnectionPool to avoid creating too many connections.
		"""
		redis_url = crawler.settings.get("REDIS_URL") or os.environ.get("REDIS_URL")
		try:
			if redis_url:
				pool = ConnectionPool.from_url(redis_url, decode_responses=True)
			else:
				host = crawler.settings.get("REDIS_HOST", "redis")
				port = int(crawler.settings.get("REDIS_PORT", 6379))
				db = int(crawler.settings.get("REDIS_DB", 0))
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
			fallback = Redis(host="localhost", port=6379, db=0, decode_responses=True)
			return cls(fallback)

	def _setup_django(self):
		if self.django_setup_done:
			return

		api_path = os.path.join(os.path.dirname(__file__), "..", "api")
		sys.path.insert(0, api_path)

		os.environ.setdefault("DJANGO_SETTINGS_MODULE", "vod.settings")

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

		self.Movie = Movie
		self.Source = Source
		self.Genre = Genre
		self.Platform = Platform
		self.transaction = transaction

		self.content_manager = ContentManager()

		logger.info("PostgreSQL pipeline with enhanced content matching opened")
		self.stats = {
			"items_created": 0,
			"items_updated": 0,
			"sources_added": 0,
			"sources_updated": 0,
			"matches_found": 0,
			"errors": 0
		}

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
		"""Synchronous item processing - COMPLETELY REWRITTEN"""
		if not self.django_setup_done:
			self._setup_django()

		try:
			adapter = ItemAdapter(item)

			# Extract and validate required fields
			title = adapter.get("title", "").strip()
			title_en = adapter.get("title_en", "").strip()
			year = adapter.get("release_year") or adapter.get("year")

			if not title or not year:
				logger.warning(f"Skipping item missing title or year: {adapter}")
				return item

			# Prepare genres list
			genre_objects = self._prepare_genres(adapter.get("genres", []))

			movie, content_created, source_created = self.content_manager.process_scraped_content(
				title=title,
				title_en=title_en,
				release_year=year,
				movie_type=adapter.get("type", "movie"),
				platform=self._get_platform_from_spider(spider.name),
				source_id=adapter.get("source_id"),
				url=adapter.get("url", ""),
				raw_payload=adapter.get("raw_data"),
				genres=genre_objects)

			# Update statistics based on what happened
			if content_created:
				self.stats["items_created"] += 1
				logger.info(f"✅ NEW content created: {movie.title}")
			else:
				self.stats["matches_found"] += 1
				logger.info(f"🔗 EXISTING content matched: {movie.title}")

			if source_created:
				self.stats["sources_added"] += 1
				logger.info(f"📺 NEW source linked: {spider.name}")
			else:
				self.stats["sources_updated"] += 1
				logger.info(f"🔄 Source updated: {spider.name}")

			self._update_redis_cache(movie, title, year)

			return item

		except Exception as e:
			logger.exception(f"Error processing item: {e}")
			self.stats["errors"] += 1
			return item

	def _prepare_genres(self, genre_names):
		"""Convert genre names to Genre objects"""
		genre_objects = []
		for genre_name in genre_names:
			if genre_name and genre_name.strip():
				cleaned_genre = genre_name.strip()
				if cleaned_genre not in self.genre_cache:
					genre, created = self.Genre.objects.get_or_create(name=cleaned_genre)
					self.genre_cache[cleaned_genre] = genre
				genre_objects.append(self.genre_cache[cleaned_genre])
		return genre_objects

	def _update_redis_cache(self, movie, title, year):
		"""Update Redis cache for future matching"""
		cache_key = f"match:{title}:{year}"
		try:
			self.redis.setex(cache_key, 7200, str(movie.id))  # 2 hours cache
		except redis_exceptions.ConnectionError as e:
			logger.warning(f"Redis cache update failed: {e}")

	def _get_platform_from_spider(self, spider_name):
		"""Map spider name to platform"""
		spider_to_platform = {
			"filimo": self.Platform.FILIMO,
			"namava": self.Platform.NAMAVA,
		}
		return spider_to_platform.get(spider_name, self.Platform.FILIMO)
