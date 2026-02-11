import pandas as pd
import geocoder

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_POST
from django.db import connection


CORRECOES_ENDERECO = {
    "ALANO SIMAS FILHO": "ALCINO SIMAS FILHO",
    "JUSTINA DE SOUZA PEREIRA": "JUSTINA DE SOUZA PENA",
    "SANTA ALEXANDRE": "SANTO ALEXANDRE",
    "JOÃO BARTOLOMEU": "SÃO BARTOLOMEU",
    "GEREZEM": "MONTE GEREZÉM",
    "JOSE BERNARDES PASSOS": "JOSÉ BERNARDES PASSOS",
    "JOSÉ BERNADES DOS PASSOS": "JOSÉ BERNARDES PASSOS",
    "SANTO EXPEDIDO": "RUA SANTO EXPEDITO",
    "SÃO BRAS, 180": "SÃO BRÁS",
    "SÃO BRAS": "SÃO BRÁS",
    "RIO SENA": "RUA RIO SENNA",
    "LEANDRO BERTOLDI - ": "RUA LEANDRO BERTOLDI",
    "RUA LEANDRO BERTOLDISN": "RUA LEANDRO BERTOLDI",
    "RUA FRANCISCO GARCIA , 961 CENTRO": "RUA FRANCISCO GARCIA, 961",
    "RUA JOÃO MORAES, 4590": "RUA JOÃO MORAES",
    "RUA TEREZA EVANGELISTA GONÇALVES, 360, TABULEIRO": "RUA TEREZA EVANGELISTA GONÇALVES, TABULEIRO",
    "RUA IJUI": "RUA RIO IJUÍ",
    "RUA SANTA CECILIA, 504": "RUA SANTA CECÍLIA",
    "RUA SAMARINO, 414, SANTA REGINA, CAMBORIU": "RUA SAN MARINO, 414, SANTA REGINA, CAMBORIU",
}

COORDS_FIXAS = {
    "RUA SÃO BRÁS": (-27.0246740, -48.6405868),
    "JOSÉ BERNARDES PASSOS": (-27.0307410, -48.6461234),
    "FINLANDIA": (-27.0367205, -48.6751565),
    "RUA RIO SOLIMOES": (-27.0323908, -48.6451871),
    "BR 101 KM 532 MARGINAL, TABULEIRO, CAMBORIÚ": (-26.999199, -48.647584),
    "RODOVIA BR 101": (-26.999199, -48.647584),
    "RUA MONTE ALEGRE": (-27.001054, -48.661927),
    "RUA JURI SILVA": (-27.0307275, -48.6497894),
}

LIMITES_GEO = (-27.10, -26.95, -48.75, -48.60)


def col(df, *nomes):
    cols = {str(c).strip().upper(): c for c in df.columns}
    for n in nomes:
        key = str(n).strip().upper()
        if key in cols:
            return cols[key]
    return None


def _to_str(v):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ""
    s = str(v).strip()
    return s


def _to_int(v):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    try:
        return int(float(str(v).strip().replace(",", ".")))
    except:
        return None


def _to_date(v):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    try:
        dt = pd.to_datetime(v, errors="coerce")
        if pd.isna(dt):
            return None
        return dt.date()
    except:
        return None


def _hash_row(*parts):
    base = "|".join([str(p) for p in parts]).lower()
    import hashlib
    return hashlib.sha256(base.encode("utf-8")).hexdigest()


def _dentro_bbox(lat, lon):
    return (
        LIMITES_GEO[0] <= lat <= LIMITES_GEO[1]
        and LIMITES_GEO[2] <= lon <= LIMITES_GEO[3]
    )


def _geocodificar_endereco(endereco, bairro):
    if not isinstance(endereco, str) or not endereco.strip():
        return None, None, "SEM_ENDERECO"

    rua = endereco.strip().upper()

    for erro, correto in CORRECOES_ENDERECO.items():
        if erro in rua:
            rua = rua.replace(erro, correto)

    for chave, (lat, lon) in COORDS_FIXAS.items():
        if chave in rua:
            return lat, lon, "MANUAL"

    query = f"{rua}, {bairro or ''}, CAMBORIÚ, SC, BRASIL"
    try:
        g = geocoder.arcgis(query)
        if g.ok and g.latlng:
            lat, lon = g.latlng[0], g.latlng[1]
            if _dentro_bbox(lat, lon):
                return lat, lon, "API"
            return None, None, "FORA_LIMITE"
    except:
        pass

    return None, None, "FALHA"


