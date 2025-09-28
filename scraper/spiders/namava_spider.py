import logging
from typing import ClassVar

import scrapy

logger = logging.getLogger(__name__)


class NamavaSpider(scrapy.Spider):
    name = "namava"
    allowed_domains: ClassVar[tuple[str, ...]] = ("namava.ir",)

    # You can set this limit before running the spider
    max_pages = 2

    page_index = 1
    page_size = 20

    def start_requests(self):
        url = self._latest_movies_url(self.page_index, self.page_size)
        yield scrapy.Request(url, callback=self.parse)

    def parse(self, response, **kwargs):
        data = response.json()
        movies = data.get("result", [])

        if not movies:
            logger.info(f"No movies found on page {self.page_index}")
            return

        for movie in movies:
            movie_id = movie.get("id")
            caption = movie.get("caption")
            preview_url = f"https://www.namava.ir/api/v1.0/medias/{movie_id}/preview"
            yield scrapy.Request(
                preview_url, callback=self.parse_movie, meta={"source_id": movie_id, "base_title": caption}
            )

        # Pagination with limit check
        if len(movies) == self.page_size and self.page_index < self.max_pages:
            self.page_index += 1
            next_url = self._latest_movies_url(self.page_index, self.page_size)
            yield scrapy.Request(next_url, callback=self.parse)

    def parse_movie(self, response):
        data = response.json()
        result = data.get("result", {})

        title = result.get("caption")
        year = result.get("year")
        if year:
            try:
                year = int(str(year).strip())
            except Exception:
                year = None

        # Genres are categoryName inside categories array
        genres = []
        categories = result.get("categories", [])
        if isinstance(categories, list):
            for cat in categories:
                name = cat.get("categoryName")
                if name:
                    genres.append(name)

        source_id = str(result.get("id") or response.meta.get("source_id"))

        yield {
            "title": title,
            "release_year": year,
            "genres": genres,
            "source_id": source_id,
            "url": response.url,
            "raw_data": result,
        }

    def _latest_movies_url(self, page, size):
        return f"https://www.namava.ir/api/v1.0/medias/latest-movies?pi={page}&ps={size}"
