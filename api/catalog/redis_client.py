import redis
from django.conf import settings
import json


class RedisClient:
	def __init__(self):
		self.redis = redis.Redis(
			host=settings.REDIS_HOST,
			port=settings.REDIS_PORT,
			db=settings.REDIS_DB,
			decode_responses=True
		)

	def cache_item(self, item_id, data, expire=3600):
		key = f"item:{item_id}"
		self.redis.setex(key, expire, json.dumps(data))

	def get_cached_item(self, item_id):
		key = f"item:{item_id}"
		data = self.redis.get(key)
		return json.loads(data) if data else None

	def increment_view_count(self, item_id):
		key = f"views:{item_id}"
		return self.redis.incr(key)

	def cache_api_response(self, endpoint, params, data, expire=300):
		"""Cache API responses for better performance"""
		key = f"api:{endpoint}:{json.dumps(params, sort_keys=True)}"
		self.redis.setex(key, expire, json.dumps(data))

	def get_cached_api_response(self, endpoint, params):
		key = f"api:{endpoint}:{json.dumps(params, sort_keys=True)}"
		data = self.redis.get(key)
		return json.loads(data) if data else None
