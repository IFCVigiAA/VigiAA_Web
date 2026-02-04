import unicodedata
import pandas as pd
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_POST
from django.contrib.gis.geos import Point
from casos.models import CasoPositivo


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
    # tenta achar uma linha que tenha cara de cabeçalho da planilha de positivos
    needed_any = [
        {"SINAN", "ENDERECO"},
        {"SINAN", "ENDEREÇO"},
        {"LOCAL DE ATENDIMENTO", "SINAN"},
        {"NOTIFICACAO", "SINAN"},
        {"NOTIFICAÇÃO", "SINAN"},
    ]

    for i in range(min(len(df_raw), 25)):
        row = [_norm(x) for x in df_raw.iloc[i].tolist() if pd.notna(x)]
        row_set = set(row)
        for req in needed_any:
            if req.issubset(row_set):
                return i
    return None


def _colmap(df: pd.DataFrame) -> dict:
    # mapeia nome normalizado -> nome real da coluna
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


def _to_date(v):
    d = pd.to_datetime(v, errors="coerce")
    if pd.isna(d):
        return None
    return d.date()


def _to_int(v):
    if pd.isna(v):
        return None
    try:
        return int(v)
    except:
        try:
            return int(float(v))
        except:
            return None


def _to_str(v):
    if pd.isna(v):
        return None
    return str(v).strip()


@require_POST
@csrf_protect
@staff_member_required
def upload_casos_positivos(request):
    arquivo = request.FILES.get("positivos") or request.FILES.get("casos")
    if not arquivo:
        return JsonResponse({"erro": "Arquivo não enviado"}, status=400)

    try:
        df_raw = pd.read_excel(arquivo, header=None)
        header_idx = _find_header_row(df_raw)
        if header_idx is None:
            return JsonResponse(
                {
                    "erro": "Cabeçalho não encontrado (positivos).",
                    "amostra_topo": df_raw.head(8).fillna("").values.tolist(),
                },
                status=400,
            )

        df = pd.read_excel(arquivo, header=header_idx)
        df.columns = [str(c).replace("\u00a0", " ").strip() for c in df.columns]
        m = _colmap(df)

        c_local = _pick(m, "LOCAL DE ATENDIMENTO", "LOCAL ATENDIMENTO", "LOCAL")
        c_ini = _pick(m, "INICIO SINTOMAS", "INÍCIO SINTOMAS", "INICIO DOS SINTOMAS")
        c_notif = _pick(m, "NOTIFICACAO", "NOTIFICAÇÃO", "DATA NOTIFICACAO", "DATA DA NOTIFICACAO")
        c_sinan = _pick(m, "SINAN")
        c_bairro = _pick(m, "BAIRRO")
        c_nasc = _pick(m, "DATA DE NASCIMENTO", "DATA NASCIMENTO", "DATA_NASC")
        c_obs = _pick(m, "OBSERVACOES", "OBSERVAÇÕES", "OBS")
        c_result = _pick(m, "RESULTADO")
        c_aplic = _pick(m, "APLICACAO", "APLICAÇÃO")
        c_agentes = _pick(m, "AGENTE(S)", "AGENTES", "AGENTE")
        c_prim = _pick(m, "1ª VISITA", "1A VISITA", "PRIM VISITA", "PRIMEIRA VISITA")
        c_sit = _pick(m, "SITUACAO", "SITUAÇÃO")

        # lat/lon podem não existir
        c_lat = _pick(m, "LATITUDE", "LAT")
        c_lon = _pick(m, "LONGITUDE", "LON", "LNG")

        obrig = [c_sinan]  # mínimo pra deduplicar/identificar
        if any(c is None for c in obrig):
            return JsonResponse(
                {"erro": "Colunas obrigatórias não encontradas", "lidas": list(df.columns)},
                status=400,
            )

        inseridos = 0
        atualizados = 0
        pulados = 0

        for _, r in df.iterrows():
            sinan = _to_int(r.get(c_sinan))
            if sinan is None:
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

            defaults = {
                "local_atendimento": _to_str(r.get(c_local)) if c_local else None,
                "inicio_sintomas": _to_date(r.get(c_ini)) if c_ini else None,
                "notificacao": _to_date(r.get(c_notif)) if c_notif else None,
                "bairro": _to_str(r.get(c_bairro)) if c_bairro else None,
                "data_nasc": _to_date(r.get(c_nasc)) if c_nasc else None,
                "observacoes": _to_str(r.get(c_obs)) if c_obs else None,
                "resultado": _to_str(r.get(c_result)) if c_result else None,
                "aplicacao": _to_str(r.get(c_aplic)) if c_aplic else None,
                "agentes": _to_str(r.get(c_agentes)) if c_agentes else None,
                "prim_visita": _to_str(r.get(c_prim)) if c_prim else None,
                "situacao": _to_str(r.get(c_sit)) if c_sit else None,
                "geometry": Point(lon, lat, srid=4674),
            }

            obj, created = CasoPositivo.objects.update_or_create(
                sinan=sinan,
                defaults=defaults,
            )
            if created:
                inseridos += 1
            else:
                atualizados += 1

        return JsonResponse(
            {
                "sucesso": True,
                "header_row": int(header_idx),
                "inseridos": inseridos,
                "atualizados": atualizados,
                "pulados": pulados,
            }
        )

    except Exception as e:
        return JsonResponse({"erro": str(e)}, status=400)
