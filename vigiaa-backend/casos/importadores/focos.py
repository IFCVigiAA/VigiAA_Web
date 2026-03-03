import pandas as pd
from django.http import JsonResponse

from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_POST
from django.contrib.gis.geos import Point
from casos.models import FocoTemp
from casos.importadores._utils import col, to_date, to_int, to_str, hash_row
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated



def _norm(v):
    return str(v or "").strip().lower().replace("\u00a0", " ")


def _find_header_idx(df_raw):
    for i in range(len(df_raw)):
        row = [_norm(x) for x in df_raw.iloc[i].tolist()]
        if (("nº foco" in row or "n° foco" in row or "no foco" in row) and
            "regional" in row and
            ("município" in row or "municipio" in row) and
            "rua/número" in row and
            "latitude" in row and "longitude" in row):
            return i
    return None


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def upload_focos(request):
    arquivo = request.FILES.get("focos")
    if not arquivo:
        return JsonResponse({"erro": "Arquivo não enviado"}, status=400)

    try:
        df_raw = pd.read_excel(arquivo, header=None)
        header_idx = _find_header_idx(df_raw)
        if header_idx is None:
            return JsonResponse({"erro": "Cabeçalho não encontrado"}, status=400)

        df = pd.read_excel(arquivo, header=header_idx)
        df.columns = df.columns.astype(str).str.strip().str.replace("\u00a0", " ", regex=False)

        c_nfoco = col(df, "Nº Foco", "N° Foco", "No Foco", "N Foco")
        c_regional = col(df, "Regional", "REGIONAL")
        c_municipio = col(df, "Município", "Municipio", "MUNICÍPIO", "MUNICIPIO")
        c_localidade = col(df, "Localidade", "LOCALIDADE")

        c_rua_num = col(df, "Rua/número", "Rua/numero", "RUA/NÚMERO", "RUA/NUMERO")
        c_comp = col(df, "Complemento", "COMPLEMENTO")
        c_quart = col(df, "Quarteirão", "Quarteirao", "QUARTEIRÃO", "QUARTEIRAO")

        c_imovel = col(df, "Imóvel", "IMÓVEL", "Imovel", "IMOVEL")
        c_deposito = col(df, "Depósito", "DEPÓSITO", "Deposito", "DEPOSITO")
        c_tipo = col(df, "Tipo de Atividade", "TIPO DE ATIVIDADE")

        c_data_coleta = col(df, "Data da Coleta", "DATA DA COLETA")
        c_data_entrada = col(df, "Data de Entrada", "DATA DE ENTRADA")
        c_data_exame = col(df, "Data do Exame", "DATA DO EXAME")

        c_aa_aq = col(df, "A. aegypti formas aquáticas", "A. AEGYPTI FORMAS AQUÁTICAS")
        c_aa_ad = col(df, "A. aegypti formas adultas", "A. AEGYPTI FORMAS ADULTAS")
        c_al_aq = col(df, "A. albopictus formas aquáticas", "A. ALBOPICTUS FORMAS AQUÁTICAS")
        c_al_ad = col(df, "A. albopictus formas adultas", "A. ALBOPICTUS FORMAS ADULTAS")
        c_ovo = col(df, "Ovo A. aegypti", "OVO A. AEGYPTI", "Ovo A. Aegypti")

        c_lat = col(df, "Latitude", "LATITUDE")
        c_lon = col(df, "Longitude", "LONGITUDE")

        inseridos = atualizados = pulados = 0

        for _, r in df.iterrows():
            latv = r.get(c_lat)
            lonv = r.get(c_lon)
            if pd.isna(latv) or pd.isna(lonv):
                pulados += 1
                continue

            try:
                latv = float(latv)
                lonv = float(lonv)
                geom = Point(lonv, latv, srid=4674)
            except:
                pulados += 1
                continue

            n_foco = to_str(r.get(c_nfoco))
            regional = to_str(r.get(c_regional))
            municipio = to_str(r.get(c_municipio))
            localidade = to_str(r.get(c_localidade))
            rua_numero = to_str(r.get(c_rua_num))
            complemento = to_str(r.get(c_comp))
            quarteirao = to_str(r.get(c_quart))

            imovel = to_str(r.get(c_imovel))
            deposito = to_str(r.get(c_deposito))
            tipo_atividade = to_str(r.get(c_tipo))

            data_coleta = to_date(r.get(c_data_coleta))
            data_entrada = to_date(r.get(c_data_entrada))
            data_exame = to_date(r.get(c_data_exame))

            h = hash_row(
                "FOCO_TEMP",
                n_foco,
                regional,
                municipio,
                localidade,
                rua_numero,
                data_coleta or "",
                data_entrada or "",
                round(lonv, 6),
                round(latv, 6),
            )

            obj, created = FocoTemp.objects.update_or_create(
                hash_registro=h,
                defaults=dict(
                    n_foco=(n_foco[:30] if n_foco else h[:30]),
                    regional=regional or "-",
                    municipio=municipio or "-",
                    localidade=localidade or "-",
                    rua_numero=rua_numero or "-",
                    complemento=complemento or "",
                    quarteirao=quarteirao or "",
                    imovel=imovel or "",
                    deposito=deposito or "",
                    tipo_atividade=tipo_atividade or "",
                    data_coleta=data_coleta,
                    data_entrada=data_entrada,
                    data_exame=data_exame,
                    a_aegypti_form_aquaticas=to_int(r.get(c_aa_aq)),
                    a_aegypti_form_adultas=to_int(r.get(c_aa_ad)),
                    a_albopictus_form_aquaticas=to_int(r.get(c_al_aq)),
                    a_albopictus_form_adultas=to_int(r.get(c_al_ad)),
                    ovo_a_aegypti=to_int(r.get(c_ovo)),
                    latitude=latv,
                    longitude=lonv,
                    geometry=geom,
                ),
            )

            inseridos += int(created)
            atualizados += int(not created)

        return JsonResponse({"sucesso": True, "inseridos": inseridos, "atualizados": atualizados, "pulados": pulados})

    except Exception as e:
        return JsonResponse({"erro": str(e)}, status=400)
