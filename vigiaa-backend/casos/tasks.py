import os
import re
import json
import logging
import unicodedata
import difflib
import pandas as pd
import geocoder
from celery import shared_task
from django.db import connection, transaction
from django.contrib.gis.geos import Point
from casos.importadores._utils import to_int
from casos.importadores._utils import col, hash_row, to_date, to_int, to_str
from casos.utils.log_errors import ErrorLogger
from .models import (
    LogSincronizacao, PontoEstrategicoTemp, FocoTemp,
    ArmadilhaTemp, CasoPositivoTemp, CasoPositivoTempGL, OvitrampaTemp
)

logger = logging.getLogger(__name__)

# ==============================================================================
# DICIONÁRIOS DE APOIO E REGRAS DE NEGÓCIO DE CAMBORIÚ
# ==============================================================================

CORRECOES_ENDERECO = {
    "RUA ANTONIO AZEMIRO BITTENCOURT": "RUA ANTÔNIO CASSEMIRO BITTENCOURT, CENTRO",
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
    "RUA NORUEGA, 88": "AVENIDA NORUEGA, 100",
    "RUA SETE DE SETEMBRO, 459, CENTRO": "RUA SETE DE SETEMBRO, CENTRO",
    "ESTRADA GERAL DO BRAÇO": "RUA PAULO DALLAGO",
    "ESTRADA GERAL RIO DO MEIO": "RUA JOSÉ CORREIA DA LUIZ",
    "RUA GERAL DA VILA CONCEIÇÃO, 52, CEDROS": "RUA PAULO JOSÉ LORENZETTI, MACACOS",
    "RUA JOÃO MELO, 8": "RUA JOÃO MELO, 80",
    "JOSÉ ALEXANDRE": "JOSÉ ALEXANDRE BOLDA",
    "MONTE ITAIPAVA": "MONTE ITATIAIA",
    "RUA OLHO DE BONECA": "TRAVESSA OLHO DE BONECA",
    "RUA RIO GRANDE DO NORTE, 93, LIDIA DUARTE": "RUA RIO GRANDE DO NORTE, 93, AREIAS",
    "AV.": "AVENIDA",
    "PEQUIM": "ESTOCOLMO",
    "LAPAZ": "LA PAZ",
    "CRUZEIROS/N": "CRUZEIRO"
}

COORDS_FIXAS = {
    "PREFEITURA DE CAMBORIU": (-27.0245, -48.6534),
    "RUA MONTE EBAU": (-26.998638, -48.670495),
    "RUA ODETE EPIFANIA DA SILVA, 901": (-27.039804, -48.646420)
}

CENTROIDES_BAIRROS = {
    "CENTRO": (-27.0253, -48.6531),
    "MONTE ALEGRE": (-27.0142, -48.6258),
    "TABULEIRO": (-27.0175, -48.6381),
    "AREIAS": (-27.0321, -48.6374),
    "RIO PEQUENO": (-27.0396, -48.6291),
    "SÃO FRANCISCO DE ASSIS": (-27.0165, -48.6192),
    "LIDIA DUARTE": (-27.0241, -48.6433),
    "SANTA REGINA": (-27.0113, -48.6455),
    "CEDRO": (-27.0365, -48.6582),
    "MACACOS": (-27.0811, -48.6822),
    "RIO DO MEIO": (-27.0089, -48.7171),
    "VILA CONCEICAO": (-27.0450, -48.6500)
}

CENTRO_MAPA_CAMBORIU = (-27.0245, -48.6534)
LIMITES_GEO = [-27.2000, -26.9000, -48.8000, -48.5000]

ESQUEMA_SINONIMOS_CASOS = {
    'local_atendimento': ['LOCAL NOTIFICAÇÃO', 'LOCAL_NOTIFICACAO', 'LOCAL ATENDIMENTO', 'UNIDADE'],
    'notificacao': ['DATA NOT.', 'DATA_NOTIFICACAO', 'NOTIFICACAO', 'DATA NOTIFICACAO'],
    'inicio_sintomas': ['INICIO SINTOMAS', 'INICIO_SINTOMAS', 'DATA SINTOMAS', 'DT_SINTOMAS'],
    'sinan': ['SINAN', 'N_SINAN', 'NUMERO_SINAN', 'NUM_SINAN'],
    'nome': ['NOME COMPLETO', 'NOME_COMPLETO', 'NOME', 'PACIENTE'],
    'data_nasc': ['NASCIMENTO', 'DATA_NASC', 'DATA DE NASCIMENTO', 'DT_NASC'],
    'sexo': ['SEXO'],
    'endereco': ['ENDEREÇO', 'ENDERECO', 'LOGRADOURO', 'RUA'],
    'bairro': ['BAIRRO', 'LOCALIDADE'],
    'resultado': ['RESULTADO', 'CLASSIFICACAO'],
    'latitude': ['LATITUDE', 'LAT', 'Y'],
    'longitude': ['LONGITUDE', 'LNG', 'LON', 'X'],
    'situacao': ['SITUAÇÃO', 'SITUACAO', 'STATUS'],
    'observacoes': ['OBSERVAÇÃO', 'OBSERVACAO', 'OBS']
}


# ==============================================================================
# FUNÇÕES DE TRATAMENTO TEXTUAL E DATAS
# ==============================================================================

def _normalizar_texto(texto):
    if pd.isna(texto) or texto is None:
        return ""
    s = str(texto).strip().lower()
    s = ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
    s = re.sub(r'[.ªº]', '', s)
    return s.replace(' ', '_')

def _normalize_legado(s):
    if not s:
        return ""
    s = str(s).strip().upper()
    s = unicodedata.normalize("NFKD", s).encode("ASCII", "ignore").decode("ASCII")
    return " ".join(s.replace("\xa0", " ").split())

