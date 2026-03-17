import os
import pandas as pd
import geocoder
import hashlib
import unicodedata
from celery import shared_task
from django.db import connection
from django.contrib.gis.geos import Point
from django.conf import settings

# Importação dos modelos do seu projeto VigiAA
from casos.models import (
    LogSincronizacao, PontoEstrategicoTemp, FocoTemp, 
    ArmadilhaTemp, CasoPositivoTemp, CasoPositivoTempGL
)

# --- 1. CONFIGURAÇÕES DE GEO E CORREÇÕES ---

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
    "RUA FRANCISCO GARCIA , 961 CENTRO": "RUA FRANCISCO GARCIA, 961",
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

# --- 2. FERRAMENTAS DE NORMALIZAÇÃO E TRATAMENTO ---

def _normalize(s):
    """Limpa acentos e lixo de formatação para garantir o mapeamento das colunas."""
    if not s: return ""
    s = str(s).strip().upper()
    s = unicodedata.normalize("NFKD", s).encode("ASCII", "ignore").decode("ASCII")
    s = s.replace("\xa0", " ")
    return " ".join(s.split())

def col(df, *nomes):
    """Acha a coluna no DataFrame ignorando acentos."""
    cols_mapeadas = {_normalize(c): c for c in df.columns}
    for n in nomes:
        key = _normalize(n)
        if key in cols_mapeadas:
            return cols_mapeadas[key]
    return None

def _to_str(v):
    if v is None or (isinstance(v, float) and pd.isna(v)): return ""
    return str(v).strip()

def _to_int(v):
    if v is None or (isinstance(v, float) and pd.isna(v)): return None
    try: return int(float(str(v).replace(",", ".")))
    except: return None

def _to_date(v):
    if v is None or (isinstance(v, float) and pd.isna(v)): return None
    try:
        dt = pd.to_datetime(v, dayfirst=True, errors="coerce")
        return dt.date() if not pd.isna(dt) else None
    except: return None

def _hash_row(*parts):
    """Gera um identificador único para cada registro."""
    base = "|".join([_normalize(str(p)) for p in parts if p]).lower()
    return hashlib.sha256(base.encode("utf-8")).hexdigest()

def _get_table_info(table_name: str):
    with connection.cursor() as cur:
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = %s", [table_name])
        return {row[0] for row in cur.fetchall()}

def _upsert_raw(table: str, row: dict):
    cols = list(row.keys())
    placeholders = ", ".join(["%s"] * len(cols))
    collist = ", ".join([f'"{c}"' for c in cols])
    update_cols = [c for c in cols if c != "hash_registro"]
    set_clause = ", ".join([f'"{c}" = EXCLUDED."{c}"' for c in update_cols])
    sql = f'INSERT INTO "{table}" ({collist}) VALUES ({placeholders}) ON CONFLICT ("hash_registro") DO UPDATE SET {set_clause}'
    with connection.cursor() as cur:
        cur.execute(sql, [row[c] for c in cols])

def _geocodificar_endereco(endereco, bairro):
    def_lat, def_lon = -27.022986, -48.652135
    if not endereco: return def_lat, def_lon
    rua = str(endereco).upper()
    for erro, correto in CORRECOES_ENDERECO.items():
        if erro in rua: rua = rua.replace(erro, correto)
    for chave, (lat, lon) in COORDS_FIXAS.items():
        if chave in rua: return float(lat), float(lon)
    query = f"{rua}, {bairro or ''}, CAMBORIÚ, SC, BRASIL"
    try:
        g = geocoder.arcgis(query)
        if g.ok and g.latlng: return float(g.latlng[0]), float(g.latlng[1])
    except: pass
    return def_lat, def_lon

# --- 3. TASKS ---

