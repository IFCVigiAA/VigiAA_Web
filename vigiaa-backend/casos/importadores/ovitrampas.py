import os
from django.conf import settings
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from casos.models import LogSincronizacao
from casos.tasks import task_processar_ovitrampas

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def upload_ovitrampas(request):
    arquivo = request.FILES.get("ovitrampas") or request.FILES.get("file")
    if not arquivo:
        return JsonResponse({"erro": "Arquivo não enviado"}, status=400)

    # Cria o Log de Sincronização
    job = LogSincronizacao.objects.create(
        tipo="ovitrampas",
        nome_arquivo=arquivo.name,
        status="na_fila",
        progresso=0,
        mensagem="Aguardando processamento de ovitrampas..."
    )

    # Salva o arquivo temporariamente em disco
    path_dir = os.path.join(settings.MEDIA_ROOT, "temp_uploads")
    os.makedirs(path_dir, exist_ok=True)
    caminho = os.path.join(path_dir, f"job_{job.id}_{arquivo.name.replace(' ', '_')}")
    
    with open(caminho, 'wb+') as destination:
        for chunk in arquivo.chunks():
            destination.write(chunk)

    # Dispara a task no Celery
    celula_cabecalho = request.POST.get("celula_cabecalho")
    mapeamento = request.POST.get("mapeamento")

    task_processar_ovitrampas.delay(
        job.id,
        caminho,
        celula_cabecalho=celula_cabecalho,
        mapeamento_customizado=mapeamento,
    )

    return JsonResponse({"sucesso": True, "job_id": job.id})