def _corrigir_endereco_fuzzy(endereco_atual):
    if pd.isna(endereco_atual) or not endereco_atual:
        return ""
    rua_tabela = str(endereco_atual).upper().strip()

    # 1. Substituição exata e substring
    for erro, correto in CORRECOES_ENDERECO.items():
        if erro.upper() in rua_tabela:
            rua_tabela = rua_tabela.replace(erro.upper(), correto.upper())

    # 2. Fuzzy Matching por palavra
    chaves_erros = [k.upper() for k in CORRECOES_ENDERECO.keys()]
    palavras_rua = rua_tabela.split()
    for palavra in palavras_rua:
        match = difflib.get_close_matches(palavra, chaves_erros, n=1, cutoff=0.85)
        if match:
            chave_encontrada = match[0]
            valor_correto = CORRECOES_ENDERECO.get(chave_encontrada, palavra)
            if valor_correto:
                rua_tabela = rua_tabela.replace(palavra, valor_correto.upper())

    return rua_tabela

def _parse_data_segura(val):
    if val is None or pd.isna(val):
        return None

    try:
        f = float(val)
        if not pd.isna(f) and f > 1000:
            dt = pd.Timestamp('1899-12-30') + pd.Timedelta(days=int(f))
            if 1900 <= dt.year <= 2100:
                return dt.date()
    except (ValueError, TypeError):
        pass

    if hasattr(val, 'date'):
        d = val.date()
        if 1900 <= d.year <= 2100:
            return d

    s = str(val).strip()
    if not s or s.upper() in ['NAN', 'NONE', 'NAT', 'NULL', '']:
        return None

    if s.endswith(' 00:00:00'):
        s = s[:-9]

    try:
        dt = pd.to_datetime(s, dayfirst=True, errors='coerce')
        if pd.notna(dt) and 1900 <= dt.year <= 2100:
            return dt.date()
    except Exception:
        pass

    return None

def _get_str(r, col_name, maxlen=None, default=None):
    if not col_name or col_name not in r.index:
        return default
    val = r.get(col_name)
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return default
    result = str(val).strip()
    if not result or result.upper() in ['NAN', 'NONE', 'NULL', 'NAT']:
        return default
    if maxlen:
        result = result[:maxlen]
    return result

def _resolver_colunas_casos(df, mapeamento_customizado=None):
    cols_resolvidas = {}
    if mapeamento_customizado and isinstance(mapeamento_customizado, dict):
        for campo_bd, col_planilha in mapeamento_customizado.items():
            if col_planilha and col_planilha in df.columns:
                cols_resolvidas[campo_bd] = col_planilha
            else:
                cols_resolvidas[campo_bd] = None
        return cols_resolvidas

    colunas_df_norm = {_normalizar_texto(c): c for c in df.columns}
    for campo_bd, apelidos in ESQUEMA_SINONIMOS_CASOS.items():
        col_encontrada = None
        for apelido in apelidos:
            apelido_norm = _normalizar_texto(apelido)
            if apelido_norm in colunas_df_norm:
                col_encontrada = colunas_df_norm[apelido_norm]
                break
        cols_resolvidas[campo_bd] = col_encontrada

    return cols_resolvidas


# ==============================================================================
# GEOCODIFICAÇÃO EM CASCATA (ARCGIS + FIXAS + BAIRROS + BOUNDING BOX)
# ==============================================================================

def _geocodificar_cascata(endereco, bairro):
    rua = _corrigir_endereco_fuzzy(endereco) if endereco else ""
    bairro_str = str(bairro).upper().strip() if bairro and pd.notna(bairro) else ""

    if (not rua or rua == "NAN") and (not bairro_str or bairro_str == "NAN"):
        return CENTRO_MAPA_CAMBORIU[0], CENTRO_MAPA_CAMBORIU[1]

    # 1. Checagem em Coordenadas Fixas Manuais
    if rua and rua != "NAN":
        for chave, coords in COORDS_FIXAS.items():
            if chave.upper() in rua:
                return coords[0], coords[1]

    # 2. Busca Endereço Completo via ArcGIS
    if rua and rua != "NAN":
        query_rua = f"{rua}, {bairro_str}, CAMBORIÚ, SC, BRASIL" if bairro_str else f"{rua}, CAMBORIÚ, SC, BRASIL"
        try:
            g = geocoder.arcgis(query_rua, timeout=5)
            if g.ok and g.latlng:
                lat, lng = float(g.latlng[0]), float(g.latlng[1])
                if (LIMITES_GEO[0] <= lat <= LIMITES_GEO[1] and LIMITES_GEO[2] <= lng <= LIMITES_GEO[3]):
                    return lat, lng
        except Exception:
            pass

    # 3. Fallback: Centroide Manual do Bairro
    if bairro_str and bairro_str != "NAN":
        for chave_bairro, coords_bairro in CENTROIDES_BAIRROS.items():
            if chave_bairro in bairro_str:
                return coords_bairro[0], coords_bairro[1]

        # 4. Fallback: Bairro via ArcGIS
        query_bairro = f"BAIRRO {bairro_str}, CAMBORIÚ, SC, BRASIL"
        try:
            g = geocoder.arcgis(query_bairro, timeout=5)
            if g.ok and g.latlng:
                lat, lng = float(g.latlng[0]), float(g.latlng[1])
                dist = abs(lat - CENTRO_MAPA_CAMBORIU[0]) + abs(lng - CENTRO_MAPA_CAMBORIU[1])
                if dist > 0.005 and (LIMITES_GEO[0] <= lat <= LIMITES_GEO[1] and LIMITES_GEO[2] <= lng <= LIMITES_GEO[3]):
                    return lat, lng
        except Exception:
            pass

    # 5. Fallback Extremo
    return CENTRO_MAPA_CAMBORIU[0], CENTRO_MAPA_CAMBORIU[1]


# ==============================================================================
# 1. TASK CASOS POSITIVOS (COM FUZZY MATCHING E CORREÇÕES)
# ==============================================================================

