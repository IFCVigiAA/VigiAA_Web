import pandas as pd
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_POST
from django.contrib.gis.geos import Point

from casos.models import PontoEstrategico, Importacao
from casos.importadores._utils import sha256_arquivo, col, to_str


@require_POST
@csrf_protect
@staff_member_required
def upload_pontos_estrategicos(request):
    arquivo = request.FILES.get("pontos")
    if not arquivo:
        return JsonResponse({"erro": "Arquivo não enviado"}, status=400)

    h = sha256_arquivo(arquivo)
    try:
        if Importacao.objects.filter(tipo="pontos", hash=h).exists():
            return JsonResponse({"sucesso": True, "ja_importado": True, "inseridos": 0, "ignorados": 0})
    except Exception:
        pass

    try:
        df_raw = pd.read_excel(arquivo, header=None)

        header_idx = None
        for i in range(min(len(df_raw), 40)):
            row = [str(x).strip().upper().replace("\u00a0", " ") for x in df_raw.iloc[i].tolist() if pd.notna(x)]
            s = set(row)
            if ("NUMERO" in s or "NÚMERO" in s) and ("ENDERECO" in s or "ENDEREÇO" in s) and ("LATITUDE" in s) and ("LONGITUDE" in s):
                header_idx = i
                break

        if header_idx is None:
            return JsonResponse({"erro": "Cabeçalho não encontrado", "amostra_topo": df_raw.head(12).fillna("").values.tolist()}, status=400)

        df = pd.read_excel(arquivo, header=header_idx)
        df.columns = (
            df.columns.astype(str)
            .str.strip()
            .str.replace("\u00a0", " ", regex=False)
            .str.upper()
        )

        c_num = col(df, "NUMERO", "NÚMERO")
        c_mun = col(df, "MUNICIPIO", "MUNICÍPIO")
        c_loc = col(df, "LOCALIDADE")
        c_end = col(df, "ENDERECO", "ENDEREÇO")
        c_quart = col(df, "QUARTEIROES", "QUARTEIRÕES")
        c_comp = col(df, "COMPLEMENTO")
        c_lat = col(df, "LATITUDE")
        c_lon = col(df, "LONGITUDE")

        obrig = [c_num, c_mun, c_loc, c_end, c_quart, c_comp, c_lat, c_lon]
        if any(c is None for c in obrig):
            return JsonResponse({"erro": "Colunas obrigatórias não encontradas", "lidas": df.columns.tolist()}, status=400)

        existentes = set(PontoEstrategico.objects.values_list("numero", flat=True))
        vistos = set()

        objs = []
        ignorados = 0

        for _, r in df.iterrows():
            numero = to_str(r.get(c_num), default=None)
            if not numero:
                ignorados += 1
                continue

            if numero in existentes or numero in vistos:
                ignorados += 1
                continue

            lat = r.get(c_lat)
            lon = r.get(c_lon)
            if pd.isna(lat) or pd.isna(lon):
                ignorados += 1
                continue

            objs.append(
                PontoEstrategico(
                    numero=numero,
                    municipio=to_str(r.get(c_mun), default=""),
                    localidade=to_str(r.get(c_loc), default=""),
                    endereco=to_str(r.get(c_end), default=""),
                    quarteiroes=to_str(r.get(c_quart), default=""),
                    complemento=to_str(r.get(c_comp), default=""),
                    geometry=Point(float(lon), float(lat), srid=4674),
                )
            )
            vistos.add(numero)

        PontoEstrategico.objects.bulk_create(objs, batch_size=1000)

        try:
            Importacao.objects.create(tipo="pontos", nome_arquivo=getattr(arquivo, "name", "pontos"), hash=h)
        except Exception:
            pass

        return JsonResponse({"sucesso": True, "ja_importado": False, "inseridos": len(objs), "ignorados": ignorados})

    except Exception as e:
        return JsonResponse({"erro": str(e)}, status=500)
