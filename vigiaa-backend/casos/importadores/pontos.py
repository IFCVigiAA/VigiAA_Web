import pandas as pd
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_POST
from casos.models import PontoEstrategico
def _norm(s: str) -> str:
    return (
        str(s).strip().lower()
        .replace("º", "o")
        .replace("°", "o")
    )


@require_POST
@csrf_protect
@staff_member_required
def upload_pontos_estrategicos(request):
    if request.method != "POST":
        return JsonResponse({"erro": "Método inválido"}, status=405)

    arquivo = request.FILES.get("pontos")
    if not arquivo:
        return JsonResponse({"erro": "Arquivo não enviado"}, status=400)

    try:
        df_raw = pd.read_excel(arquivo, header=None)

        header_idx = None
        for i in range(len(df_raw)):
            row = [_norm(x) for x in df_raw.iloc[i].tolist() if pd.notna(x)]
            row_set = set(row)
            if ("latitude" in row_set) and ("longitude" in row_set):
                header_idx = i
                break

        if header_idx is None:
            return JsonResponse({
                "erro": "Não achei a linha de cabeçalho (preciso ver 'Latitude' e 'Longitude').",
                "amostra_topo": df_raw.head(6).fillna("").values.tolist()
            }, status=400)

        header = df_raw.iloc[header_idx].tolist()
        cols = []
        for j, h in enumerate(header):
            if pd.isna(h) or str(h).strip() == "":
                cols.append(f"col_{j}")
            else:
                cols.append(_norm(h))

        df = df_raw.iloc[header_idx + 1:].copy()
        df.columns = cols

        if "latitude" not in df.columns or "longitude" not in df.columns:
            return JsonResponse({
                "erro": "Colunas necessárias não encontradas após normalização",
                "colunas_lidas": list(df.columns)
            }, status=400)

        inseridos = 0
        for _, row in df.iterrows():
            lat = row.get("latitude")
            lon = row.get("longitude")

            if pd.isna(lat) or pd.isna(lon):
                continue

            PontoEstrategico.objects.create(
                latitude=float(lat),
                longitude=float(lon),
            )
            inseridos += 1

        return JsonResponse({"sucesso": True, "inseridos": inseridos})

    except Exception as e:
        return JsonResponse({"erro": str(e)}, status=400)
