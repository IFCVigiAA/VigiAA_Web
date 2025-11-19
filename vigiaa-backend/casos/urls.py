from django.urls import path
from .views import listar_casos

urlpatterns = [
    path("", listar_casos),
]