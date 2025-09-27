from django.contrib import admin

from .models import Credit, Movie, Source

admin.site.register(Movie)
admin.site.register(Source)
admin.site.register(Credit)