@shared_task(bind=True)
def task_processar_positivos(self, job_id, arquivo_path, celula_cabecalho=None, mapeamento_customizado=None):
    try:
        log = LogSincronizacao.objects.get(id=job_id)
        log.status = "processando"
        log.mensagem = "Lendo planilha padronizada de casos positivos..."
        log.save()

        engine = 'odf' if arquivo_path.endswith('.ods') else None

        if isinstance(mapeamento_customizado, str):
            try:
                mapeamento_customizado = json.loads(mapeamento_customizado)
            except Exception:
                mapeamento_customizado = None

        h_idx = None
        if celula_cabecalho:
            match = re.search(r'\d+', str(celula_cabecalho))
            if match:
                h_idx = max(0, int(match.group()) - 1)

        if h_idx is None:
            df_temp = pd.read_excel(arquivo_path, header=None, engine=engine)
            h_idx = next((
                i for i, row in df_temp.iterrows()
                if any(k in str(x).upper() for x in row for k in ["SINAN", "RESULTADO", "NOME COMPLETO", "LOCAL NOTIFICAÇÃO", "ENDEREÇO"])
            ), 0)

        df = pd.read_excel(arquivo_path, header=h_idx, engine=engine).dropna(how='all')
        df.columns = [str(c).replace('\n', ' ').strip() for c in df.columns]

        cols = _resolver_colunas_casos(df, mapeamento_customizado)

        c_local   = cols.get('local_atendimento')
        c_notif   = cols.get('notificacao')
        c_inicio  = cols.get('inicio_sintomas')
        c_sinan   = cols.get('sinan')
        c_nome    = cols.get('nome')
        c_nasc    = cols.get('data_nasc')
        c_sexo    = cols.get('sexo')
        c_end     = cols.get('endereco')
        c_bairro  = cols.get('bairro')
        c_res     = cols.get('resultado')
        c_lat     = cols.get('latitude')
        c_lng     = cols.get('longitude')
        c_sit     = cols.get('situacao')
        c_obs     = cols.get('observacoes')

        # Limpa staging local antigo
        CasoPositivoTemp.objects.all().delete()

        params_temp = []
        total_rows = len(df)

        for idx, r in df.iterrows():
            nome_raw = r.get(c_nome) if c_nome and c_nome in df.columns else None
            nome_v = str(nome_raw).strip().upper() if pd.notna(nome_raw) else ""
            if not nome_v or nome_v in ['NAN', 'NULL', 'NONE', 'NAT', '']:
                continue

            end_original = _get_str(r, c_end, 255)
            end_tratado = _corrigir_endereco_fuzzy(end_original) if end_original else None

            bairro_v = _get_str(r, c_bairro, 50)
            if not bairro_v and end_original and ',' in end_original:
                partes = end_original.split(',')
                if len(partes) >= 2:
                    bairro_v = partes[-2].strip()[:50]

            dt_inicio = _parse_data_segura(r.get(c_inicio)) if c_inicio else None
            dt_notif  = _parse_data_segura(r.get(c_notif)) if c_notif else None
            dt_nasc   = _parse_data_segura(r.get(c_nasc)) if c_nasc else None

            val_sinan = r.get(c_sinan) if c_sinan and c_sinan in df.columns else None
            try:
                val_sinan_clean = int(float(val_sinan)) if pd.notna(val_sinan) else None
            except (ValueError, TypeError):
                val_sinan_clean = None

            val_local   = _get_str(r, c_local, 100)
            val_res     = _get_str(r, c_res, 50)
            val_sit     = _get_str(r, c_sit, 50)
            val_obs     = _get_str(r, c_obs, 255)

            dados = (
                val_local.upper() if val_local else None,
                dt_notif,
                dt_inicio,
                val_sinan_clean,
                nome_v,
                dt_nasc,
                _get_str(r, c_sexo, 20),
                end_tratado.upper() if end_tratado else None,
                bairro_v.upper() if bairro_v else None,
                val_res.upper() if val_res else None,
                _get_str(r, c_lat, 50),
                _get_str(r, c_lng, 50),
                val_sit.upper() if val_sit else None,
                val_obs
            )
            params_temp.append(dados)

            if idx % 50 == 0 or idx == total_rows - 1:
                log.progresso = int(((idx + 1) / total_rows) * 100)
                log.save()

        if params_temp:
            with transaction.atomic():
                with connection.cursor() as cursor:
                    sql = """
                        INSERT INTO casos_positivos_temp 
                        (local_atendimento, notificacao, inicio_sintomas, sinan, nome, 
                         data_nasc, sexo, endereco, bairro, resultado, latitude, 
                         longitude, situacao, observacoes)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT DO NOTHING
                    """
                    cursor.executemany(sql, params_temp)

        log.status = "finalizado"
        log.progresso = 100
        log.mensagem = f"Sucesso! {len(params_temp)} casos positivos importados e limpos."
        log.save()

    except Exception as e:
        LogSincronizacao.objects.filter(id=job_id).update(status="erro", mensagem=str(e))
    finally:
        if os.path.exists(arquivo_path):
            try:
                os.remove(arquivo_path)
            except:
                pass


# ==============================================================================
# 2. TASK GEOPROCESSAMENTO 
# ==============================================================================

