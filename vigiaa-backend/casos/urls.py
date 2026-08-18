from django.urls import path
from casos.importadores.upload_planilhas import upload_planilhas
from casos.importadores.focos import upload_focos
from casos.importadores.armadilhas import upload_armadilhas
from casos.importadores.pontos import upload_pontos_estrategicos
from casos.importadores.positivos import upload_casos_positivos
from casos.sincronizar import sincronizar_oficial_api
from .views import me
from django.contrib.auth import views as auth_views
from .views import status_processamento
from .views import disparar_geoprocessamento
from . import views

urlpatterns = [
    path("me/", me, name="me"),
    path("upload-planilhas/", upload_planilhas, name="upload_planilhas"),
    path("upload/focos/", upload_focos, name="upload_focos"),
    path("upload/armadilhas/", upload_armadilhas, name="upload_armadilhas"),
    path("upload/pontos/", upload_pontos_estrategicos, name="upload_pontos"),
    path("upload/positivos/", upload_casos_positivos, name="upload_positivos"),
    path("login/", auth_views.LoginView.as_view(template_name="login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(next_page="/api/casos/login/"), name="logout"),
    path("sincronizar/", sincronizar_oficial_api, name="sincronizar_oficial"),
    path("status-processamento/<int:job_id>/", status_processamento),
    path('geoprocessar-positivos/', disparar_geoprocessamento, name='geoprocessar_positivos'),
    path('extrair-cabecalho/', views.extrair_cabecalho_e_sugerir, name='extrair_cabecalho'),
]
