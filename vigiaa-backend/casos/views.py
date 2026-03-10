from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from casos.models import Processamento


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
        proc = Processamento.objects.get(id=job_id)
        return JsonResponse({
            "status": proc.status,
            "progresso": proc.progresso,
            "mensagem": proc.mensagem
        })
    except Processamento.DoesNotExist:
        return JsonResponse({"erro": "Job não encontrado"}, status=404)