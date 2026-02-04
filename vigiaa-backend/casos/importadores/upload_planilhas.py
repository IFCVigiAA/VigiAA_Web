import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from casos.importadores.focos import upload_focos
from casos.importadores.armadilhas import upload_armadilhas
from casos.importadores.pontos import upload_pontos_estrategicos
from casos.importadores.positivos import upload_casos_positivos


def _resp_to_dict(resp):
    try:
        return json.loads(resp.content.decode("utf-8"))
    except Exception:
        return {"raw": resp.content.decode("utf-8", errors="ignore")}


@csrf_exempt
def upload_planilhas(request):
    if request.method != "POST":
        return JsonResponse({"erro": "Método inválido"}, status=405)

    resultados = {}

    if "focos" in request.FILES:
        request._files = {"focos": request.FILES["focos"]}
        resultados["focos"] = _resp_to_dict(upload_focos(request))

    if "armadilhas" in request.FILES:
        request._files = {"armadilhas": request.FILES["armadilhas"]}
        resultados["armadilhas"] = _resp_to_dict(upload_armadilhas(request))

    if "pontos" in request.FILES:
        request._files = {"pontos": request.FILES["pontos"]}
        resultados["pontos"] = _resp_to_dict(upload_pontos_estrategicos(request))

    if "positivos" in request.FILES:
        request._files = {"positivos": request.FILES["positivos"]}
        resultados["positivos"] = _resp_to_dict(upload_casos_positivos(request))

    return JsonResponse({"sucesso": True, "detalhes": resultados})
