import logging
import re
from typing import Optional, Tuple, Dict, Any
from difflib import SequenceMatcher

import jellyfish
from django.db import transaction
from django.db.models import Q

from .models import Movie, Source
from .redis_client import RedisClient

logger = logging.getLogger(__name__)


class ContentManager:
	"""
	High-level content management class that handles the complete workflow:
	1. Match content against existing items
	2. Only create new content items when no match found
	3. Always create/update source mapping for the matched/existing item
	"""

	def __init__(self):
		self.matcher = EnhancedContentMatcher()

	def process_scraped_content(
			self, title: str,
			title_en: str,
			release_year: int, movie_type: str, platform: str,
			source_id: str, url: str = "", raw_payload: dict = None, **additional_metadata) -> Tuple[Movie, bool, bool]:
		"""
		Process scraped content with the optimal workflow:

		Returns: (movie, was_content_created, was_source_created)
		"""
		with transaction.atomic():
			# Step 1: Find existing content item or create new one if no match
			movie, content_created = self.matcher.find_or_get_movie(
				title=title,
				title_en=title_en,
				release_year=release_year,
				movie_type=movie_type,
				**additional_metadata
			)

			# Step 2: Always create/update the source mapping for the content item
			source = self._create_source(
				movie=movie,
				platform=platform,
				source_id=source_id,
				url=url,
				raw_payload=raw_payload
			)

			logger.info(
				f"Processed: {title} → {movie.title} "
				f"(Content: {'Created' if content_created else 'Existing'}, "
				f"Source: {'Created' if source else 'Existing'})"
			)

			return movie, content_created, source

	def _create_source(
			self,
			movie: Movie,
			platform: str,
			source_id: str,
			url: str = "",
			raw_payload: dict = None
	) -> Tuple[Source, bool]:
		"""
		Upsert source mapping - creates if not exists, updates if exists
		"""
		source = Source.objects.create(
			platform=platform,
			source_id=source_id,
			movie=movie,
			url=url,
			raw_payload=raw_payload,
			# defaults={
			# 	'movie': movie,
			# 	'url': url,
			# 	'raw_payload': raw_payload
			# }
		)
		return source

	def _update_content_metadata(self, movie: Movie, new_metadata: Dict[str, Any]):
		"""
		Update content item with new metadata if it improves the record
		"""
		update_fields = []

		if not movie.title_en and new_metadata.get('title_en'):
			movie.title_en = new_metadata['title_en']
			update_fields.append('title_en')

		if update_fields:
			movie.save(update_fields=update_fields)
			logger.info(f"Updated metadata for {movie.title}: {update_fields}")


