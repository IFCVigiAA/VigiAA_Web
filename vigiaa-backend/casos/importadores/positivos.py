import pandas as pd
from django.http import JsonResponse
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect
from casos.models import CasoPositivo

@require_POST
@csrf_protect
@staff_member_required
def upload_casos_positivos(request):
    if request.method != 'POST':
        return JsonResponse({'erro': 'Método inválido'}, status=405)

    arquivo = (
        request.FILES.get('arquivo')
        or request.FILES.get('casos')
        or request.FILES.get('positivos')
        or next(iter(request.FILES.values()), None)
    )
    if not arquivo:
        return JsonResponse({'erro': 'Arquivo não enviado'}, status=400)

    try:
        df = pd.read_excel(arquivo)

        # normaliza nomes das colunas pra evitar espaço/acentos chatos
        df.columns = (
            df.columns.astype(str)
            .str.strip()
            .str.replace('\u00a0', ' ', regex=False)
        )

        inseridos = 0
        pulados = 0

        for _, row in df.iterrows():
            endereco = row.get('ENDEREÇO') or row.get('ENDERECO')
            sinan = row.get('SINAN')
            notif = row.get('NOTIFICAÇÃO') or row.get('NOTIFICACAO')

            if pd.isna(endereco) or pd.isna(sinan) or pd.isna(notif):
                pulados += 1
                continue

            data = pd.to_datetime(notif, errors='coerce')

            if pd.isna(data):
                pulados += 1
                continue

            CasoPositivo.objects.create(
                endereco=str(endereco).strip(),
                data_notificacao=data.date(),
                sinan=str(sinan).strip()
            )
            inseridos += 1

        return JsonResponse({'sucesso': True, 'inseridos': inseridos, 'pulados': pulados})

    except Exception as e:
        return JsonResponse({'erro': str(e)}, status=400)
