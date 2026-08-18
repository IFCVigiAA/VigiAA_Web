import os
import re
import json
import logging
import unicodedata
import pandas as pd
import geocoder
from celery import shared_task
from django.db import connection, transaction
from django.contrib.gis.geos import Point

from casos.utils.log_errors import ErrorLogger
from .models import (
    LogSincronizacao, PontoEstrategicoTemp, FocoTemp,
    ArmadilhaTemp, CasoPositivoTemp, CasoPositivoTempGL
)

logger = logging.getLogger(__name__)

DEFAULT_STR = "NÃO INFORMADO"


# ==============================================================================
# AUXILIARES DE TRATAMENTO E NORMALIZAÇÃO
# ==============================================================================

def _normalizar_texto(texto):
    """Normaliza texto para cruzamento robusto de cabeçalhos de planilhas."""
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


def _parse_data_segura(val):
    """Converte números seriais do Excel, strings DD/MM/YYYY ou timestamps para objeto date."""
    if val is None or pd.isna(val):
        return None

    # Caso 1: Serial numérico do Excel
    try:
        f = float(val)
        if not pd.isna(f) and f > 1000:
            dt = pd.Timestamp('1899-12-30') + pd.Timedelta(days=int(f))
            if 1900 <= dt.year <= 2100:
                return dt.date()
    except (ValueError, TypeError):
        pass

    # Caso 2: Objeto com método date
    if hasattr(val, 'date'):
        d = val.date()
        if 1900 <= d.year <= 2100:
            return d

    # Caso 3: String
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
    """Lê um campo da linha do DataFrame retornando string limpa."""
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


# Dicionário de Sinônimos para Casos Positivos
ESQUEMA_SINONIMOS_CASOS = {
    'local_atendimento': ['local_atendimento', 'local_notificacao', 'local_de_notificacao', 'local_de_atendimento', 'unidade'],
    'inicio_sintomas': ['inicio_sintomas', 'data_sintomas', 'inicio_dos_sintomas', 'dt_sintomas'],
    'notificacao': ['notificacao', 'data_not', 'data_notificacao', 'dt_notificacao'],
    'sinan': ['sinan', 'n_sinan', 'numero_sinan', 'num_sinan'],
    'nome': ['nome', 'nome_completo', 'paciente', 'nome_do_paciente'],
    'endereco': ['endereco', 'endereco_completo', 'logradouro', 'rua', 'end'],
    'bairro': ['bairro', 'localidade', 'bairros'],
    'nome_mae': ['nome_da_mae', 'nome_mae', 'mae'],
    'data_nasc': ['data_de_nascimento', 'nascimento', 'data_nasc', 'dt_nasc', 'dt_nascimento'],
    'resultado': ['resultado', 'classificacao', 'resultado_final'],
    'aplicacao': ['aplicacao', 'data_aplicacao', 'dt_aplicacao'],
    'agentes': ['agentes', 'agente', 'responsavel', 'agente_visita'],
    'prim_visita': ['1_visita', 'prim_visita', 'primeira_visita', 'visita', 'data_visita', '1a_visita'],
    'situacao': ['situacao', 'status', 'situacao_caso'],
    'observacoes': ['observacoes', 'observacao', 'obs'],
    'recebido': ['recebido', 'data_recebido', 'dt_recebido']
}


def _resolver_colunas_casos(df, mapeamento_customizado=None):
    """Resolve os nomes de colunas usando o mapeamento manual ou os sinônimos de fallback."""
    cols_resolvidas = {}

    # 1. Mapeamento manual do Modal
    if mapeamento_customizado and isinstance(mapeamento_customizado, dict):
        for campo_bd, col_planilha in mapeamento_customizado.items():
            if col_planilha and col_planilha in df.columns:
                cols_resolvidas[campo_bd] = col_planilha
            else:
                cols_resolvidas[campo_bd] = None
        return cols_resolvidas

    # 2. Fallback Inteligente baseado em Sinônimos
    print("⚠️ [CELERY TASK] APLICANDO FALLBACK INTELIGENTE DE SINÔNIMOS", flush=True)
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
# GEOCODIFICAÇÃO
# ==============================================================================

