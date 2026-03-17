import os
from django.conf import settings
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from .models import LogSincronizacao
from .tasks import (
    task_processar_positivos, 
    task_processar_pontos, 
    task_processar_focos, 
    task_processar_armadilhas
)

# --- FUNÇÃO AUXILIAR PARA SALVAR ARQUIVO ---
def _salvar_arquivo_temporario(job_id, arquivo):
    """Salva o arquivo em media/temp para que o Celery possa acessá-lo"""
    path_dir = os.path.join(settings.MEDIA_ROOT, "temp_uploads")
    os.makedirs(path_dir, exist_ok=True)
    
    nome_seguro = f"{job_id}_{arquivo.name.replace(' ', '_')}"
    caminho_final = os.path.join(path_dir, nome_seguro)
    
    with open(caminho_final, 'wb+') as destination:
        for chunk in arquivo.chunks():
            destination.write(chunk)
    return caminho_final

# --- VIEWS DE AUTENTICAÇÃO E STATUS ---

@login_required
def me(request):
    u = request.user
    return JsonResponse({
        "authenticated": True,
        "username": u.username,
        "is_staff": u.is_staff,
        "is_superuser": u.is_superuser,
    })

def status_processamento(request, job_id):
    try:
        proc = LogSincronizacao.objects.get(id=job_id)
        return JsonResponse({
            "status": proc.status,
            "progresso": proc.progresso,
            "mensagem": proc.mensagem
        })
    except LogSincronizacao.DoesNotExist:
        return JsonResponse({"erro": "Job não encontrado"}, status=404)

# --- VIEWS DE UPLOAD (DISPARAM O CELERY) ---

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def upload_casos_positivos(request):
    arquivo = request.FILES.get("positivos") or request.FILES.get("casos")
    if not arquivo:
        return JsonResponse({"erro": "Arquivo de positivos não enviado"}, status=400)

    job = LogSincronizacao.objects.create(tipo="positivos", nome_arquivo=arquivo.name, status="na_fila")
    caminho = _salvar_arquivo_temporario(job.id, arquivo)
    
    # Chama a Task do Celery
    task_processar_positivos.delay(job.id, caminho)
    
    return JsonResponse({"sucesso": True, "job_id": job.id})

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def upload_pontos_estrategicos(request):
    arquivo = request.FILES.get("pontos")
    if not arquivo:
        return JsonResponse({"erro": "Arquivo de pontos não enviado"}, status=400)

    job = LogSincronizacao.objects.create(tipo="pontos", nome_arquivo=arquivo.name, status="na_fila")
    caminho = _salvar_arquivo_temporario(job.id, arquivo)
    
    task_processar_pontos.delay(job.id, caminho)
    
    return JsonResponse({"sucesso": True, "job_id": job.id})

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def upload_focos(request):
    arquivo = request.FILES.get("focos")
    if not arquivo:
        return JsonResponse({"erro": "Arquivo de focos não enviado"}, status=400)

    job = LogSincronizacao.objects.create(tipo="focos", nome_arquivo=arquivo.name, status="na_fila")
    caminho = _salvar_arquivo_temporario(job.id, arquivo)
    
    task_processar_focos.delay(job.id, caminho)
    
    return JsonResponse({"sucesso": True, "job_id": job.id})

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def upload_armadilhas(request):
    arquivo = request.FILES.get("armadilhas")
    if not arquivo:
        return JsonResponse({"erro": "Arquivo de armadilhas não enviado"}, status=400)

    job = LogSincronizacao.objects.create(tipo="armadilhas", nome_arquivo=arquivo.name, status="na_fila")
    caminho = _salvar_arquivo_temporario(job.id, arquivo)
    
    task_processar_armadilhas.delay(job.id, caminho)
    
    return JsonResponse({"sucesso": True, "job_id": job.id})