import pandas as pd
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_POST
from django.contrib.gis.geos import Point

from casos.models import ArmadilhaTemp
from casos.importadores._utils import col, to_str, to_int, hash_row


def _norm(v):
    return str(v or "").strip().lower().replace("\u00a0", " ")


def _find_header_idx(df_raw):
    for i in range(len(df_raw)):
        row = [_norm(x) for x in df_raw.iloc[i].tolist()]
        if ("número" in row or "numero" in row) and "localidade" in row and ("endereço" in row or "endereco" in row) and "latitude" in row and "longitude" in row:
            return i
    return None


@require_POST
@csrf_protect
@staff_member_required
def upload_armadilhas(request):
    arquivo = request.FILES.get("armadilhas")
    if not arquivo:
        return JsonResponse({"erro": "Arquivo não enviado"}, status=400)

    try:
        df_raw = pd.read_excel(arquivo, header=None)
        header_idx = _find_header_idx(df_raw)
        if header_idx is None:
            header_idx = 3

        df = pd.read_excel(arquivo, header=header_idx)
        df.columns = df.columns.astype(str).str.strip().str.replace("\u00a0", " ", regex=False)

        c_num = col(df, "Número", "Numero", "NÚMERO", "NUMERO")
        c_mun = col(df, "Município", "Municipio", "MUNICÍPIO", "MUNICIPIO")
        c_loc = col(df, "Localidade", "LOCALIDADE")
        c_end = col(df, "Endereço", "Endereco", "ENDEREÇO", "ENDERECO")
        c_comp = col(df, "Complemento", "COMPLEMENTO")
        c_quart = col(df, "Quarteiroes", "Quarteirões", "QUARTEIROES", "QUARTEIRÕES")
        c_imovel = col(df, "Tipo Imóvel", "Tipo Imovel", "TIPO IMÓVEL", "TIPO IMOVEL")
        c_tipo = col(df, "Tipo Armadilha", "TIPO ARMADILHA")

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

            numero = to_str(r.get(c_num))
            municipio = to_str(r.get(c_mun))
            localidade = to_str(r.get(c_loc))
            endereco = to_str(r.get(c_end))
            complemento = to_str(r.get(c_comp))
            quarteiroes = to_int(r.get(c_quart))
            tipo_imovel = to_str(r.get(c_imovel))
            tipo_armadilha = to_str(r.get(c_tipo))

            h = hash_row(
                "ARM_TEMP",
                numero,
                municipio,
                localidade,
                endereco,
                tipo_imovel,
                tipo_armadilha,
                round(lonv, 6),
                round(latv, 6),
            )

            obj, created = ArmadilhaTemp.objects.update_or_create(
                hash_registro=h,
                defaults=dict(
                    numero=numero or "-",
                    municipio=municipio or "-",
                    localidade=localidade or "-",
                    endereco=endereco or "-",
                    complemento=complemento or "",
                    quarteiroes=str(quarteiroes) if quarteiroes is not None else "",
                    tipo_imovel=tipo_imovel or "",
                    tipo_armadilha=tipo_armadilha or "",
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
