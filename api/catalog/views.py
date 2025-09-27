from rest_framework import generics

from .models import Movie
from .serializers import ItemSerializer


class MovieList(generics.ListAPIView):
    serializer_class = ItemSerializer

    def get_queryset(self):
        return Movie.objects.filter(type="movie").order_by("-year")


class SeriesList(generics.ListAPIView):
    serializer_class = ItemSerializer

    def get_queryset(self):
        return Movie.objects.filter(type="series").order_by("-year")


class ItemDetail(generics.RetrieveAPIView):
    serializer_class = ItemSerializer
    queryset = Movie.objects.all()
