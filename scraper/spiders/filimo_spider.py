import logging
from typing import ClassVar

import scrapy

logger = logging.getLogger(__name__)


class FilimoSpider(scrapy.Spider):
    name = "filimo_api"
    allowed_domains: ClassVar[tuple[str, ...]] = ("api.filimo.com",)

    custom_settings = {
        "ITEM_PIPELINES": {
            "scraper.pipelines.PostgreSQLPipeline": 300,
        },
        "DEFAULT_REQUEST_HEADERS": {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://www.filimo.com/",
            "Accept-Language": "en-US,en;q=0.9,fa;q=0.8",
        },
        "DOWNLOAD_DELAY": 0.2,
        "AUTOTHROTTLE_ENABLED": True,
        "LOG_LEVEL": "INFO",
    }

    # TODO: this is for new movies...
    start_urls = ["https://api.filimo.com/api/fa/v1/movie/movie/list/tagid/1/other_data/movie-new_nocomingsoon"]

    def parse(self, response):
        data = response.json()
        included = data.get("included", [])
        movies = [item for item in included if item.get("type") == "movies"]

        for movie in movies:
            attr = movie.get("attributes", {})

            title = attr.get("movie_title")
            release_year = self._safe_int(attr.get("pro_year"))
            genres = [
                c.get("title_en") or c.get("title")
                for c in attr.get("categories", [])
                if c.get("title") or c.get("title_en")
            ]
            source_id = str(attr.get("movie_id") or attr.get("uid") or attr.get("id"))

            yield {
                "title": title,
                "release_year": release_year,
                "type": "movie",
                "genres": genres,
                "source_id": source_id,
                "url": f"https://www.filimo.com/m/{source_id}",
                "raw_data": movie,  # Store full API response
            }

    def _safe_int(self, value):
        if not value:
            return None
        try:
            value_str = str(value)
            persian_digits = "۰۱۲۳۴۵۶۷۸۹"
            if any(ch in persian_digits for ch in value_str):
                trans_table = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")
                value_str = value_str.translate(trans_table)
            return int(value_str)
        except Exception:
            return None