@shared_task(bind=True)
def task_processar_positivos(self, job_id, arquivo_path):
    try:
        log = LogSincronizacao.objects.get(id=job_id)
        df = pd.read_excel(arquivo_path)
        
        c_local = col(df, "LOCAL DE ATENDIMENTO")
        c_inicio = col(df, "INÍCIO SINTOMAS", "INICIO SINTOMAS")
        c_notif = col(df, "NOTIFICAÇÃO", "NOTIFICACAO")
        c_sinan = col(df, "SINAN")
        c_nome = col(df, "NOME")
        c_end = col(df, "ENDEREÇO", "ENDERECO")
        c_bairro = col(df, "BAIRRO")
        c_mae = col(df, "NOME DA MÃE", "NOME DA MAE")
        c_nasc = col(df, "DATA DE NASCIMENTO")
        c_obs = col(df, "OBSERVAÇÕES", "OBSERVACOES")
        c_result = col(df, "RESULTADO")
        c_aplic = col(df, "APLICAÇÃO", "APLICACAO")
        c_agentes = col(df, "AGENTE(S)", "AGENTES")
        c_prim = col(df, "1ª VISITA", "1A VISITA")
        c_sit = col(df, "SITUAÇÃO", "SITUACAO")

        # --- ORDENAÇÃO E HERANÇA DE DATA NO PANDAS ---
        if c_inicio:
            df[c_inicio] = pd.to_datetime(df[c_inicio], dayfirst=True, errors="coerce")
            df[c_inicio] = df[c_inicio].where(df[c_inicio].dt.year >= 2000)
            # Ordena para garantir cronologia correta
            df = df.sort_values(by=c_inicio, ascending=True).reset_index(drop=True)
            df[c_inicio] = df[c_inicio].ffill()

        cols_db = _get_table_info("casos_positivos_temp")
        cols_gl = _get_table_info("casos_positivos_temp_gl")
        total = len(df)

        for i, (_, r) in enumerate(df.iterrows()):
            nome = _to_str(r.get(c_nome))
            if not nome: continue
            
            sinan = _to_str(r.get(c_sinan))
            endereco = _to_str(r.get(c_end))
            bairro = _to_str(r.get(c_bairro))
            data_nasc = _to_str(r.get(c_nasc))
            data_notif = _to_str(r.get(c_notif))

            # --- HASH REFORÇADO (Evita que linha 25 sobrescreva a 43) ---
            h = _hash_row("POS", sinan, nome, endereco, data_nasc, data_notif)
            
            row_temp = {
                "hash_registro": h,
                "local_atendimento": _to_str(r.get(c_local)) or None,
                "inicio_sintomas": r.get(c_inicio).date() if pd.notna(r.get(c_inicio)) else None,
                "notificacao": _to_date(r.get(c_notif)),
                "sinan": _to_int(sinan),
                "nome": nome, 
                "endereco": endereco or None,
                "bairro": bairro or None,
                "nome_mae": _to_str(r.get(c_mae)) or None,
                "data_nasc": _to_date(r.get(c_nasc)),
                "observacoes": _to_str(r.get(c_obs)) or None,
                "resultado": _to_str(r.get(c_result)) or None,
                "aplicacao": _to_str(r.get(c_aplic)) or None,
                "agentes": _to_str(r.get(c_agentes)) or None,
                "prim_visita": _to_str(r.get(c_prim)) or None,
                "situacao": _to_str(r.get(c_sit)) or None,
            }

            row_save = {k: v for k, v in row_temp.items() if k in cols_db}
            _upsert_raw("casos_positivos_temp", row_save)

            lat, lon = _geocodificar_endereco(endereco, bairro)
            row_gl = row_save.copy()
            row_gl["geometry"] = f"SRID=4674;POINT({float(lon)} {float(lat)})"
            
            row_gl_save = {k: v for k, v in row_gl.items() if k in cols_gl}
            _upsert_raw("casos_positivos_temp_gl", row_gl_save)

            if i % 20 == 0:
                log.progresso = int((i/total)*100); log.save()

        log.status = "finalizado"; log.progresso = 100; log.save()
        if os.path.exists(arquivo_path): os.remove(arquivo_path)
    except Exception as e:
        LogSincronizacao.objects.filter(id=job_id).update(status="erro", mensagem=str(e))

