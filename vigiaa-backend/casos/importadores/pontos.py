import pandas as pd
from django.http import JsonResponse
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_POST
from django.contrib.gis.geos import Point
from casos.models import PontoEstrategicoTemp
from casos.importadores._utils import col, to_str, hash_row
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def upload_pontos_estrategicos(request):
    arquivo = request.FILES.get("pontos")
    if not arquivo:
        return JsonResponse({"erro": "Arquivo não enviado"}, status=400)

    try:
        # no teu print o header começa na linha 4 (index 3)
        df = pd.read_excel(arquivo, header=3)
        df.columns = df.columns.astype(str).str.strip().str.replace("\u00a0", " ", regex=False)

        c_num = col(df, "Número", "Numero", "NÚMERO", "NUMERO")
        c_mun = col(df, "Municipio", "Município", "MUNICIPIO", "MUNICÍPIO")
        c_loc = col(df, "Localidade", "LOCALIDADE")
        c_end = col(df, "Endereço", "Endereco", "ENDEREÇO", "ENDERECO")
        c_quart = col(df, "Quarteiroes", "Quarteirões", "QUARTEIROES", "QUARTEIRÕES")
        c_comp = col(df, "Complemento", "COMPLEMENTO")
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
                geom = Point(float(lonv), float(latv), srid=4674)
            except:
                pulados += 1
                continue

            numero = to_str(r.get(c_num))
            municipio = to_str(r.get(c_mun))
            localidade = to_str(r.get(c_loc))
            endereco = to_str(r.get(c_end))
            quarteiroes = to_str(r.get(c_quart))
            complemento = to_str(r.get(c_comp))

            h = hash_row(
                "PONTO_TEMP",
                numero,
                municipio,
                localidade,
                endereco,
                complemento,
                round(float(geom.x), 6),
                round(float(geom.y), 6),
            )

            obj, created = PontoEstrategicoTemp.objects.update_or_create(
                hash_registro=h,
                defaults=dict(
                    numero=numero,
                    municipio=municipio,
                    localidade=localidade,
                    endereco=endereco,
                    quarteiroes=quarteiroes,
                    complemento=complemento,
                    latitude=float(latv),
                    longitude=float(lonv),
                    geometry=geom,
                ),
            )

            inseridos += int(created)
            atualizados += int(not created)

        return JsonResponse({"sucesso": True, "inseridos": inseridos, "atualizados": atualizados, "pulados": pulados})

    except Exception as e:
        return JsonResponse({"erro": str(e)}, status=400)