@shared_task(bind=True)
def task_geoprocessar_pendentes(self, job_id):
    try:
        log = LogSincronizacao.objects.get(id=job_id)
        log.status = "processando"
        log.mensagem = "Iniciando geoprocessamento em cascata dos endereços..."
        log.save()

        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT t.* FROM casos_positivos_temp t
                LEFT JOIN casos_positivos_temp_gl gl ON t.hash_registro = gl.hash_registro
                WHERE gl.hash_registro IS NULL
            """)
            colunas = [col[0] for col in cursor.description]
            registros = [dict(zip(colunas, row)) for row in cursor.fetchall()]

        if not registros:
            log.status = "finalizado"
            log.mensagem = "Nenhum dado pendente encontrado na tabela temporária."
            log.save()
            return

        total = len(registros)
        params_gl = []

        for idx, r in enumerate(registros):
            try:
                lat, lon = None, None

                # 1. Tenta usar as coordenadas diretas se vieram na planilha
                if r.get('latitude') and r.get('longitude'):
                    try:
                        lat = float(str(r.get('latitude')).replace(',', '.'))
                        lon = float(str(r.get('longitude')).replace(',', '.'))
                    except (ValueError, TypeError):
                        lat, lon = None, None

                # 2. Fallback: Geocodificação em cascata caso não existam coordenadas
                if not lat or not lon:
                    lat, lon = _geocodificar_cascata(r.get('endereco'), r.get('bairro'))

                dados = (
                    r.get('local_atendimento'), r.get('notificacao'), r.get('inicio_sintomas'),
                    r.get('sinan'), r.get('nome'), r.get('data_nasc'), r.get('sexo'),
                    r.get('endereco'), r.get('bairro'), r.get('resultado'),
                    r.get('situacao'), r.get('observacoes'),
                    f"POINT({lon} {lat})"
                )
                params_gl.append(dados)
            except Exception:
                continue

            if idx % 10 == 0 or idx == total - 1:
                log.progresso = int(((idx + 1) / total) * 100)
                log.mensagem = f"Processando: {idx + 1} de {total} endereços..."
                log.save()

        if params_gl:
            with transaction.atomic():
                with connection.cursor() as cursor:
                    sql_gl = """
                        INSERT INTO casos_positivos_temp_gl
                        (local_atendimento, notificacao, inicio_sintomas, sinan, nome, 
                         data_nasc, sexo, endereco, bairro, resultado, situacao, 
                         observacoes, geometry)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, ST_GeomFromText(%s, 4674))
                        ON CONFLICT DO NOTHING
                    """
                    cursor.executemany(sql_gl, params_gl)

        log.status = "finalizado"
        log.progresso = 100
        log.mensagem = f"Sucesso! {len(params_gl)} pontos geoprocessados."
        log.save()

    except Exception as e:
        LogSincronizacao.objects.filter(id=job_id).update(status="erro", mensagem=str(e))

# ==============================================================================
# AUXILIAR: CORREÇÃO INTELIGENTE DE ESCALA DE COORDENADAS (FOCOS / ARMADILHAS)
# ==============================================================================
def _separar_rua_e_numero(endereco_bruto):
    """
    Extrai com precisão a rua e o número predial:
    - 'RUA RIO GUAÍRA, 1843-1' -> ('RUA RIO GUAÍRA', '1843-1')
    - 'RUA SANTA MARIA, 11' -> ('RUA SANTA MARIA', '11')
    - 'AV MARGINAL OESTE, 7' -> ('AV MARGINAL OESTE', '7')
    - 'RUA RIO AMAZONAS, 813' -> ('RUA RIO AMAZONAS', '813')
    - 'RUA 1500, S/N' -> ('RUA 1500', 'S/N')
    """
    if pd.isna(endereco_bruto) or not str(endereco_bruto).strip():
        return None, None

    texto = str(endereco_bruto).strip()

    # Caso 1: Separado por vírgula no final (Padrão mais comum: "Nome da Rua, 123")
    if ',' in texto:
        partes = texto.rsplit(',', 1)
        rua_candidata = partes[0].strip()
        sufixo = partes[1].strip()

        # Verifica se o que está após a vírgula é número, complemento numérico ou S/N
        match_num = re.search(r'^(?:N[º°\.]?\s*|NUM[º°\.]?\s*)?(\d+[\w\-\/]*|S/?N|SEM N[UÚ]MERO)\b', sufixo, re.IGNORECASE)
        if match_num:
            return rua_candidata, match_num.group(1).upper()[:10]

    # Caso 2: Padrão sem vírgula ou com S/N no final
    if re.search(r'\b(S/?N|SEM N[UÚ]MERO)\b', texto, re.IGNORECASE):
        rua_limpa = re.sub(r'[,.\-]?\s*\b(S/?N|SEM N[UÚ]MERO)\b', '', texto, flags=re.IGNORECASE).strip(' ,-')
        return (rua_limpa if rua_limpa else texto), 'S/N'

    # Caso 3: Pega os dígitos no final da string (ex: "AV BRASIL 450")
    match_final = re.search(r'^(.*?)(?:\s+n[º°\.]?\s*|\s+)(\d+[\w\-\/]*)$', texto, re.IGNORECASE)
    if match_final:
        return match_final.group(1).strip(' ,-'), match_final.group(2).strip()[:10]

    return texto, None

def _corrigir_coordenadas_escalavel(df, coluna):
    """
    Usa a Mediana da coluna como referência para identificar coordenadas
    que perderam a vírgula (ou ganharam notação científica) e corrige a escala.
    """
    if coluna not in df.columns or df[coluna].isna().all():
        return df[coluna] if coluna in df.columns else pd.Series(index=df.index, dtype=object)

    serie_limpa = df[coluna].astype(str).str.replace(',', '.').apply(pd.to_numeric, errors='coerce')
    limite_global = 90.0 if 'lat' in str(coluna).lower() else 180.0
    
    valores_validos = serie_limpa[(serie_limpa.abs() > 0) & (serie_limpa.abs() <= limite_global)]
    if valores_validos.empty:
        return serie_limpa.fillna(0).astype(str)
        
    referencia = valores_validos.median()

    def ajustar_escala(val):
        if pd.isna(val) or val == 0:
            return None
        # Faltou vírgula (número gigante)
        while abs(val) > limite_global or (abs(referencia) > 0 and abs(val) > abs(referencia) * 5):
            val /= 10.0
        # Sobrou vírgula / zeros (número minúsculo)
        if abs(referencia) > 1:
            while abs(val) > 0 and abs(val) < abs(referencia) / 5:
                val *= 10.0
        return str(round(val, 8))

    return serie_limpa.apply(ajustar_escala)


# ==============================================================================
# 3. TASK FOCOS 
# ==============================================================================

@shared_task(bind=True)
def task_processar_focos(self, job_id, arquivo_path, celula_cabecalho=None, mapeamento_customizado=None):
    try:
        log = LogSincronizacao.objects.get(id=job_id)
        erros = ErrorLogger()

        _, ext = os.path.splitext(arquivo_path)
        ext = ext.lower()
        if ext == '.ods':
            engine = 'odf'
        elif ext == '.xls':
            engine = 'xlrd'
        else:
            engine = 'openpyxl'

        if isinstance(mapeamento_customizado, str):
            try:
                mapeamento_customizado = json.loads(mapeamento_customizado)
            except Exception:
                mapeamento_customizado = None

        df_raw = pd.read_excel(arquivo_path, header=None, nrows=30, engine=engine)

        h_idx = None
        if celula_cabecalho:
            match = re.search(r'\d+', str(celula_cabecalho))
            if match:
                h_idx = max(0, int(match.group()) - 1)

        if h_idx is None:
            TERMOS_RECONHECIDOS = {
                'foco', 'n_foco', 'regional', 'municipio', 'bairro', 'endereco',
                'atividade', 'tipo_atividade', 'coleta', 'data_coleta', 'exame',
                'imovel', 'deposito', 'latitude', 'longitude', 'aquaticas'
            }

            melhor_linha = 0
            max_matches = 0

            for i, row in df_raw.iterrows():
                valores_linha = set(_normalizar_texto(str(v)) for v in row.values if pd.notna(v))
                matches = len(valores_linha.intersection(TERMOS_RECONHECIDOS))

                if matches > max_matches:
                    max_matches = matches
                    melhor_linha = i

            h_idx = melhor_linha if max_matches >= 3 else 0

        df = pd.read_excel(arquivo_path, header=h_idx, engine=engine).dropna(how='all')
        df.columns = [str(c).replace('\n', ' ').strip() for c in df.columns]

        # Mapeamento DE_PARA oficial atualizado para as 16 colunas reais
        DE_PARA_PADRAO = {
            'n_foco': 'Nº FOCO',
            'regional': 'REGIONAL',
            'municipio': 'MUNICÍPIO',
            'localidade': 'BAIRRO',
            'rua_numero': 'ENDEREÇO',
            'complemento': 'COMPLEMENTO',
            'quarteirao': 'QUARTEIRÃO',
            'imovel': 'IMÓVEL',
            'deposito': 'DEPÓSITO',
            'tipo_atividade': 'TIPO DE ATIVIDADE',
            'data_coleta': 'DATA DA COLETA',
            'data_entrada': 'DATA DE ENTRADA',
            'data_exame': 'DATA DO EXAME',
            'a_aegypti_form_aquaticas': 'A. AEGYPTI FORMAS AQUÁTICAS',
            'a_albopictus_form_aquaticas': 'A. ALBOPICTUS FORMAS AQUÁTICAS',
            'latitude': 'LATITUDE',
            'longitude': 'LONGITUDE'
        }

        DE_PARA = {}
        if mapeamento_customizado and isinstance(mapeamento_customizado, dict):
            for k in DE_PARA_PADRAO.keys():
                DE_PARA[k] = mapeamento_customizado.get(k, DE_PARA_PADRAO.get(k))
        else:
            DE_PARA = DE_PARA_PADRAO

        col_lat = DE_PARA.get('latitude')
        col_lng = DE_PARA.get('longitude')

        if col_lat and col_lat in df.columns:
            df[col_lat] = _corrigir_coordenadas_escalavel(df, col_lat)
        if col_lng and col_lng in df.columns:
            df[col_lng] = _corrigir_coordenadas_escalavel(df, col_lng)

        campos_sql = list(DE_PARA_PADRAO.keys())
        registros = []

        for idx, r in df.iterrows():
            lt = r.get(col_lat) if col_lat and col_lat in df.columns else None
            ln = r.get(col_lng) if col_lng and col_lng in df.columns else None

            if pd.isna(lt) or pd.isna(ln) or str(lt).strip() in ['None', 'nan', '0', '']:
                erros.add("geoprocessamento", linha=idx + h_idx + 2, erro="coordenadas ausentes ou invalidas")
                continue

            try:
                lat_f = float(str(lt).replace(',', '.'))
                lon_f = float(str(ln).replace(',', '.'))
            except (ValueError, TypeError):
                continue

            valores = []
            for campo_bd in list(DE_PARA_PADRAO.keys()):
                coluna_planilha = DE_PARA.get(campo_bd)
                if coluna_planilha and coluna_planilha in df.columns:
                    val = r.get(coluna_planilha)

                    if campo_bd in ['data_coleta', 'data_entrada', 'data_exame']:
                        valores.append(_parse_data_segura(val))
                    elif campo_bd in ['a_aegypti_form_aquaticas', 'a_albopictus_form_aquaticas']:
                        val_num = pd.to_numeric(val, errors='coerce')
                        valores.append(0 if pd.isna(val_num) else int(val_num))
                    else:
                        valores.append(None if (pd.isna(val) or str(val).strip().upper() in ['NAN', 'NONE', 'NAT']) else str(val).strip())
                else:
                    if campo_bd in ['a_aegypti_form_aquaticas', 'a_albopictus_form_aquaticas']:
                        valores.append(0)
                    else:
                        valores.append(None)

            registros.append(valores)

        if not registros:
            log.status = "erro"
            log.mensagem = "Nenhum foco válido encontrado. Verifique as colunas de Latitude e Longitude."
            log.save()
            return

        with connection.cursor() as cursor:
            cursor.execute("TRUNCATE TABLE focos_aedes_temp RESTART IDENTITY;")

        placeholders = ["%s"] * len(DE_PARA_PADRAO.keys())
        query = f"""
            INSERT INTO focos_aedes_temp ({", ".join(campos_sql)}) 
            VALUES ({", ".join(placeholders)}) 
            ON CONFLICT DO NOTHING
        """
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.executemany(query, registros)

        log.status = "finalizado"
        log.progresso = 100
        log.mensagem = f"Sucesso! {len(registros)} focos importados."
        log.save()

    except Exception as e:
        LogSincronizacao.objects.filter(id=job_id).update(status="erro", mensagem=str(e))
    finally:
        if os.path.exists(arquivo_path):
            try:
                os.remove(arquivo_path)
            except:
                pass 


# ==============================================================================
# 4. TASK PONTOS ESTRATÉGICOS
# ==============================================================================

@shared_task(bind=True)
def task_processar_pontos(self, job_id, arquivo_path, celula_cabecalho=None, mapeamento_customizado=None):
    try:
        log = LogSincronizacao.objects.get(id=job_id)
        erros = ErrorLogger()

        _, ext = os.path.splitext(arquivo_path)
        ext = ext.lower()
        if ext == '.ods':
            engine = 'odf'
        elif ext == '.xls':
            engine = 'xlrd'
        else:
            engine = 'openpyxl'

        if isinstance(mapeamento_customizado, str):
            try:
                mapeamento_customizado = json.loads(mapeamento_customizado)
            except Exception:
                mapeamento_customizado = None

        df_raw = pd.read_excel(arquivo_path, header=None, nrows=30, engine=engine)

        h_idx = None
        if celula_cabecalho:
            match = re.search(r'\d+', str(celula_cabecalho))
            if match:
                h_idx = max(0, int(match.group()) - 1)

        if h_idx is None:
            TERMOS_RECONHECIDOS = {
                'pe', 'n_pe', 'regional', 'municipio', 'bairro', 'endereco',
                'atividade', 'tipo_atividade', 'coleta', 'exame', 'latitude', 'longitude'
            }

            melhor_linha = 0
            max_matches = 0

            for i, row in df_raw.iterrows():
                valores_linha = set(_normalizar_texto(str(v)) for v in row.values if pd.notna(v))
                matches = len(valores_linha.intersection(TERMOS_RECONHECIDOS))

                if matches > max_matches:
                    max_matches = matches
                    melhor_linha = i

            h_idx = melhor_linha if max_matches >= 3 else 0

        df = pd.read_excel(arquivo_path, header=h_idx, engine=engine).dropna(how='all')
        df.columns = [str(c).replace('\n', ' ').strip() for c in df.columns]

        if not df.empty:
            primeira_coluna = df.columns[0]
            df = df[~df[primeira_coluna].astype(str).str.upper().str.contains("TOTAL", na=False)]

        # Mapeamento DE_PARA padronizado para as 17 colunas
        DE_PARA_PADRAO = {
            'n_pe': 'Nº PE',
            'regional': 'REGIONAL',
            'municipio': 'MUNICÍPIO',
            'localidade': 'BAIRRO',
            'endereco': 'ENDEREÇO',
            'complemento': 'COMPLEMENTO',
            'quarteiroes': 'QUARTEIRÃO',  
            'imovel': 'IMÓVEL',
            'deposito': 'DEPÓSITO',
            'tipo_atividade': 'TIPO DE ATIVIDADE',
            'data_coleta': 'DATA DA COLETA',
            'data_entrada': 'DATA DE ENTRADA',
            'data_exame': 'DATA DO EXAME',
            'a_aegypti_form_aquaticas': 'A. AEGYPTI FORMAS AQUÁTICAS',
            'a_albopictus_form_aquaticas': 'A. ALBOPICTUS FORMAS AQUÁTICAS',
            'latitude': 'LATITUDE',
            'longitude': 'LONGITUDE'
        }

        DE_PARA = {}
        if mapeamento_customizado and isinstance(mapeamento_customizado, dict):
            for campo in DE_PARA_PADRAO.keys():
                DE_PARA[campo] = mapeamento_customizado.get(campo, DE_PARA_PADRAO.get(campo))
        else:
            DE_PARA = DE_PARA_PADRAO

        col_lat = DE_PARA.get('latitude')
        col_lng = DE_PARA.get('longitude')

        if col_lat and col_lat in df.columns:
            df[col_lat] = _corrigir_coordenadas_escalavel(df, col_lat)
        if col_lng and col_lng in df.columns:
            df[col_lng] = _corrigir_coordenadas_escalavel(df, col_lng)

        campos_sql = list(DE_PARA_PADRAO.keys())
        registros = []

        for idx, r in df.iterrows():
            lt = r.get(col_lat) if col_lat and col_lat in df.columns else None
            ln = r.get(col_lng) if col_lng and col_lng in df.columns else None

            if pd.isna(lt) or pd.isna(ln) or str(lt).strip() in ['None', 'nan', '0', '']:
                continue

            try:
                lat_f = float(str(lt).replace(',', '.'))
                lon_f = float(str(ln).replace(',', '.'))
            except (ValueError, TypeError):
                continue

            valores_finais = []
            for campo_bd in list(DE_PARA_PADRAO.keys()):
                coluna_planilha = DE_PARA.get(campo_bd)
                if coluna_planilha and coluna_planilha in df.columns:
                    val = r.get(coluna_planilha)

                    if campo_bd in ['data_coleta', 'data_entrada', 'data_exame']:
                        valores_finais.append(_parse_data_segura(val))
                    elif campo_bd in ['a_aegypti_form_aquaticas', 'a_albopictus_form_aquaticas']:
                        val_num = pd.to_numeric(val, errors='coerce')
                        valores_finais.append(0 if pd.isna(val_num) else int(val_num))
                    else:
                        valores_finais.append(None if (pd.isna(val) or str(val).strip().upper() in ['NAN', 'NONE', 'NAT']) else str(val).strip())
                else:
                    if campo_bd in ['a_aegypti_form_aquaticas', 'a_albopictus_form_aquaticas']:
                        valores_finais.append(0)
                    else:
                        valores_finais.append(None)

            registros.append(valores_finais)

        if not registros:
            log.status = "erro"
            log.mensagem = "Nenhum ponto estratégico válido encontrado. Verifique as colunas de Latitude e Longitude."
            log.save()
            return

        with connection.cursor() as cursor:
            cursor.execute("TRUNCATE TABLE pontos_estrategicos_temp RESTART IDENTITY;")

        placeholders = ["%s"] * len(DE_PARA_PADRAO.keys())
        query = f"""
            INSERT INTO pontos_estrategicos_temp ({", ".join(campos_sql)}) 
            VALUES ({", ".join(placeholders)}) 
            ON CONFLICT DO NOTHING
        """
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.executemany(query, registros)

        log.status = "finalizado"
        log.progresso = 100
        log.mensagem = f"Sucesso! {len(registros)} pontos estratégicos importados."
        log.save()

    except Exception as e:
        LogSincronizacao.objects.filter(id=job_id).update(status="erro", mensagem=str(e))
    finally:
        if os.path.exists(arquivo_path):
            try:
                os.remove(arquivo_path)
            except:
                pass
# ==============================================================================
# 5. TASK ARMADILHAS
# ==============================================================================

@shared_task(bind=True)
def task_processar_armadilhas(self, job_id, arquivo_path, celula_cabecalho=None, mapeamento_customizado=None):
    try:
        log = LogSincronizacao.objects.get(id=job_id)
        erros = ErrorLogger()
        engine = 'odf' if arquivo_path.endswith('.ods') else None

        if isinstance(mapeamento_customizado, str):
            try:
                mapeamento_customizado = json.loads(mapeamento_customizado)
            except Exception:
                mapeamento_customizado = None

        h_idx = None
        if celula_cabecalho:
            match = re.search(r'\d+', str(celula_cabecalho))
            if match:
                h_idx = max(0, int(match.group()) - 1)

        if h_idx is None:
            df_temp = pd.read_excel(arquivo_path, header=None, engine=engine)
            h_idx = next((i for i, row in df_temp.iterrows() if any("Número" in str(x)                                                                                                                                                                                                                                                                                                                                                                                                                                                                  or "Tipo Armadilha" in str(x) for x in row)), 0)

        df = pd.read_excel(arquivo_path, header=h_idx, engine=engine).dropna(how='all')
        colunas_limpas = [str(c).strip() for c in df.columns]
        if "Tipo Imóvel" not in colunas_limpas or "Tipo Armadilha" not in colunas_limpas:
            raise ValueError("Arquivo inválido para Armadilhas.")

        DE_PARA = mapeamento_customizado or {
            'numero': 'Número', 'municipio': 'Município', 'localidade': 'Localidade',
            'endereco': 'Endereço', 'complemento': 'Complemento', 'quarteiroes': 'Quarteiroes',
            'tipo_imovel': 'Tipo Imóvel', 'tipo_armadilha': 'Tipo Armadilha',
            'latitude': 'Latitude', 'longitude': 'Longitude'
        }

        campos_sql = list(DE_PARA.keys())
        registros = []

        for idx, r in df.iterrows():
            col_lat = DE_PARA.get('latitude')
            col_lng = DE_PARA.get('longitude')
            lt = r.get(col_lat) if col_lat else None
            ln = r.get(col_lng) if col_lng else None

            if pd.isna(lt) or pd.isna(ln):
                continue

            linha_registro = []
            for campo_bd in campos_sql:
                coluna_planilha = DE_PARA.get(campo_bd)
                if coluna_planilha and coluna_planilha in df.columns:
                    val = r.get(coluna_planilha)
                    linha_registro.append(None if pd.isna(val) else val)
                else:
                    linha_registro.append(None)

            registros.append(linha_registro)

        if registros:
            query = f"INSERT INTO relat_arm_temp ({', '.join(campos_sql)}) VALUES ({', '.join(['%s']*len(campos_sql))}) ON CONFLICT DO NOTHING"
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.executemany(query, registros)

        log.mensagem, log.status = erros.to_json(), "finalizado"
        log.save()

    except Exception as e:
        LogSincronizacao.objects.filter(id=job_id).update(status="erro", mensagem=str(e))
    finally:
        if os.path.exists(arquivo_path):
            try:
                os.remove(arquivo_path)
            except:
                pass
# ==============================================================================
# 6. TASK OVITRAMPAS
# ==============================================================================
@shared_task(bind=True)
def task_processar_ovitrampas(self, job_id, arquivo_path, celula_cabecalho=None, mapeamento_customizado=None):
    try:
        log = LogSincronizacao.objects.get(id=job_id)
        erros = ErrorLogger()
        engine = 'odf' if arquivo_path.endswith('.ods') else None

        if isinstance(mapeamento_customizado, str):
            try:
                mapeamento_customizado = json.loads(mapeamento_customizado)
            except Exception:
                mapeamento_customizado = None

        h_idx = None
        if celula_cabecalho:
            match = re.search(r'\d+', str(celula_cabecalho))
            if match:
                h_idx = max(0, int(match.group()) - 1)

        if h_idx is None:
            df_temp = pd.read_excel(arquivo_path, header=None, engine=engine)
            h_idx = next((i for i, row in df_temp.iterrows() if any("Ovitrampa" in str(x) or "Nº Armadilha" in str(x) or "Endereço" in str(x) for x in row)), 0)

        df = pd.read_excel(arquivo_path, header=h_idx, engine=engine).dropna(how='all')
        df.columns = [str(c).replace('\n', ' ').strip() for c in df.columns]

        # Mapeamento oficial DE_PARA idêntico à estrutura de Armadilhas
        DE_PARA = mapeamento_customizado or {
            'id_ovitrampa': 'Nº Armadilha',
            'endereco': 'Endereço',
            'numero': 'Número',
            'complemento_tipo': 'Complemento',
            'bairro': 'Bairro',
            'localizacao': 'Localidade',
            'setor_distrito': 'Distrito',
            'responsavel': 'Agente',
            'quarteirao': 'Quarteirão',
            'data_exame': 'Data Instalação',
            'ovos_aegypti': 'A. aegypti',
            'ovos_albopictus': 'A. albopictus',
            'outros_ovos': 'Outros Ovos',
            'tipo': 'Tipo Imóvel',
            'latitude': 'Latitude',
            'longitude': 'Longitude',
            'acoes': 'Observação'
        }

        # Limpa registros antigos do staging
        OvitrampaTemp.objects.all().delete()

        registros = []
        total_rows = len(df)

        for idx, r in df.iterrows():
            col_lat = DE_PARA.get('latitude')
            col_lng = DE_PARA.get('longitude')
            lt = r.get(col_lat) if col_lat and col_lat in df.columns else None
            ln = r.get(col_lng) if col_lng and col_lng in df.columns else None

            # Leitura direta de campos usando o dicionário DE_PARA
            id_ovi = to_str(r.get(DE_PARA.get('id_ovitrampa'))) if DE_PARA.get('id_ovitrampa') in df.columns else ""
            end_bruto = to_str(r.get(DE_PARA.get('endereco'))) if DE_PARA.get('endereco') in df.columns else ""
            num_bruto = to_str(r.get(DE_PARA.get('numero'))) if DE_PARA.get('numero') in df.columns else ""

            # Separação regex caso número venha junto da rua no endereço
            if end_bruto:
                rua_limpa, num_extraido = _separar_rua_e_numero(end_bruto)
                end = rua_limpa or end_bruto
                num = num_bruto or num_extraido or ""
            else:
                end = ""
                num = num_bruto

            comp = to_str(r.get(DE_PARA.get('complemento_tipo'))) if DE_PARA.get('complemento_tipo') in df.columns else ""
            bairro = to_str(r.get(DE_PARA.get('bairro'))) if DE_PARA.get('bairro') in df.columns else ""
            loc = to_str(r.get(DE_PARA.get('localizacao'))) if DE_PARA.get('localizacao') in df.columns else "CAMBORIÚ"
            setor = to_str(r.get(DE_PARA.get('setor_distrito'))) if DE_PARA.get('setor_distrito') in df.columns else ""
            resp = to_str(r.get(DE_PARA.get('responsavel'))) if DE_PARA.get('responsavel') in df.columns else ""
            quart = to_str(r.get(DE_PARA.get('quarteirao'))) if DE_PARA.get('quarteirao') in df.columns else ""

            val_data = r.get(DE_PARA.get('data_exame')) if DE_PARA.get('data_exame') in df.columns else None
            dt_exame = _parse_data_segura(val_data) or to_date(val_data)

            aegypti = to_int(r.get(DE_PARA.get('ovos_aegypti'))) if DE_PARA.get('ovos_aegypti') in df.columns else 0
            albopictus = to_int(r.get(DE_PARA.get('ovos_albopictus'))) if DE_PARA.get('ovos_albopictus') in df.columns else 0
            outros = to_int(r.get(DE_PARA.get('outros_ovos'))) if DE_PARA.get('outros_ovos') in df.columns else 0

            tipo = to_str(r.get(DE_PARA.get('tipo'))) if DE_PARA.get('tipo') in df.columns else ""
            lat_str = to_str(lt) if lt else ""
            lng_str = to_str(ln) if ln else ""
            acoes = to_str(r.get(DE_PARA.get('acoes'))) if DE_PARA.get('acoes') in df.columns else ""

            # Geometria PostGIS
            geom = None
            if lat_str and lng_str:
                try:
                    lat_f = float(lat_str.replace(",", "."))
                    lng_f = float(lng_str.replace(",", "."))
                    geom = Point(lng_f, lat_f, srid=4674)
                except (ValueError, TypeError):
                    geom = None

            if not geom and end:
                lat_c, lon_c = _geocodificar_cascata(f"{end}, {num}", bairro)
                if lat_c and lon_c:
                    geom = Point(lon_c, lat_c, srid=4674)

            h_reg = hash_row(id_ovi, end, num, dt_exame, aegypti, albopictus)

            registros.append(
                OvitrampaTemp(
                    id_ovitrampa=id_ovi,
                    endereco=end,
                    numero=num,
                    complemento_tipo=comp,
                    bairro=bairro,
                    localizacao=loc,
                    setor_distrito=setor,
                    responsavel=resp,
                    quarteirao=quart,
                    data_exame=dt_exame,
                    ovos_aegypti=aegypti or 0,
                    ovos_albopictus=albopictus or 0,
                    outros_ovos=outros or 0,
                    tipo=tipo,
                    latitude=lat_str,
                    longitude=lng_str,
                    acoes=acoes,
                    geometry=geom,
                    hash_registro=h_reg
                )
            )

            if idx % 50 == 0 or idx == total_rows - 1:
                log.progresso = int(((idx + 1) / total_rows) * 100)
                log.save()

        OvitrampaTemp.objects.bulk_create(registros)

        log.status = "finalizado"
        log.progresso = 100
        log.mensagem = f"Upload concluído! {len(registros)} registros de ovitrampas inseridos."
        log.save()

    except Exception as e:
        LogSincronizacao.objects.filter(id=job_id).update(status="erro", mensagem=str(e))
    finally:
        if os.path.exists(arquivo_path):
            try:
                os.remove(arquivo_path)
            except:
                pass