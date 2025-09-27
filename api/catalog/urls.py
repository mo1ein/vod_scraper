from django.urls import path
from . import views

urlpatterns = [
    path('movies/', views.MovieList.as_view(), name='movies-list'),
    path('series/', views.SeriesList.as_view(), name='series-list'),
    path('items/<int:pk>/', views.ItemDetail.as_view(), name='item-detail'),
]
