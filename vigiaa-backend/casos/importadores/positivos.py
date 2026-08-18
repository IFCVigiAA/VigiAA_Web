import os
import json
from django.conf import settings
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

# Importação dos models e tasks da aplicação casos
from casos.models import LogSincronizacao
from casos.tasks import task_processar_positivos


def _salvar_arquivo_temporario(job_id, arquivo):
    """Salva o arquivo em media/temp_uploads para que o Celery possa acessá-lo"""
    path_dir = os.path.join(settings.MEDIA_ROOT, "temp_uploads")
    os.makedirs(path_dir, exist_ok=True)
    
    nome_seguro = f"{job_id}_{arquivo.name.replace(' ', '_')}"
    caminho_final = os.path.join(path_dir, nome_seguro)
    
    with open(caminho_final, 'wb+') as destination:
        for chunk in arquivo.chunks():
            destination.write(chunk)
    return caminho_final


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def upload_casos_positivos(request):
    arquivo = (
        request.FILES.get("positivos") 
        or request.FILES.get("casos") 
        or (hasattr(request, 'data') and (request.data.get("positivos") or request.data.get("casos")))
    )
    celula_cabecalho = (
        request.POST.get("celula_cabecalho") 
        or (hasattr(request, 'data') and request.data.get("celula_cabecalho"))
    )

    mapeamento_raw = (
        (hasattr(request, 'data') and request.data.get("mapeamento"))
        or request.POST.get("mapeamento")
    )
    
    mapeamento_dict = None
    if mapeamento_raw:
        try:
            if isinstance(mapeamento_raw, str):
                mapeamento_dict = json.loads(mapeamento_raw)
            elif isinstance(mapeamento_raw, dict):
                mapeamento_dict = mapeamento_raw
        except Exception as e:
            print(f"⚠️ Erro ao converter JSON em casos/importadores/positivos.py: {e}", flush=True)

    print("\n" + "="*60, flush=True)
    print(">>> [IMPORTADORES/POSITIVOS.PY] MAPEAMENTO CAPTURADO:", mapeamento_dict, flush=True)
    print("="*60 + "\n", flush=True)

    if not arquivo:
        return JsonResponse({"erro": "Arquivo de positivos não enviado"}, status=400)

    job = LogSincronizacao.objects.create(
        tipo="positivos", 
        nome_arquivo=arquivo.name, 
        status="na_fila"
    )
    caminho = _salvar_arquivo_temporario(job.id, arquivo)

    task_processar_positivos.delay(
        job.id,
        caminho,
        celula_cabecalho=celula_cabecalho,
        mapeamento_customizado=mapeamento_dict
    )

    return JsonResponse({"sucesso": True, "job_id": job.id})