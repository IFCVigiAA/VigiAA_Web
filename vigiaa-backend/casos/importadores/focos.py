import pandas as pd
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_POST
from django.contrib.gis.geos import Point

from casos.models import Foco, Importacao
from casos.importadores._utils import sha256_arquivo, col, to_date, to_int, to_str


@require_POST
@csrf_protect
@staff_member_required
def upload_focos(request):
    arquivo = request.FILES.get("focos")
    if not arquivo:
        return JsonResponse({"erro": "Arquivo não enviado"}, status=400)

    h = sha256_arquivo(arquivo)
    try:
        if Importacao.objects.filter(tipo="focos", hash=h).exists():
            return JsonResponse({"sucesso": True, "ja_importado": True, "inseridos": 0, "ignorados": 0})
    except Exception:
        pass

    try:
        df_raw = pd.read_excel(arquivo, header=None)

        header_idx = None
        for i in range(min(len(df_raw), 50)):
            row = [str(x).strip().upper().replace("\u00a0", " ") for x in df_raw.iloc[i].tolist() if pd.notna(x)]
            s = set(row)
            ok_nfoco = ("Nº FOCO" in s) or ("NO FOCO" in s) or ("N° FOCO" in s) or ("N FOCO" in s)
            ok_loc = "LOCALIDADE" in s
            ok_data = ("DATA DA COLETA" in s) or ("DATA COLETA" in s)
            ok_latlon = ("LATITUDE" in s) and ("LONGITUDE" in s)
            if ok_nfoco and ok_loc and ok_data and ok_latlon:
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

        c_nfoco = col(df, "Nº FOCO", "NO FOCO", "N° FOCO", "N FOCO")
        c_localidade = col(df, "LOCALIDADE")
        c_imovel = col(df, "IMÓVEL", "IMOVEL")
        c_deposito = col(df, "DEPÓSITO", "DEPOSITO")
        c_tipo = col(df, "TIPO DE ATIVIDADE", "TIPO ATIVIDADE")
        c_data = col(df, "DATA DA COLETA", "DATA COLETA")
        c_lat = col(df, "LATITUDE")
        c_lon = col(df, "LONGITUDE")

        obrig = [c_nfoco, c_localidade, c_imovel, c_deposito, c_tipo, c_data, c_lat, c_lon]
        if any(c is None for c in obrig):
            return JsonResponse({"erro": "Colunas obrigatórias não encontradas", "lidas": df.columns.tolist()}, status=400)

        existentes = set(Foco.objects.values_list("n_foco", flat=True))
        vistos = set()

        objs = []
        ignorados = 0

        c_ae_aq = col(df, "A_AEGYPTI_FORM_AQUATICAS", "A. AEGYPTI FORM AQUÁTICAS", "A AEGYPTI FORM AQUÁTICAS")
        c_ae_ad = col(df, "A_AEGYPTI_FORM_ADULTAS", "A. AEGYPTI FORM ADULTAS", "A AEGYPTI FORM ADULTAS")
        c_al_aq = col(df, "A_ALBOPICTUS_FORM_AQUATICAS", "A. ALBOPICTUS FORM AQUÁTICAS", "A ALBOPICTUS FORM AQUÁTICAS")
        c_al_ad = col(df, "A_ALBOPICTUS_FORM_ADULTAS", "A. ALBOPICTUS FORM ADULTAS", "A ALBOPICTUS FORM ADULTAS")
        c_ovo = col(df, "OVO_A_AEGYPTI", "OVO A. AEGYPTI", "OVO A AEGYPTI")

        for _, r in df.iterrows():
            n_foco = to_str(r.get(c_nfoco), default=None)
            if not n_foco:
                ignorados += 1
                continue

            if n_foco in existentes or n_foco in vistos:
                ignorados += 1
                continue

            lat = r.get(c_lat)
            lon = r.get(c_lon)
            if pd.isna(lat) or pd.isna(lon):
                ignorados += 1
                continue

            data_coleta = to_date(r.get(c_data))
            if data_coleta is None:
                ignorados += 1
                continue

            objs.append(
                Foco(
                    n_foco=n_foco,
                    localidade=to_str(r.get(c_localidade), default=""),
                    imovel=to_str(r.get(c_imovel), default=""),
                    deposito=to_str(r.get(c_deposito), default=""),
                    tipo_atividade=to_str(r.get(c_tipo), default=""),
                    data_coleta=data_coleta,
                    a_aegypti_form_aquaticas=to_int(r.get(c_ae_aq), 0),
                    a_aegypti_form_adultas=to_int(r.get(c_ae_ad), 0),
                    a_albopictus_form_aquaticas=to_int(r.get(c_al_aq), 0),
                    a_albopictus_form_adultas=to_int(r.get(c_al_ad), 0),
                    ovo_a_aegypti=to_int(r.get(c_ovo), 0),
                    geometry=Point(float(lon), float(lat), srid=4674),
                )
            )
            vistos.add(n_foco)

        Foco.objects.bulk_create(objs, batch_size=1000)

        try:
            Importacao.objects.create(tipo="focos", nome_arquivo=getattr(arquivo, "name", "focos"), hash=h)
        except Exception:
            pass

        return JsonResponse({"sucesso": True, "ja_importado": False, "inseridos": len(objs), "ignorados": ignorados})

    except Exception as e:
        return JsonResponse({"erro": str(e)}, status=500)
