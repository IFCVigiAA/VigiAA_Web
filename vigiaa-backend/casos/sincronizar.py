import re
from io import StringIO

from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect
from django.contrib.admin.views.decorators import staff_member_required
from django.core.management import call_command


def _extrair_processados(texto: str):
    if not texto:
        return None
    m = re.search(r'processad(?:o|os)\s*[:=]?\s*(\d+)', texto, flags=re.IGNORECASE)
    if m:
        return int(m.group(1))
    m = re.search(r'processed\s*[:=]?\s*(\d+)', texto, flags=re.IGNORECASE)
    if m:
        return int(m.group(1))
    return None


@require_POST
@csrf_protect
@staff_member_required
def sincronizar_oficial_api(request):
    out = StringIO()
    err = StringIO()

    try:
        call_command("sincronizar_oficial", stdout=out, stderr=err)
        stdout = out.getvalue()
        stderr = err.getvalue()

        processados = _extrair_processados(stdout) or _extrair_processados(stderr)

        return JsonResponse(
            {
                "sucesso": True,
                "comando": "sincronizar_oficial",
                "processados": processados,
                "resumo": f"processados {processados}" if processados is not None else "sincronização concluída",
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
