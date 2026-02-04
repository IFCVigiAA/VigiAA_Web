import unicodedata
import pandas as pd
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_POST
from django.contrib.gis.geos import Point
from casos.models import Armadilha


CENTRO_CAMBORIU = (-27.022986, -48.652135)  # (lat, lon)


def _norm(s) -> str:
    if s is None:
        return ""
    s = str(s).replace("\u00a0", " ").strip()
    s = "".join(
        c for c in unicodedata.normalize("NFD", s)
        if unicodedata.category(c) != "Mn"
    )
    s = s.upper()
    s = s.replace("º", "O").replace("°", "O")
    return " ".join(s.split())


def _find_header_row(df_raw: pd.DataFrame) -> int | None:
    needed_sets = [
        {"NUMERO", "MUNICIPIO", "LOCALIDADE", "ENDERECO"},
        {"NÚMERO", "MUNICÍPIO", "LOCALIDADE", "ENDEREÇO"},
        {"NUMERO", "LOCALIDADE", "ENDERECO"},
        {"TIPO ARMADILHA", "NUMERO"},
    ]

    for i in range(min(len(df_raw), 25)):
        row = [_norm(x) for x in df_raw.iloc[i].tolist() if pd.notna(x)]
        row_set = set(row)
        for req in needed_sets:
            if req.issubset(row_set):
                return i
    return None


def _colmap(df: pd.DataFrame) -> dict:
    m = {}
    for c in df.columns:
        m[_norm(c)] = c
    return m


def _pick(m: dict, *names):
    for n in names:
        key = _norm(n)
        if key in m:
            return m[key]
    return None


def _to_str(v):
    if pd.isna(v):
        return ""
    return str(v).strip()


@require_POST
@csrf_protect
@staff_member_required
def upload_armadilhas(request):
    arquivo = request.FILES.get("armadilhas")
    if not arquivo:
        return JsonResponse({"erro": "Arquivo não enviado"}, status=400)

    try:
        df_raw = pd.read_excel(arquivo, header=None)
        header_idx = _find_header_row(df_raw)
        if header_idx is None:
            return JsonResponse(
                {
                    "erro": "Cabeçalho não encontrado (armadilhas).",
                    "amostra_topo": df_raw.head(8).fillna("").values.tolist(),
                },
                status=400,
            )

        df = pd.read_excel(arquivo, header=header_idx)
        df.columns = [str(c).replace("\u00a0", " ").strip() for c in df.columns]
        m = _colmap(df)

        c_num = _pick(m, "NUMERO", "NÚMERO")
        c_mun = _pick(m, "MUNICIPIO", "MUNICÍPIO")
        c_loc = _pick(m, "LOCALIDADE")
        c_end = _pick(m, "ENDERECO", "ENDEREÇO", "RUA/NUMERO", "RUA/NÚMERO")
        c_comp = _pick(m, "COMPLEMENTO")
        c_quart = _pick(m, "QUARTEIROES", "QUARTEIRÕES", "QUARTEIRAO", "QUARTEIRÃO")
        c_tipo_imovel = _pick(m, "TIPO IMOVEL", "TIPO IMÓVEL")
        c_tipo_arm = _pick(m, "TIPO ARMADILHA")

        c_lat = _pick(m, "LATITUDE", "LAT")
        c_lon = _pick(m, "LONGITUDE", "LON", "LNG")

        obrig = [c_num, c_mun, c_loc, c_end, c_quart, c_tipo_imovel, c_tipo_arm]
        if any(c is None for c in obrig):
            return JsonResponse(
                {
                    "erro": "Colunas obrigatórias não encontradas",
                    "lidas": list(df.columns),
                    "esperadas": ["Numero", "Municipio", "Localidade", "Endereco", "Quarteiroes", "Tipo Imovel", "Tipo Armadilha"],
                },
                status=400,
            )

        inseridos = 0
        duplicados = 0
        pulados = 0

        for _, r in df.iterrows():
            if any(pd.isna(r.get(c)) for c in obrig):
                pulados += 1
                continue

            lat = None
            lon = None
            if c_lat and c_lon:
                try:
                    lat = float(r.get(c_lat))
                    lon = float(r.get(c_lon))
                except:
                    lat = None
                    lon = None

            if lat is None or lon is None:
                lat, lon = CENTRO_CAMBORIU

            numero = _to_str(r.get(c_num))
            municipio = _to_str(r.get(c_mun))
            localidade = _to_str(r.get(c_loc))
            endereco = _to_str(r.get(c_end))
            complemento = _to_str(r.get(c_comp)) if c_comp else ""
            quarteiroes = _to_str(r.get(c_quart))
            tipo_imovel = _to_str(r.get(c_tipo_imovel))
            tipo_armadilha = _to_str(r.get(c_tipo_arm))

            # 🔒 anti-duplicado: só cria se não existir registro igual
            exists = Armadilha.objects.filter(
                numero=numero,
                municipio=municipio,
                localidade=localidade,
                endereco=endereco,
                complemento=complemento,
                quarteiroes=quarteiroes,
                tipo_imovel=tipo_imovel,
                tipo_armadilha=tipo_armadilha,
            ).exists()

            if exists:
                duplicados += 1
                continue

            Armadilha.objects.create(
                numero=numero,
                municipio=municipio,
                localidade=localidade,
                endereco=endereco,
                complemento=complemento,
                quarteiroes=quarteiroes,
                tipo_imovel=tipo_imovel,
                tipo_armadilha=tipo_armadilha,
                geometry=Point(lon, lat, srid=4674),
            )
            inseridos += 1

        return JsonResponse(
            {
                "sucesso": True,
                "header_row": int(header_idx),
                "inseridos": inseridos,
                "duplicados": duplicados,
                "pulados": pulados,
            }
        )

    except Exception as e:
        return JsonResponse({"erro": str(e)}, status=400)
