import re
from io import StringIO
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.admin.views.decorators import staff_member_required
from django.core.management import call_command


def _extrair_processados(texto: str):
    if not texto:
        return []

    numeros = re.findall(
        r'processad(?:o|os)\s*[:=]?\s*(\d+)',
        texto,
        flags=re.IGNORECASE
    )

    return [int(n) for n in numeros]


def sincronizar_oficial_api(request):
    out = StringIO()
    err = StringIO()

    try:
        call_command("sincronizar_oficial", stdout=out, stderr=err)
        stdout = out.getvalue()
        stderr = err.getvalue()

        processados_stdout = _extrair_processados(stdout)
        processados_stderr = _extrair_processados(stderr)

        processados = processados_stdout or processados_stderr
        total = sum(processados) if processados else 0

        return JsonResponse(
    {
        "sucesso": True,
        "comando": "sincronizar_oficial",
        "processados_por_tabela": processados,
        "total_processados": total,
        "stdout": stdout[-4000:],
        "stderr": stderr[-4000:],
    }
)
    except Exception as e:
        stdout = out.getvalue()
        stderr = err.getvalue()
        return JsonResponse(
            {
                "erro": str(e),
                "comando": "sincronizar_oficial",
                "stdout": stdout[-4000:],
                "stderr": stderr[-4000:],
            },
            status=400,
        )
