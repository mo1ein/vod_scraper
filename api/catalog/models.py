from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class Platform(models.TextChoices):
    FILIMO = 'filimo', 'Filimo'
    NAMAVA = 'namava', 'Namava'


class ContentType(models.TextChoices):
    MOVIE = 'movie', 'Movie'
    SERIES = 'series', 'Series'


class Genre(models.Model):
    name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(null=False, auto_now_add=True)

    class Meta:
            db_table = 'genres'

    def __str__(self):
        return self.name


class Movie(models.Model):
    title = models.CharField(max_length=500, db_index=True)
    year = models.IntegerField(
        validators=[MinValueValidator(1900), MaxValueValidator(2030)],
        db_index=True
    )
    type = models.CharField(
        max_length=10,
        choices=ContentType.choices,
        default=ContentType.MOVIE,
        db_index=True
    )

    genres = models.ManyToManyField(Genre, related_name='movies', db_table='movie_genres')
    created_at = models.DateTimeField(null=False, auto_now_add=True)
    updated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'movies'
        indexes = [
            models.Index(fields=['year', 'type']),
            models.Index(fields=['title']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['title', 'year'],
                name='unique_title_year'
            )
        ]

    def __str__(self):
        return f"{self.title} ({self.year})"

class Source(models.Model):
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='sources', db_column='movie_id')
    platform = models.CharField(max_length=20, choices=Platform.choices)
    source_id = models.CharField(max_length=200)
    url = models.URLField(blank=True)
    raw_payload = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(null=False, auto_now_add=True)

    class Meta:
        db_table = 'sources'  # Optional: if you want to rename this too
        unique_together = ['platform', 'source_id']

    def __str__(self):
        return f"{self.platform}: {self.source_id}"


class Credit(models.Model):
    class RoleType(models.TextChoices):
        DIRECTOR = 'director', 'Director'
        PRODUCER = 'producer', 'Producer'
        ACTOR = 'actor', 'Actor'

    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='credits', db_column='movie_id')
    role = models.CharField(max_length=20, choices=RoleType.choices)
    name = models.CharField(max_length=200)
    character_name = models.CharField(max_length=200, blank=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(null=True, blank=True)


    class Meta:
        db_table = 'credits'  # Add this line
        ordering = ['role', 'order']

    def __str__(self):
        return f"{self.name} - {self.role}"