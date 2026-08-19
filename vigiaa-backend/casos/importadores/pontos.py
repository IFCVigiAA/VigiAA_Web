import os
import json
from django.conf import settings
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from casos.models import LogSincronizacao
from casos.tasks import task_processar_pontos


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def upload_pontos_estrategicos(request):
    # 1. Recupera o arquivo de pontos estratégicos
    arquivo = (
        request.FILES.get("pontos") 
        or (hasattr(request, 'data') and request.data.get("pontos"))
    )
    if not arquivo:
        return JsonResponse({"erro": "Arquivo não enviado"}, status=400)

    # 2. Captura parâmetro de cabeçalho inicial opcional
    celula_cabecalho = (
        request.POST.get("celula_cabecalho") 
        or (hasattr(request, 'data') and request.data.get("celula_cabecalho"))
    )

    # 3. Captura e converte a string JSON de mapeamento
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
            print(f"⚠️ Erro ao converter JSON em upload_pontos_estrategicos: {e}", flush=True)

    print("\n" + "="*60, flush=True)
    print(">>> [IMPORTADORES/PONTOS.PY] MAPEAMENTO CAPTURADO:", mapeamento_dict, flush=True)
    print("="*60 + "\n", flush=True)

    # 4. Cria o registro de Log
    job = LogSincronizacao.objects.create(
        tipo="pontos",
        nome_arquivo=arquivo.name,
        status="na_fila",
        progresso=0,
        mensagem="Aguardando processamento de pontos estratégicos..."
    )

    # 5. Salva o arquivo temporariamente
    path_dir = os.path.join(settings.MEDIA_ROOT, "temp_uploads")
    os.makedirs(path_dir, exist_ok=True)
    caminho = os.path.join(path_dir, f"job_{job.id}_{arquivo.name.replace(' ', '_')}")
    
    with open(caminho, 'wb+') as destination:
        for chunk in arquivo.chunks():
            destination.write(chunk)

    # 6. Dispara a Task do Celery com os parâmetros completos
    task_processar_pontos.delay(
        job.id,
        caminho,
        celula_cabecalho=celula_cabecalho,
        mapeamento_customizado=mapeamento_dict
    )

    return JsonResponse({"sucesso": True, "job_id": job.id})    