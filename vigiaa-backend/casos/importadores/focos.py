import os
from django.conf import settings
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from casos.models import LogSincronizacao
from casos.tasks import task_processar_focos

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def upload_focos(request):
    arquivo = request.FILES.get("focos")
    if not arquivo:
        return JsonResponse({"erro": "Arquivo não enviado"}, status=400)

    # Cria o Log
    job = LogSincronizacao.objects.create(
        tipo="focos",
        nome_arquivo=arquivo.name,
        status="na_fila",
        progresso=0,
        mensagem="Aguardando processamento de focos..."
    )

    # Salva temporariamente
    path_dir = os.path.join(settings.MEDIA_ROOT, "temp_uploads")
    os.makedirs(path_dir, exist_ok=True)
    caminho = os.path.join(path_dir, f"job_{job.id}_{arquivo.name.replace(' ', '_')}")
    
    with open(caminho, 'wb+') as destination:
        for chunk in arquivo.chunks():
            destination.write(chunk)

    # Dispara Celery
    task_processar_focos.delay(job.id, caminho)

    return JsonResponse({"sucesso": True, "job_id": job.id})