@shared_task(bind=True)
def task_processar_pontos(self, job_id, arquivo_path):
    try:
        log = LogSincronizacao.objects.get(id=job_id)
        df = pd.read_excel(arquivo_path, header=3)
        c_num = col(df, "NÚMERO", "NUMERO")
        c_lat = col(df, "LATITUDE"); c_lon = col(df, "LONGITUDE")
        for i, (_, r) in enumerate(df.iterrows()):
            lat, lon = r.get(c_lat), r.get(c_lon)
            if pd.isna(lat) or pd.isna(lon): continue
            h = _hash_row("PONTO", _to_str(r.get(c_num)), lat, lon)
            PontoEstrategicoTemp.objects.update_or_create(
                hash_registro=h, defaults={
                    "numero": _to_str(r.get(c_num)), 
                    "geometry": Point(float(lon), float(lat), srid=4674), 
                    "latitude": float(lat), "longitude": float(lon)
                }
            )
        log.status = "finalizado"; log.save()
        if os.path.exists(arquivo_path): os.remove(arquivo_path)
    except Exception as e:
        LogSincronizacao.objects.filter(id=job_id).update(status="erro", mensagem=str(e))

@shared_task(bind=True)
def task_processar_focos(self, job_id, arquivo_path):
    try:
        log = LogSincronizacao.objects.get(id=job_id)
        df_raw = pd.read_excel(arquivo_path, header=None)
        h_idx = 0
        for idx, row in df_raw.iterrows():
            row_str = [_normalize(str(x)) for x in row]
            if "N FOCO" in row_str or "REGIONAL" in row_str:
                h_idx = idx + 1; break
        df = pd.read_excel(arquivo_path, skiprows=h_idx)
        c_nf = col(df, "Nº FOCO", "N FOCO")
        c_lat = col(df, "LATITUDE"); c_lon = col(df, "LONGITUDE")
        for i, (_, r) in enumerate(df.iterrows()):
            lat, lon = r.get(c_lat), r.get(c_lon)
            if pd.isna(lat) or pd.isna(lon): continue
            h = _hash_row("FOCO", _to_str(r.get(c_nf)), lat, lon)
            FocoTemp.objects.update_or_create(
                hash_registro=h, defaults={
                    "n_foco": _to_str(r.get(c_nf)), 
                    "geometry": Point(float(lon), float(lat), srid=4674), 
                    "latitude": float(lat), "longitude": float(lon)
                }
            )
        log.status = "finalizado"; log.save()
        if os.path.exists(arquivo_path): os.remove(arquivo_path)
    except Exception as e:
        LogSincronizacao.objects.filter(id=job_id).update(status="erro", mensagem=str(e))

@shared_task(bind=True)
def task_processar_armadilhas(self, job_id, arquivo_path):
    try:
        log = LogSincronizacao.objects.get(id=job_id)
        df = pd.read_excel(arquivo_path, header=3)
        c_num = col(df, "NÚMERO", "NUMERO")
        c_lat = col(df, "LATITUDE"); c_lon = col(df, "LONGITUDE")
        for i, (_, r) in enumerate(df.iterrows()):
            lat, lon = r.get(c_lat), r.get(c_lon)
            if pd.isna(lat) or pd.isna(lon): continue
            h = _hash_row("ARM", _to_str(r.get(c_num)), lon, lat)
            ArmadilhaTemp.objects.update_or_create(
                hash_registro=h, defaults={
                    "numero": _to_str(r.get(c_num)), 
                    "geometry": Point(float(lon), float(lat), srid=4674), 
                    "latitude": float(lat), "longitude": float(lon)
                }
            )
        log.status = "finalizado"; log.save()
        if os.path.exists(arquivo_path): os.remove(arquivo_path)
    except Exception as e:
        LogSincronizacao.objects.filter(id=job_id).update(status="erro", mensagem=str(e))