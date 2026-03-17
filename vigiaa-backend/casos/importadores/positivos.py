import os
from django.conf import settings
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from casos.models import LogSincronizacao
from casos.tasks import task_processar_positivos  

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def upload_casos_positivos(request):
    arquivo = request.FILES.get("positivos") or request.FILES.get("casos")
    
    if not arquivo:
        return JsonResponse({"erro": "Arquivo não enviado"}, status=400)


    job = LogSincronizacao.objects.create(
        tipo="positivos",
        nome_arquivo=arquivo.name,
        status="na_fila",
        progresso=0,
        mensagem="Arquivo recebido. Aguardando processamento..."
    )

    # 2. Salva o arquivo fisicamente no servidor
    # O Celery não consegue acessar arquivos que estão apenas na memória da request
    path_dir = os.path.join(settings.MEDIA_ROOT, "temp_uploads")
    os.makedirs(path_dir, exist_ok=True)
    
    # Geramos um nome único usando o ID do job para não sobrescrever arquivos
    nome_arquivo_servidor = f"job_{job.id}_{arquivo.name.replace(' ', '_')}"
    caminho_final = os.path.join(path_dir, nome_arquivo_servidor)
    
    with open(caminho_final, 'wb+') as destination:
        for chunk in arquivo.chunks():
            destination.write(chunk)

    # 3. Dispara a tarefa em background (.delay) e passa o caminho do arquivo
    # Isso responde ao usuário em milissegundos
    task_processar_positivos.delay(job.id, caminho_final)

    # 4. Retorna o job_id para o React
    return JsonResponse({
        "sucesso": True,
        "job_id": job.id,
        "mensagem": "Upload iniciado em segundo plano."
    })