CAMBORIU_BBOX = {
    "lat_min": -27.07,
    "lat_max": -26.97,
    "lon_min": -48.72,
    "lon_max": -48.61,
}

def _dentro_de_camboriu(lat, lon):
    return (
        CAMBORIU_BBOX["lat_min"] <= lat <= CAMBORIU_BBOX["lat_max"] and
        CAMBORIU_BBOX["lon_min"] <= lon <= CAMBORIU_BBOX["lon_max"]
    )

def _geocodificar_endereco(endereco, bairro):
    DEF_LAT, DEF_LON = -27.022986, -48.652135

    if not endereco:
        logger.warning("Geocoder: endereço vazio, usando coordenada default.")
        return DEF_LAT, DEF_LON

    try:
        query = f"{str(endereco).upper()}, {bairro or ''}, SC, BRASIL"
        logger.info(f"Geocodificando: {query}")
        g = geocoder.arcgis(query, timeout=5)

        if g.ok and g.latlng:
            lat, lon = float(g.latlng[0]), float(g.latlng[1])
            if _dentro_de_camboriu(lat, lon):
                logger.info(f"  → OK: lat={lat}, lon={lon}")
                return lat, lon
            else:
                logger.warning(f"  → fora do bbox de Camboriú: lat={lat}, lon={lon} — usando default")
        else:
            logger.warning(f"  → geocoder falhou: status={g.status}")
    except Exception as ex:
        logger.exception(f"Geocoder exception para '{endereco}': {ex}")

    return DEF_LAT, DEF_LON


# ==============================================================================
# 1. TASK CASOS POSITIVOS
# ==============================================================================

