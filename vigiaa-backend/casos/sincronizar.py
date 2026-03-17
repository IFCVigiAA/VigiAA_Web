import re
import threading
from io import StringIO
from django.http import JsonResponse
from django.core.management import call_command
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from casos.models import LogSincronizacao


def _extrair_processados(texto):

    if not texto:
        return []

    numeros = re.findall(
        r'processad(?:o|os)\s*[:=]?\s*(\d+)',
        texto,
        flags=re.IGNORECASE
    )

    return [int(n) for n in numeros]


def rodar_sincronizacao(job_id):

    proc = LogSincronizacao.objects.get(id=job_id)

    out = StringIO()
    err = StringIO()

    try:

        proc.progresso = 10
        proc.mensagem = "Iniciando sincronização"
        proc.save()

        call_command("sincronizar_oficial", stdout=out, stderr=err)

        proc.progresso = 90
        proc.mensagem = "Finalizando sincronização"
        proc.save()

        stdout = out.getvalue()
        stderr = err.getvalue()

        processados_stdout = _extrair_processados(stdout)
        processados_stderr = _extrair_processados(stderr)

        processados = processados_stdout or processados_stderr
        total = sum(processados) if processados else 0

        proc.status = "concluido"
        proc.progresso = 100
        proc.mensagem = f"Sincronização concluída ({total} registros processados)"
        proc.save()

    except Exception as e:

        proc.status = "erro"
        proc.progresso = 100
        proc.mensagem = str(e)
        proc.save()


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def sincronizar_oficial_api(request):

    proc = LogSincronizacao.objects.create(
        tipo="sincronizacao",
        nome_arquivo="sincronizacao_manual",
        hash="manual",
        status="processando",
        progresso=0,
        mensagem="Preparando sincronização"
    )

    thread = threading.Thread(
        target=rodar_sincronizacao,
        args=(proc.id,)
    )

    thread.start()

    return JsonResponse({
        "sucesso": True,
        "job_id": proc.id
    })