def _get_table_info(table_name: str):
    with connection.cursor() as cur:
        cur.execute(
            """
            SELECT column_name, is_nullable
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = %s
            """,
            [table_name],
        )
        rows = cur.fetchall()
    cols = {name for name, _ in rows}
    not_null = {name for name, nullable in rows if nullable == "NO"}
    return cols, not_null


def _upsert(table: str, row: dict):
    cols = list(row.keys())
    placeholders = ", ".join(["%s"] * len(cols))
    collist = ", ".join([f'"{c}"' for c in cols])

    update_cols = [c for c in cols if c != "hash_registro"]
    set_clause = ", ".join([f'"{c}" = EXCLUDED."{c}"' for c in update_cols])

    sql = f"""
        INSERT INTO "{table}" ({collist})
        VALUES ({placeholders})
        ON CONFLICT ("hash_registro")
        DO UPDATE SET {set_clause}
        RETURNING (xmax = 0) AS inserted;
    """
    values = [row[c] for c in cols]
    with connection.cursor() as cur:
        cur.execute(sql, values)
        inserted = cur.fetchone()[0]
        return bool(inserted)


@require_POST
@csrf_protect
@staff_member_required
def upload_casos_positivos(request):
    arquivo = request.FILES.get("positivos") or request.FILES.get("casos")
    if not arquivo:
        return JsonResponse({"erro": "Arquivo não enviado"}, status=400)

    try:
        df = pd.read_excel(arquivo)
        df.columns = df.columns.astype(str).str.strip().str.replace("\u00a0", " ", regex=False)

        c_local = col(df, "LOCAL DE ATENDIMENTO")
        c_inicio = col(df, "INICIO SINTOMAS", "INÍCIO SINTOMAS")
        c_notif = col(df, "NOTIFICACAO", "NOTIFICAÇÃO")
        c_sinan = col(df, "SINAN")

        c_nome = col(df, "NOME")
        c_end = col(df, "ENDERECO", "ENDEREÇO")
        c_bairro = col(df, "BAIRRO")
        c_mae = col(df, "NOME DA MAE", "NOME DA MÃE")

        c_nasc = col(df, "DATA DE NASCIMENTO", "DATA NASC", "DATA_NASC")
        c_obs = col(df, "OBSERVACOES", "OBSERVAÇÕES")
        c_result = col(df, "RESULTADO")
        c_aplic = col(df, "APLICACAO", "APLICAÇÃO")
        c_agentes = col(df, "AGENTE(S)", "AGENTES")
        c_prim = col(df, "1ª VISITA", "1A VISITA", "PRIM_VISITA")
        c_sit = col(df, "SITUACAO", "SITUAÇÃO")

        table_temp = "casos_positivos_temp"
        table_gl = "casos_positivos_temp_gl"

        cols_temp, not_null_temp = _get_table_info(table_temp)
        cols_gl, not_null_gl = _get_table_info(table_gl)

        inseridos_temp = atualizados_temp = 0
        inseridos_gl = atualizados_gl = 0
        pulados = 0
        pulados_sem_nome = 0

        geo_api = geo_manual = geo_falha = geo_sem_end = geo_fora = 0

        total_linhas = int(len(df))

        for _, r in df.iterrows():
            sinan = _to_int(r.get(c_sinan)) if c_sinan else None
            notif = _to_date(r.get(c_notif)) if c_notif else None
            inicio = _to_date(r.get(c_inicio)) if c_inicio else None
            local = _to_str(r.get(c_local)) if c_local else ""

            nome = _to_str(r.get(c_nome)) if c_nome else ""
            endereco = _to_str(r.get(c_end)) if c_end else ""
            bairro = _to_str(r.get(c_bairro)) if c_bairro else ""
            nome_mae = _to_str(r.get(c_mae)) if c_mae else ""

            nasc = _to_date(r.get(c_nasc)) if c_nasc else None
            obs = _to_str(r.get(c_obs)) if c_obs else ""
            resultado = _to_str(r.get(c_result)) if c_result else ""
            aplicacao = _to_str(r.get(c_aplic)) if c_aplic else ""
            agentes = _to_str(r.get(c_agentes)) if c_agentes else ""
            prim = _to_str(r.get(c_prim)) if c_prim else ""
            situacao = _to_str(r.get(c_sit)) if c_sit else ""

            if not nome:
                pulados_sem_nome += 1
                continue

            h = _hash_row(
                "CASO_POSITIVO",
                sinan or "",
                notif or "",
                inicio or "",
                nome,
                endereco,
                bairro,
                nome_mae,
                resultado,
                aplicacao,
                agentes,
                prim,
                situacao,
            )

            row_temp = {
                "hash_registro": h,
                "local_atendimento": local or None,
                "inicio_sintomas": inicio,
                "notificacao": notif,
                "sinan": sinan,
                "bairro": bairro or None,
                "data_nasc": nasc,
                "observacoes": obs or None,
                "resultado": resultado or None,
                "aplicacao": aplicacao or None,
                "agentes": agentes or None,
                "prim_visita": prim or None,
                "situacao": situacao or None,
                "nome": nome,
                "endereco": endereco or None,
                "nome_mae": nome_mae or None,
            }
            row_temp = {k: v for k, v in row_temp.items() if k in cols_temp}

            ok = True
            for k in not_null_temp:
                if k in row_temp and (row_temp[k] is None or row_temp[k] == ""):
                    ok = False
                    break
            if not ok:
                pulados += 1
                continue

            created = _upsert(table_temp, row_temp)
            inseridos_temp += int(created)
            atualizados_temp += int(not created)

            latf, lonf, status_geo = _geocodificar_endereco(endereco, bairro)

            if status_geo == "API":
                geo_api += 1
            elif status_geo == "MANUAL":
                geo_manual += 1
            elif status_geo == "SEM_ENDERECO":
                geo_sem_end += 1
            elif status_geo == "FORA_LIMITE":
                geo_fora += 1
            else:
                geo_falha += 1

            if latf is None or lonf is None:
                continue

            row_gl = {
                "hash_registro": h,
                "local_atendimento": local or None,
                "inicio_sintomas": inicio,
                "notificacao": notif,
                "sinan": sinan,
                "bairro": bairro or None,
                "data_nasc": nasc,
                "observacoes": obs or None,
                "resultado": resultado or None,
                "aplicacao": aplicacao or None,
                "agentes": agentes or None,
                "prim_visita": prim or None,
                "situacao": situacao or None,
                "nome": nome,
                "endereco": endereco or None,
                "nome_mae": nome_mae or None,
                "geometry": f"SRID=4674;POINT({lonf} {latf})",
            }
            row_gl = {k: v for k, v in row_gl.items() if k in cols_gl}

            ok_gl = True
            for k in not_null_gl:
                if k in row_gl and (row_gl[k] is None or row_gl[k] == ""):
                    ok_gl = False
                    break
            if not ok_gl:
                continue

            created_gl = _upsert(table_gl, row_gl)
            inseridos_gl += int(created_gl)
            atualizados_gl += int(not created_gl)

        return JsonResponse(
            {
                "sucesso": True,
                "dataset": "casos_positivos",
                "total_linhas": total_linhas,
                "temp": {"inseridos": inseridos_temp, "atualizados": atualizados_temp},
                "temp_gl": {"inseridos": inseridos_gl, "atualizados": atualizados_gl},
                "pulados": pulados,
                "pulados_sem_nome": pulados_sem_nome,
                "geocoding": {
                    "api": geo_api,
                    "manual": geo_manual,
                    "sem_endereco": geo_sem_end,
                    "fora_limite": geo_fora,
                    "falha": geo_falha,
                },
                "resumo": f"TEMP: {inseridos_temp} ins, {atualizados_temp} att | GL: {inseridos_gl} ins, {atualizados_gl} att | sem_nome: {pulados_sem_nome}",
            }
        )

    except Exception as e:
        return JsonResponse({"erro": str(e)}, status=400)