@shared_task(bind=True)
def task_processar_positivos(self, job_id, arquivo_path, celula_cabecalho=None, mapeamento_customizado=None):
    try:
        log = LogSincronizacao.objects.get(id=job_id)
        engine = 'odf' if arquivo_path.endswith('.ods') else None

        if isinstance(mapeamento_customizado, str):
            try:
                mapeamento_customizado = json.loads(mapeamento_customizado)
            except Exception:
                mapeamento_customizado = None

        print("\n" + "="*60, flush=True)
        print(">>> [CELERY TASK] MAPEAMENTO RECEBIDO:", mapeamento_customizado, flush=True)
        print("="*60 + "\n", flush=True)

        # 1. Localização Inteligente do Cabeçalho
        h_idx = None
        if celula_cabecalho:
            match = re.search(r'\d+', str(celula_cabecalho))
            if match:
                h_idx = max(0, int(match.group()) - 1)

        if h_idx is None:
            df_temp = pd.read_excel(arquivo_path, header=None, engine=engine)
            h_idx = next((
                i for i, row in df_temp.iterrows() 
                if any(k in str(x).upper() for x in row for k in ["SINAN", "RESULTADO", "NOME", "PACIENTE", "ENDEREÇO", "BAIRRO"])
            ), 0)

        # 2. Carrega a planilha e LIMPA espaços de todas as colunas
        df = pd.read_excel(arquivo_path, header=h_idx, engine=engine).dropna(how='all')
        df.columns = [str(c).replace('\n', ' ').strip() for c in df.columns]

        print(f">>> [CELERY TASK] Linha do cabeçalho: {h_idx} | Total de linhas: {len(df)}", flush=True)
        print(">>> [CELERY TASK] Colunas encontradas no Excel:", list(df.columns), flush=True)

        # 3. Resolução das Colunas
        cols = _resolver_colunas_casos(df, mapeamento_customizado)
        print(">>> [CELERY TASK] Colunas resolvidas para inserção:", cols, flush=True)

        c_local   = cols.get('local_atendimento')
        c_inicio  = cols.get('inicio_sintomas')
        c_notif   = cols.get('notificacao')
        c_sinan   = cols.get('sinan')
        c_nome    = cols.get('nome')
        c_end     = cols.get('endereco')
        c_bairro  = cols.get('bairro')
        c_mae     = cols.get('nome_mae')
        c_nasc    = cols.get('data_nasc')
        c_res     = cols.get('resultado')
        c_aplic   = cols.get('aplicacao')
        c_agentes = cols.get('agentes')
        c_visita  = cols.get('prim_visita')
        c_sit     = cols.get('situacao')
        c_obs     = cols.get('observacoes')
        c_rec     = cols.get('recebido')

        # 4. Extração e Sanitização das Linhas
        params_temp = []
        for idx, r in df.iterrows():
            # Extrai o nome mesmo que a coluna venha com formatação diferente
            nome_raw = r.get(c_nome) if c_nome and c_nome in df.columns else None
            nome_v = str(nome_raw).strip().upper() if pd.notna(nome_raw) else ""
            
            # Pula apenas se o nome for totalmente nulo ou texto 'NAN'/'NULL'
            if not nome_v or nome_v in ['NAN', 'NULL', 'NONE', 'NAT', '']:
                continue

            dt_inicio = _parse_data_segura(r.get(c_inicio)) if c_inicio and c_inicio in df.columns else None
            dt_notif  = _parse_data_segura(r.get(c_notif)) if c_notif and c_notif in df.columns else None
            dt_nasc   = _parse_data_segura(r.get(c_nasc)) if c_nasc and c_nasc in df.columns else None
            dt_aplic  = _parse_data_segura(r.get(c_aplic)) if c_aplic and c_aplic in df.columns else None
            dt_visita = _parse_data_segura(r.get(c_visita)) if c_visita and c_visita in df.columns else None
            dt_rec    = _parse_data_segura(r.get(c_rec)) if c_rec and c_rec in df.columns else None

            val_sinan = r.get(c_sinan) if c_sinan and c_sinan in df.columns else None
            try:
                val_sinan_clean = int(float(val_sinan)) if pd.notna(val_sinan) else None
            except (ValueError, TypeError):
                val_sinan_clean = None

            val_local   = _get_str(r, c_local, 100)
            val_end     = _get_str(r, c_end, 255)
            val_bairro  = _get_str(r, c_bairro, 50)
            val_mae     = _get_str(r, c_mae, 100)
            val_res     = _get_str(r, c_res, 50)
            val_agentes = _get_str(r, c_agentes, 150)
            val_sit     = _get_str(r, c_sit, 50)
            val_obs     = _get_str(r, c_obs, 255)

            dados = (
                val_local.upper() if val_local else None,
                dt_inicio,
                dt_notif,
                val_sinan_clean,
                nome_v,
                val_end.upper() if val_end else None,
                val_bairro.upper() if val_bairro else None,
                val_mae.upper() if val_mae else None,
                dt_nasc,
                val_obs,
                val_res.upper() if val_res else None,
                dt_aplic,
                val_agentes.upper() if val_agentes else None,
                dt_visita,
                val_sit.upper() if val_sit else None,
                dt_rec
            )
            params_temp.append(dados)

        print(f">>> [CELERY TASK] Linhas válidas para inserção: {len(params_temp)}", flush=True)

        if params_temp:
            with transaction.atomic():
                with connection.cursor() as cursor:
                    sql = """
                        INSERT INTO casos_positivos_temp 
                        (local_atendimento, inicio_sintomas, notificacao, sinan, nome, 
                         endereco, bairro, nome_mae, data_nasc, observacoes, resultado, 
                         aplicacao, agentes, prim_visita, situacao, observacao2)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT DO NOTHING
                    """
                    cursor.executemany(sql, params_temp)

        log.status = "finalizado"
        log.progresso = 100
        log.mensagem = f"Sucesso! {len(params_temp)} casos positivos importados."
        log.save()

    except Exception as e:
        print(f"❌ [CELERY TASK] ERRO: {e}", flush=True)
        LogSincronizacao.objects.filter(id=job_id).update(status="erro", mensagem=str(e))
    finally:
        if os.path.exists(arquivo_path):
            try:
                os.remove(arquivo_path)
            except:
                pass


# ==============================================================================
# 2. TASK GEOPROCESSAMENTO DE CASOS PENDENTES
# ==============================================================================