class EnhancedContentMatcher:
	"""
	Optimized matcher that focuses on finding existing content rather than creating duplicates
	"""

	def __init__(self):
		self.redis = RedisClient()
		self.common_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by"}

		self.title_variations = {
			"متری شیش و نیم": ["metri shish o nim", "metri shesh o nim", "metri 6.5"],
			"شقایق": ["shaghayegh"],
			"خانه پدری": ["khane pedari", "khaneh pedari", "father's house"],
		}

	def find_or_get_movie(
			self,
			title: str,
			title_en: str,
			release_year: int,
			movie_type: str,
			**additional_metadata
	) -> Tuple[Movie, bool]:
		"""
		Find existing content item or create new one ONLY if no match found

		Returns: (content_item, created)
		"""
		# Try multiple matching strategies in order of reliability
		matching_strategies = [
			lambda: self._match_by_exact_criteria(title=title, title_en=title_en, release_year=release_year,
												  movie_type=movie_type, additional_metadata=additional_metadata),
			lambda: self._match_by_fuzzy_logic(title=title, title_en=title_en, release_year=release_year, movie_type=movie_type,
											   additional_metadata=additional_metadata),
			lambda: self._match_by_title_variations(title=title, title_en=title_en,release_year=release_year, movie_type=movie_type,
													additional_metadata=additional_metadata),
		]

		for strategy in matching_strategies:
			match = strategy()  # Call the lambda function
			# match = strategy(release_year=release_year, movie_type=movie_type, additional_metadata=additional_metadata)
			if match:
				logger.info(f"Match found via {strategy.__name__}: {match.title}")
				return match, False  # Existing item, not created

		# No match found - create new content item
		return self._create_movie(title, title_en, release_year, movie_type, additional_metadata), True

	def _match_by_exact_criteria(self, title: str, title_en: str, release_year: int, movie_type: str,
								 additional_metadata: dict) -> \
			Optional[Movie]:
		"""Exact matching using multiple criteria"""
		if not release_year:
			return None

		normalized_title = self.normalize_title(
			title_en) if title_en != '' or title_en is not None else self.normalize_title(title)

		# Build query for exact matching
		query = Q(year=release_year, type=movie_type)

		# Try multiple title fields
		title_filters = Q()
		for field in ['title', 'title_en']:
			title_filters |= Q(**{f"{field}__iexact": normalized_title})

		query &= title_filters

		try:
			return Movie.objects.filter(query).first()
		except Exception as e:
			logger.error(f"Error in exact matching: {e}")
			return None

	def _match_by_fuzzy_logic(self, title: str, title_en: str, release_year: int, movie_type: str,
							  additional_metadata: dict) -> \
			Optional[Movie]:
		"""Fuzzy matching with year tolerance"""
		if not release_year:
			return None

		year_tolerance = 1
		min_year = release_year - year_tolerance
		max_year = release_year + year_tolerance

		try:
			potential_matches = Movie.objects.filter(
				year__gte=min_year,
				year__lte=max_year,
				type=movie_type
			)[:100]  # Performance limit

			best_match = None
			best_score = 0.0

			for item in potential_matches:
				score = self.similarity_score(title_en,
											  item.title_en) if title_en != '' or title_en is not None else self.similarity_score(
					title, item.title_en)
				if score > best_score and score >= 0.9:  # Higher threshold for fuzzy matching
					best_score = score
					best_match = item

			return best_match

		except Exception as e:
			logger.error(f"Error in fuzzy matching: {e}")
			return None

	def _match_by_title_variations(self, title: str, title_en: str, release_year: int, movie_type: str,
								   additional_metadata: dict) -> \
			Optional[Movie]:
		"""Match using known title variations"""
		if not release_year:
			return None

		normalized_title = self.normalize_title(
			title_en) if title_en != '' or title_en is not None else self.normalize_title(title)

		# Check if this title matches any known variations
		for base_title, variations in self.title_variations.items():
			if normalized_title in variations:
				try:
					return Movie.objects.get(
						title__icontains=base_title,
						year=release_year,
						type=movie_type
					)
				except (Movie.DoesNotExist, Movie.MultipleObjectsReturned):
					continue
		return None

	def _create_movie(self, title: str, title_en: str, release_year: int, movie_type: str,
					  metadata: dict) -> Movie:
		"""Create new content item ONLY when no match is found"""
		# with transaction.atomic():
		movie = Movie.objects.create(
			title=title,
			title_en=title_en,
			year=release_year,
			type=movie_type,
		)

		# Add genres if provided
		if 'genres' in metadata:
			movie.genres.set(metadata['genres'])

		logger.info(f"Created new content item: {movie.title_en}")
		return movie

	# Keep the existing helper methods
	def normalize_title(self, title: str) -> str:
		if not title:
			return ""
		title = title.lower().strip()
		title = re.sub(r"[^\w\s]", " ", title)
		title = " ".join(title.split())
		words = [word for word in title.split() if word not in self.common_words]
		return " ".join(words)

	def similarity_score(self, title1: str, title2: str) -> float:
		normalized1 = self.normalize_title(title1)
		normalized2 = self.normalize_title(title2)

		if not normalized1 or not normalized2:
			return 0.0

		if normalized1 == normalized2:
			return 1.0

		ratios = [
			SequenceMatcher(None, normalized1, normalized2).ratio(),
			jellyfish.jaro_winkler_similarity(normalized1, normalized2),
		]
		return max(ratios)
