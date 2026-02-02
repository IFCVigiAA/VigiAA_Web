from django.urls import path
from casos.importadores.upload_planilhas import upload_planilhas
from casos.importadores.focos import upload_focos
from casos.importadores.armadilhas import upload_armadilhas
from casos.importadores.pontos import upload_pontos_estrategicos
from casos.importadores.positivos import upload_casos_positivos
from .views_csrf import csrf
from .views import me

urlpatterns = [
    path("me/", me, name="me"),
    path("csrf/", csrf),
    path("upload-planilhas/", upload_planilhas, name="upload_planilhas"),
    path("upload/focos/", upload_focos, name="upload_focos"),
    path("upload/armadilhas/", upload_armadilhas, name="upload_armadilhas"),
    path("upload/pontos/", upload_pontos_estrategicos, name="upload_pontos"),
    path("upload/positivos/", upload_casos_positivos, name="upload_positivos"),
]