@shared_task(bind=True)
def task_geoprocessar_pendentes(self, job_id):
    try:
        log = LogSincronizacao.objects.get(id=job_id)
        log.mensagem = "Iniciando consulta ao serviço de Geocodificação..."
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
            log.status = "erro"
            log.mensagem = "Nenhum dado pendente encontrado na tabela temporária. Faça o upload da planilha antes de gerar o mapa."
            log.save()
            return

        total = len(registros)
        params_gl = []

        for idx, r in enumerate(registros):
            try:
                lat, lon = _geocodificar_endereco(r.get('endereco'), r.get('bairro'))
                dados = (
                    r.get('local_atendimento'), r.get('inicio_sintomas'), r.get('notificacao'),
                    r.get('sinan'), r.get('nome'), r.get('endereco'), r.get('bairro'),
                    r.get('nome_mae'), r.get('data_nasc'), r.get('observacoes'),
                    r.get('resultado'), r.get('aplicacao'), r.get('agentes'),
                    r.get('prim_visita'), r.get('situacao'), r.get('observacao2'),
                    f"POINT({lon} {lat})"
                )
                params_gl.append(dados)
            except Exception:
                continue

            if idx % 10 == 0 or idx == total - 1:
                log.progresso = int((idx / total) * 100)
                log.mensagem = f"Processando: {idx + 1} de {total} endereços..."
                log.save()

        if params_gl:
            with transaction.atomic():
                with connection.cursor() as cursor:
                    sql_gl = """
                        INSERT INTO casos_positivos_temp_gl
                        (local_atendimento, inicio_sintomas, notificacao, sinan, nome, 
                         endereco, bairro, nome_mae, data_nasc, observacoes, resultado, 
                         aplicacao, agentes, prim_visita, situacao, observacao2, geometry)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, ST_GeomFromText(%s, 4674))
                        ON CONFLICT DO NOTHING
                    """
                    cursor.executemany(sql_gl, params_gl)

        log.status = "finalizado"
        log.progresso = 100
        log.mensagem = f"Sucesso! {len(params_gl)} pontos gerados no mapa."
        log.save()

    except Exception as e:
        LogSincronizacao.objects.filter(id=job_id).update(status="erro", mensagem=str(e))


# ==============================================================================
# 3. TASK FOCOS
# ==============================================================================

