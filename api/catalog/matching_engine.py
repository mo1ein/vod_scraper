import logging
import re
from difflib import SequenceMatcher

import jellyfish

from .models import Movie
from .redis_client import RedisClient

logger = logging.getLogger(__name__)


class ContentMatcher:
    def __init__(self):
        self.redis = RedisClient()
        self.common_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by"}

        # Common title variations for Iranian content
        self.title_variations = {
            "متری شیش و نیم": ["metri shish o nim", "metri shesh o nim"],
            "شقایق": ["shaghayegh"],
            "خانه پدری": ["khane pedari"],
            # Add more Persian title variations as needed
        }

    def normalize_title(self, title):
        """Normalize title for comparison - handles Persian and English"""
        if not title:
            return ""

        # Convert to lowercase
        title = title.lower().strip()

        # Remove common Persian and English punctuation
        title = re.sub(r"[^\w\s]", " ", title)

        # Remove extra whitespace
        title = " ".join(title.split())

        # Remove common words (both English and Persian)
        persian_common = {"در", "با", "از", "به", "برای"}
        all_common = self.common_words.union(persian_common)
        words = [word for word in title.split() if word not in all_common]

        return " ".join(words)

    def similarity_score(self, title1, title2):
        """Calculate similarity between two titles using multiple algorithms"""
        normalized1 = self.normalize_title(title1)
        normalized2 = self.normalize_title(title2)

        if not normalized1 or not normalized2:
            return 0.0

        # Use multiple similarity algorithms for better accuracy
        ratios = [
            SequenceMatcher(None, normalized1, normalized2).ratio(),
            jellyfish.jaro_winkler_similarity(normalized1, normalized2),
        ]

        return max(ratios)

    def find_matching_item(self, platform_title, release_year, platform, source_id):
        """
        Find existing item that matches the scraped content
        Returns matching item or None if no match found
        """
        # Check Redis cache first
        cache_key = f"match:{platform_title}:{release_year}"
        cached_item_id = self.redis.redis.get(cache_key)

        if cached_item_id:
            try:
                item = Movie.objects.get(id=cached_item_id)
                logger.debug(f"Found cached match: {item.title}")
                return item
            except Movie.DoesNotExist:
                pass  # Cache stale, continue to DB lookup

        # Step 1: Exact match (same title and year)
        exact_match = self._find_exact_match(platform_title, release_year)
        if exact_match:
            self.redis.redis.setex(cache_key, 3600, str(exact_match.id))  # Cache for 1 hour
            return exact_match

        # Step 2: Fuzzy match with year tolerance
        fuzzy_match = self._find_fuzzy_match(platform_title, release_year)
        if fuzzy_match:
            self.redis.redis.setex(cache_key, 3600, str(fuzzy_match.id))
            return fuzzy_match

        # Step 3: Check for known title variations
        variation_match = self._find_variation_match(platform_title, release_year)
        if variation_match:
            self.redis.redis.setex(cache_key, 3600, str(variation_match.id))
            return variation_match

        return None

    def _find_exact_match(self, platform_title, release_year):
        """Find exact match by normalized title and year"""
        if not release_year:
            return None

        normalized_title = self.normalize_title(platform_title)

        # Look for items with same normalized title and exact year
        try:
            movies = Movie.objects.filter(year=release_year)
            for item in movies:
                if self.normalize_title(item.title) == normalized_title:
                    logger.info(f"Exact match found: {item.title} ({item.year})")
                    return item
        except Exception as e:
            logger.error(f"Error in exact matching: {e}")

        return None

    def _find_fuzzy_match(self, platform_title, release_year, year_tolerance=1, similarity_threshold=0.85):
        """Find fuzzy matches with year tolerance"""
        if not release_year:
            return None

        # Search in items within year tolerance
        min_year = release_year - year_tolerance
        max_year = release_year + year_tolerance

        try:
            potential_matches = Movie.objects.filter(year__gte=min_year, year__lte=max_year)[
                :100
            ]  # Limit for performance

            best_match = None
            best_score = 0.0

            for item in potential_matches:
                score = self.similarity_score(platform_title, item.title)

                # Check for known variations
                normalized_platform = self.normalize_title(platform_title)
                normalized_item = self.normalize_title(item.title)

                for base, variations in self.title_variations.items():
                    if normalized_platform in variations and normalized_item in variations:
                        score = max(score, 0.95)  # Boost for known variations

                if score > best_score and score >= similarity_threshold:
                    best_score = score
                    best_match = item

            if best_match:
                logger.info(f"Fuzzy match found: {best_match.title} ({best_match.year}) - Score: {best_score:.2f}")
                return best_match

        except Exception as e:
            logger.error(f"Error in fuzzy matching: {e}")

        return None

    def _find_variation_match(self, platform_title, release_year):
        """Check for known title variations"""
        if not release_year:
            return None

        normalized_title = self.normalize_title(platform_title)

        # Check if this title is a known variation
        for base_title, variations in self.title_variations.items():
            if normalized_title in variations:
                # Look for the base title
                try:
                    movie = Movie.objects.get(title__icontains=base_title, year=release_year)
                    logger.info(f"Variation match found: {movie.title} for {platform_title}")
                    return movie
                except (Movie.DoesNotExist, Movie.MultipleObjectsReturned):
                    continue

        return None

    def generate_canonical_title(self, platform_titles):
        """Generate canonical title from multiple platform titles"""
        if not platform_titles:
            return ""

        # Simple strategy: use the most common title format
        # For now, return the first title - can be enhanced with frequency analysis
        return platform_titles[0] if platform_titles else ""
