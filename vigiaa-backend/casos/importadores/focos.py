import pandas as pd
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.contrib.admin.views.decorators import staff_member_required
from casos.models import Foco
from django.views.decorators.http import require_POST

@require_POST
@csrf_protect
@staff_member_required
def upload_focos(request):
    if request.method != 'POST':
        return JsonResponse({'erro': 'Método inválido'}, status=405)

    arquivo = request.FILES.get('focos')
    if not arquivo:
        return JsonResponse({'erro': 'Arquivo não enviado'}, status=400)

    try:
        df_raw = pd.read_excel(arquivo, header=None)

        header_row = None
        for i, row in df_raw.iterrows():
            if row.astype(str).str.contains('Nº Foco', case=False, na=False).any():
                header_row = i
                break

        if header_row is None:
            return JsonResponse({'erro': 'Cabeçalho não encontrado'}, status=400)

        df = pd.read_excel(arquivo, header=header_row)

        df.columns = (
            df.columns
            .astype(str)
            .str.strip()
            .str.lower()
            .str.replace('º', 'o', regex=False)
            .str.replace('°', 'o', regex=False)
        )

        # garante que as colunas existem
        required = ['no foco', 'data da coleta', 'latitude', 'longitude']
        missing = [c for c in required if c not in df.columns]
        if missing:
            return JsonResponse({
                'erro': 'Colunas obrigatórias não encontradas',
                'missing': missing,
                'columns': df.columns.tolist(),
                'header_row': int(header_row),
                'rows': int(len(df)),
            }, status=400)

        # remove linhas vazias nessas colunas
        df = df.dropna(subset=required)

        criados = 0
        for _, row in df.iterrows():
            Foco.objects.create(
                numero_foco=str(row['no foco']),
                data_coleta=pd.to_datetime(row['data da coleta'], errors='coerce').date(),
                latitude=float(row['latitude']),
                longitude=float(row['longitude']),
            )
            criados += 1

        return JsonResponse({
            'sucesso': True,
            'header_row': int(header_row),
            'rows_lidas': int(len(df_raw)),
            'rows_df': int(len(df)),
            'criados': int(criados),
            'columns': df.columns.tolist(),
        })

    except Exception as e:
        return JsonResponse({'erro': str(e)}, status=400)
