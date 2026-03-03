from django.http import JsonResponse

from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponseForbidden
from casos.importadores.focos import upload_focos
from casos.importadores.armadilhas import upload_armadilhas
from casos.importadores.pontos import upload_pontos_estrategicos
from casos.importadores.positivos import upload_casos_positivos
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated



@api_view(["POST"])
@permission_classes([IsAuthenticated])

def upload_planilhas(request):
    if request.method != "POST":
        return JsonResponse({"erro": "Método inválido"}, status=405)

    resultados = {}

    if "focos" in request.FILES:
        request._files = {"focos": request.FILES["focos"]}
        resp = upload_focos(request)
        resultados["focos"] = resp.content.decode()

    if "armadilhas" in request.FILES:
        request._files = {"armadilhas": request.FILES["armadilhas"]}
        resp = upload_armadilhas(request)
        resultados["armadilhas"] = resp.content.decode()

    if "pontos" in request.FILES:
        request._files = {"pontos": request.FILES["pontos"]}
        resp = upload_pontos_estrategicos(request)
        resultados["pontos"] = resp.content.decode()

    if "positivos" in request.FILES:
        request._files = {"positivos": request.FILES["positivos"]}
        resp = upload_casos_positivos(request)
        resultados["positivos"] = resp.content.decode()

    return JsonResponse({"sucesso": True, "detalhes": resultados})