@shared_task(bind=True)
def task_processar_focos(self, job_id, arquivo_path, celula_cabecalho=None, mapeamento_customizado=None):
    try:
        log = LogSincronizacao.objects.get(id=job_id)
        erros = ErrorLogger()
        engine = 'odf' if arquivo_path.endswith('.ods') else None

        if isinstance(mapeamento_customizado, str):
            try:
                mapeamento_customizado = json.loads(mapeamento_customizado)
            except Exception:
                mapeamento_customizado = None

        df_raw = pd.read_excel(arquivo_path, header=None, engine=engine)

        conteudo_total_texto = " ".join([str(x) for x in df_raw.values.flatten() if pd.notna(x)]).upper()
        if "AEGYPTI" not in conteudo_total_texto:
            raise ValueError("Arquivo inválido! O arquivo enviado não possui as colunas estruturais de Focos.")

        h_idx = None
        if celula_cabecalho:
            match = re.search(r'\d+', str(celula_cabecalho))
            if match:
                h_idx = max(0, int(match.group()) - 1)

        if h_idx is None:
            h_idx = next((i for i, row in df_raw.iterrows() if any("N FOCO" in _normalize_legado(str(x)) for x in row)), 2)

        df = pd.read_excel(arquivo_path, header=h_idx, engine=engine).dropna(how='all')

        DE_PARA = mapeamento_customizado or {
            'n_foco': 'Nº Foco', 'regional': 'Regional', 'municipio': 'Município',
            'localidade': 'Localidade', 'rua_numero': 'Rua/número', 'complemento': 'Complemento',
            'quarteirao': 'Quarteirão', 'imovel': 'Imóvel', 'deposito': 'Depósito',
            'tipo_atividade': 'Tipo de Atividade', 'data_coleta': 'Data da Coleta',
            'data_entrada': 'Data de Entrada', 'data_exame': 'Data do Exame',
            'a_aegypti_form_aquaticas': 'A. aegypti formas aquáticas',
            'a_aegypti_form_adultas': 'A. aegypti formas adultas',
            'a_albopictus_form_aquaticas': 'A. albopictus formas aquáticas',
            'a_albopictus_form_adultas': 'A. albopictus formas adultas',
            'ovo_a_aegypti': 'Ovo A. aegypti', 'latitude': 'Latitude', 'longitude': 'Longitude'
        }

        campos_sql = list(DE_PARA.keys())
        registros = []

        for idx, r in df.iterrows():
            col_lat = DE_PARA.get('latitude')
            col_lng = DE_PARA.get('longitude')

            lt = r.get(col_lat) if col_lat else None
            ln = r.get(col_lng) if col_lng else None

            if pd.isna(lt) or pd.isna(ln):
                erros.add("geoprocessamento", linha=idx + h_idx + 2, erro="coordenadas ausentes")
                continue

            valores = []
            for campo_bd in campos_sql:
                coluna_planilha = DE_PARA.get(campo_bd)
                if coluna_planilha and coluna_planilha in df.columns:
                    val = r.get(coluna_planilha)

                    if campo_bd in ['data_coleta', 'data_entrada', 'data_exame']:
                        valores.append(_parse_data_segura(val))
                    elif campo_bd in ['a_aegypti_form_aquaticas', 'a_aegypti_form_adultas', 'a_albopictus_form_aquaticas', 'a_albopictus_form_adultas', 'ovo_a_aegypti']:
                        val_num = pd.to_numeric(val, errors='coerce')
                        valores.append(0 if pd.isna(val_num) else int(val_num))
                    else:
                        valores.append(None if pd.isna(val) else val)
                else:
                    valores.append(None)

            registros.append(valores)

        if registros:
            query = f"""
                INSERT INTO focos_aedes_temp ({", ".join(campos_sql)}) 
                VALUES ({", ".join(["%s"] * len(campos_sql))}) 
                ON CONFLICT DO NOTHING
            """
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
# 4. TASK PONTOS ESTRATÉGICOS
# ==============================================================================

@shared_task(bind=True)
def task_processar_pontos(self, job_id, arquivo_path, celula_cabecalho=None, mapeamento_customizado=None):
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
            h_idx = next((i for i, row in df_temp.iterrows() if any("Número" in str(x) or "Município" in str(x) for x in row)), 0)

        df = pd.read_excel(arquivo_path, header=h_idx, engine=engine).dropna(how='all')

        if not df.empty:
            primeira_coluna = df.columns[0]
            df = df[~df[primeira_coluna].astype(str).str.upper().str.contains("TOTAL", na=False)]

        colunas_limpas = [str(c).strip() for c in df.columns]
        if "Tipo Imóvel" in colunas_limpas or "Tipo Armadilha" in colunas_limpas:
            raise ValueError("Arquivo inválido! O arquivo enviado não possui as colunas estruturais de Pontos Estratégicos.")

        DE_PARA = mapeamento_customizado or {
            'numero': 'Número', 'municipio': 'Município', 'localidade': 'Localidade',
            'endereco': 'Endereço', 'quarteiroes': 'Quarteiroes', 'complemento': 'Complemento',
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

        if not registros:
            log.status = "erro"
            log.mensagem = "Nenhum registro válido encontrado. Verifique as colunas de Latitude e Longitude."
            log.save()
            return

        query = f"INSERT INTO pontos_estrategicos_temp ({', '.join(campos_sql)}) VALUES ({', '.join(['%s']*len(campos_sql))}) ON CONFLICT DO NOTHING"
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
            h_idx = next((i for i, row in df_temp.iterrows() if any("Número" in str(x) or "Tipo Armadilha" in str(x) for x in row)), 0)

        df = pd.read_excel(arquivo_path, header=h_idx, engine=engine).dropna(how='all')

        colunas_limpas = [str(c).strip() for c in df.columns]
        if "Tipo Imóvel" not in colunas_limpas or "Tipo Armadilha" not in colunas_limpas:
            raise ValueError("Arquivo inválido! O arquivo enviado não possui as colunas estruturais de Armadilhas.")

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