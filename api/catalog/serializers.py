from rest_framework import serializers

from .models import Credit, Movie, Source


class SourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Source
        fields = ("platform", "source_id", "url", "scraped_at")


class CreditSerializer(serializers.ModelSerializer):
    class Meta:
        model = Credit
        fields = ("role", "name", "character_name")


class ItemSerializer(serializers.ModelSerializer):
    genres = serializers.SlugRelatedField(many=True, read_only=True, slug_field="name")
    sources_count = serializers.SerializerMethodField()
    platforms = serializers.SerializerMethodField()

    class Meta:
        model = Movie
        fields = ("id", "title", "year", "type", "genres", "sources_count", "platforms")

    def get_sources_count(self, obj):
        return obj.sources.count()

    def get_platforms(self, obj):
        return list(obj.sources.values_list("platform", flat=True).distinct())


class ItemDetailSerializer(ItemSerializer):
    credits = serializers.SerializerMethodField()
    matching_score = serializers.SerializerMethodField()

    class Meta(ItemSerializer.Meta):
        fields = ItemSerializer.Meta.fields + ("credits", "matching_score")

    def get_credits(self, obj):
        credits = obj.credits.all()
        return CreditSerializer(credits, many=True).data

    def get_matching_score(self, obj):
        return min(obj.sources.count() / 2, 1.0)
