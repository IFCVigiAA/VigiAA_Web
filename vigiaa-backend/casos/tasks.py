import os
import logging
import pandas as pd
import geocoder
import hashlib
import unicodedata
from celery import shared_task
from django.db import connection, transaction
from django.contrib.gis.geos import Point
import json
from casos.utils.log_errors import ErrorLogger

from .models import (
    LogSincronizacao, PontoEstrategicoTemp, FocoTemp,
    ArmadilhaTemp, CasoPositivoTemp, CasoPositivoTempGL
)

logger = logging.getLogger(__name__)

# AUXILIARES DE TRATAMENTO

DEFAULT_STR = "NÃO INFORMADO"

def add_erro(erros, tipo, linha, coluna=None, valor=None, erro=None, detalhe=None):
    erros.append({
        "tipo": tipo,
        "linha": linha,
        "coluna": coluna,
        "valor": str(valor)[:100] if valor is not None else None,
        "erro": erro,
        "detalhe": detalhe
    })

def corrigir_datas_mistas(serie):
    numeros_excel = pd.to_numeric(serie, errors='coerce')
    datas_dos_numeros = pd.to_datetime(numeros_excel, unit='D', origin='1899-12-30')
    textos_puros = serie.where(numeros_excel.isna(), pd.NaT)
    datas_dos_textos = pd.to_datetime(textos_puros, errors='coerce', dayfirst=True)
    return datas_dos_textos.fillna(datas_dos_numeros)

def _normalize(s):
    if not s: return ""
    s = str(s).strip().upper()
    s = unicodedata.normalize("NFKD", s).encode("ASCII", "ignore").decode("ASCII")
    return " ".join(s.replace("\xa0", " ").split())

def col(df, *nomes):
    cols_mapeadas = {_normalize(c): c for c in df.columns}
    for n in nomes:
        key = _normalize(n)
        if key in cols_mapeadas: return cols_mapeadas[key]
    return None

def _get_str(r, col_name, maxlen=None, default=DEFAULT_STR):
    """Lê um campo do row, retorna string tratada. Usa default se vazio/nulo."""
    if col_name is None:
        return default
    val = r.get(col_name)
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return default
    result = str(val).strip()
    if not result or result.upper() == 'NAN':
        return default
    if maxlen:
        result = result[:maxlen]
    return result

def _formatar_data_visita(val):
    """
    Converte o valor de prim_visita para string de data limpa (DD/MM/YYYY).
    Aceita: número serial do Excel (ex: 45995), datetime, string com ou sem hora.
    Retorna None se não conseguir converter.
    """
    if val is None:
        return None

    try:
        f = float(val)
        if not pd.isna(f) and f > 1000:
            dt = pd.Timestamp('1899-12-30') + pd.Timedelta(days=int(f))
            return dt.strftime('%d/%m/%Y')
    except (ValueError, TypeError):
        pass
    try:
        ts = pd.Timestamp(val)
        if pd.notna(ts):
            return ts.strftime('%d/%m/%Y')
    except Exception:
        pass
    s = str(val).strip()
    if s.endswith(' 00:00:00'):
        s = s[:-9]
    return s if s and s.upper() != 'NAN' else None

def _get_date_str(r, col_name, maxlen=50):
    """
    Lê um campo que pode ser data, datetime, número serial Excel ou string de data,
    e retorna sempre uma string 'YYYY-MM-DD' (ou None se vazio/inválido).
    Usado para colunas VARCHAR que guardam datas (ex: prim_visita).
    """
    if col_name is None:
        return None
    val = r.get(col_name)
    if val is None:
        return None

    try:
        num = float(val)
        if pd.isna(num):
            return None
        if num > 1000:
            try:
                dt = pd.Timestamp('1899-12-30') + pd.Timedelta(days=int(num))
                return str(dt.date())[:maxlen]
            except:
                pass
    except (ValueError, TypeError):
        pass

    try:
        if hasattr(val, 'date'):
            return str(val.date())[:maxlen]
    except:
        pass

    s = str(val).strip()
    if not s or s.upper() == 'NAN':
        return None
    try:
        return str(pd.to_datetime(s, dayfirst=True).date())[:maxlen]
    except:
        pass

    return s[:maxlen]

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
                logger.warning(
                    f"  → fora do bbox de Camboriú: lat={lat}, lon={lon} — usando default"
                )
        else:
            logger.warning(
                f"  → geocoder falhou: status={g.status}, error={getattr(g, 'error', 'desconhecido')}"
            )

    except Exception as ex:
        logger.exception(f"Geocoder exception para '{endereco}': {ex}")

    return DEF_LAT, DEF_LON

# --- 2. TASK POSITIVOS ---

@shared_task(bind=True)
def task_processar_positivos(self, job_id, arquivo_path):
    """
    TASK 1: UPLOAD RÁPIDO
    Apenas lê a planilha e insere na tabela 'casos_positivos_temp'.
    NÃO faz geoprocessamento.
    """
    try:
        log = LogSincronizacao.objects.get(id=job_id)
        
        # 1. Leitura dos dados
        df_bruto = pd.read_excel(arquivo_path)
        df = df_bruto.dropna(how='all')

        # --- VALIDAÇÃO DE SEGURANÇA ---
        colunas_limpas = [str(c).strip().upper() for c in df.columns]
        if "SINAN" not in colunas_limpas or "RESULTADO" not in colunas_limpas:
            raise ValueError("Arquivo inválido! O arquivo enviado não possui as colunas estruturais de Casos Positivos.")

        # 2. Mapeamento de colunas
        c_nome    = col(df, "NOME")
        c_end     = col(df, "ENDEREÇO", "ENDERECO")
        c_sinan   = col(df, "SINAN")
        c_inicio  = col(df, "INÍCIO SINTOMAS", "INICIO SINTOMAS")
        c_notif   = col(df, "NOTIFICAÇÃO", "NOTIFICACAO")
        c_nasc    = col(df, "DATA DE NASCIMENTO")
        c_bairro  = col(df, "BAIRRO")
        c_local   = col(df, "LOCAL DE ATENDIMENTO")
        c_mae     = col(df, "NOME DA MÃE", "NOME DA MAE")
        c_obs     = col(df, "OBSERVAÇÕES", "OBSERVACOES")
        c_res     = col(df, "RESULTADO")
        c_aplic   = col(df, "APLICAÇÃO", "APLICACAO")
        c_agentes = col(df, "AGENTE(S)", "AGENTES")
        c_prim    = col(df, "1ª VISITA", "1A VISITA")
        c_sit     = col(df, "SITUAÇÃO", "SITUACAO")
        c_obs2    = col(df, "UNNAMED: 15", "OBSERVACAO2")

        # 3. Tratamento de datas
        for c in [c_inicio, c_nasc, c_notif]:
            if c:
                df[c] = corrigir_datas_mistas(df[c])

        params_temp = []
        for idx, r in df.iterrows():
            nome_v = _get_str(r, c_nome, 100).upper()
            if not nome_v or nome_v == 'NAN':
                continue

            # Montando a tupla para a tabela temp (DADOS PUROS)
            dados = (
                _get_str(r, c_local, 100).upper(),
                r.get(c_inicio).date() if pd.notna(r.get(c_inicio)) else None,
                r.get(c_notif).date() if pd.notna(r.get(c_notif)) else None,
                int(float(r.get(c_sinan))) if pd.notna(r.get(c_sinan)) else None,
                nome_v,
                _get_str(r, c_end, 255).upper(),
                _get_str(r, c_bairro, 50).upper(),
                _get_str(r, c_mae, 100).upper(),
                r.get(c_nasc).date() if pd.notna(r.get(c_nasc)) else None,
                _get_str(r, c_obs, 255),
                _get_str(r, c_res, 50).upper(),
                _get_str(r, c_aplic, 50),
                _get_str(r, c_agentes, 100),
                _formatar_data_visita(r.get(c_prim)),
                _get_str(r, c_sit, 255),
                _get_str(r, c_obs2, 255)
            )
            params_temp.append(dados)

        # 4. Inserção em lote no banco
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
        log.save()

    except Exception as e:
        LogSincronizacao.objects.filter(id=job_id).update(status="erro", mensagem=str(e))
    finally:
        if os.path.exists(arquivo_path):
            try: os.remove(arquivo_path)
            except: pass

@shared_task(bind=True)
def task_geoprocessar_pendentes(self, job_id):
    """
    TASK 2: GEOPROCESSAMENTO (Botão Gerar Mapa)
    Lê os dados que já estão na 'casos_positivos_temp', 
    consulta o ArcGIS e insere na 'casos_positivos_temp_gl'.
    """
    try:
        log = LogSincronizacao.objects.get(id=job_id)
        log.mensagem = "Iniciando consulta ao ArcGIS..."
        log.save()
        
        with connection.cursor() as cursor:
            # Seleciona todos da temp para geoprocessar
            cursor.execute("""
                SELECT t.* FROM casos_positivos_temp t
                LEFT JOIN casos_positivos_temp_gl gl ON t.hash_registro = gl.hash_registro
                WHERE gl.hash_registro IS NULL
            """)
            colunas = [col[0] for col in cursor.description]
            registros = [dict(zip(colunas, row)) for row in cursor.fetchall()]

        if not registros:
            log.status = "finalizado"
            log.mensagem = "Nenhum dado na tabela temporária para geoprocessar."
            log.save()
            return

        total = len(registros)
        params_gl = []
        
        for idx, r in enumerate(registros):
            try:
                # CONSULTA REAL AO ARCGIS
                lat, lon = _geocodificar_endereco(r['endereco'], r['bairro'])
                
                # Monta os dados com a GEOMETRY para a tabela _gl
                dados = (
                    r['local_atendimento'], r['inicio_sintomas'], r['notificacao'],
                    r['sinan'], r['nome'], r['endereco'], r['bairro'],
                    r['nome_mae'], r['data_nasc'], r['observacoes'],
                    r['resultado'], r['aplicacao'], r['agentes'],
                    r['prim_visita'], r['situacao'], r['observacao2'],
                    f"POINT({lon} {lat})" # Geometria WKT
                )
                params_gl.append(dados)
            except:
                continue # Se um falhar, continua para o próximo
            
            # Atualiza progresso no log para o frontend mostrar
            if idx % 10 == 0 or idx == total - 1:
                log.progresso = int((idx / total) * 100)
                log.mensagem = f"Processando: {idx + 1} de {total} endereços..."
                log.save()

        # Inserção na tabela oficial de geoprocessamento (_gl)
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

# --- 3. TASK FOCOS ---
# Planilha: 2-3 linhas de título, depois cabeçalho com "Nº Foco", depois dados.
# A lógica lê sem cabeçalho, encontra a linha do cabeçalho pelo texto "N FOCO",
# e relê o arquivo usando essa linha como header=.

@shared_task(bind=True)
def task_processar_focos(self, job_id, arquivo_path):
    try:
        log = LogSincronizacao.objects.get(id=job_id)
        erros = ErrorLogger()

        df_raw = pd.read_excel(arquivo_path, header=None)
        
        # --- VALIDAÇÃO DE SEGURANÇA ---
        conteudo_total_texto = " ".join(df_raw.astype(str).values.flatten()).upper()
        if "N FOCO" not in _normalize(conteudo_total_texto) or "TIPO DE ATIVIDADE" not in conteudo_total_texto:
            raise ValueError("Arquivo inválido! O arquivo enviado não possui as colunas estruturais de Focos.")

        h_idx = next((i for i, row in df_raw.iterrows() if any("N FOCO" in _normalize(str(x)) for x in row)), 2)
        
        df = pd.read_excel(arquivo_path, header=h_idx).dropna(how='all')

        DE_PARA = {
            'Nº Foco': 'n_foco', 'Regional': 'regional', 'Município': 'municipio',
            'Localidade': 'localidade', 'Rua/número': 'rua_numero', 'Complemento': 'complemento',
            'Quarteirão': 'quarteirao', 'Imóvel': 'imovel', 'Depósito': 'deposito',
            'Tipo de Atividade': 'tipo_atividade', 'Data da Coleta': 'data_coleta',
            'Data de Entrada': 'data_entrada', 'Data do Exame': 'data_exame',
            'A. aegypti formas aquáticas': 'a_aegypti_form_aquaticas',
            'A. aegypti formas adultas': 'a_aegypti_form_adultas',
            'A. albopictus formas aquáticas': 'a_albopictus_form_aquaticas',
            'A. albopictus formas adultas': 'a_albopictus_form_adultas',
            'Ovo A. aegypti': 'ovo_a_aegypti', 'Latitude': 'latitude', 'Longitude': 'longitude'
        }
        
        df.columns = [str(c).strip() for c in df.columns]
        mapa_final = {col(df, k): v for k, v in DE_PARA.items() if col(df, k)}
        df.rename(columns=mapa_final, inplace=True)

        # Tratamento
        for c in ['data_coleta', 'data_entrada', 'data_exame']:
            if c in df.columns: df[c] = pd.to_datetime(df[c], dayfirst=True, errors='coerce').dt.date

        cols_int = ['a_aegypti_form_aquaticas', 'a_aegypti_form_adultas', 'a_albopictus_form_aquaticas', 'a_albopictus_form_adultas', 'ovo_a_aegypti']
        for c in cols_int:
            if c in df.columns: df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0).astype(int)

        registros = []
        campos_sql = [c for c in DE_PARA.values()] # Apenas colunas da planilha

        for idx, r in df.iterrows():
            lt, ln = r.get('latitude'), r.get('longitude')
            if pd.isna(lt) or pd.isna(ln):
                erros.add("geoprocessamento", linha=idx + h_idx + 2, erro="coordenadas ausentes")
                continue
            
            # Monta lista de valores na ordem dos campos_sql
            valores = []
            for campo in campos_sql:
                val = r.get(campo)
                valores.append(None if pd.isna(val) else val)
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
        if os.path.exists(arquivo_path): os.remove(arquivo_path)

# --- 4. TASK PONTOS ESTRATÉGICOS ---
# Planilha: título L1, "Município: X" L2, cabeçalho L4 → header=3
# Colunas: Número, Município, Localidade, Endereço, Quarteiroes, Complemento, Latitude, Longitude

@shared_task(bind=True)
def task_processar_pontos(self, job_id, arquivo_path):
    try:
        log = LogSincronizacao.objects.get(id=job_id)
        erros = ErrorLogger()
        df_temp = pd.read_excel(arquivo_path, header=None)
        h_idx = next((i for i, row in df_temp.iterrows() if any("Número" in str(x) for x in row)), 0)
        df = pd.read_excel(arquivo_path, header=h_idx).dropna(how='all')

        # --- VALIDAÇÃO DE SEGURANÇA ---
        colunas_limpas = [str(c).strip() for c in df.columns]
        # Se contiver colunas de armadilhas, bloqueia o processamento de pontos
        if "Tipo Imóvel" in colunas_limpas or "Tipo Armadilha" in colunas_limpas:
            raise ValueError("Arquivo inválido! O arquivo enviado não possui as colunas estruturais de Pontos Estratégicos.")

        DE_PARA = {
            'Número': 'numero', 'Município': 'municipio', 'Localidade': 'localidade',
            'Endereço': 'endereco', 'Quarteiroes': 'quarteiroes', 'Complemento': 'complemento',
            'Latitude': 'latitude', 'Longitude': 'longitude'
        }
        df.columns = [str(c).strip() for c in df.columns]
        mapa_final = {col(df, k): v for k, v in DE_PARA.items() if col(df, k)}
        df.rename(columns=mapa_final, inplace=True)

        campos_sql = list(DE_PARA.values())
        registros = []
        for idx, r in df.iterrows():
            lt, ln = r.get('latitude'), r.get('longitude')
            if pd.isna(lt) or pd.isna(ln): continue
            
            registros.append([None if pd.isna(r.get(c)) else r.get(c) for c in campos_sql])

        if registros:
            query = f"INSERT INTO pontos_estrategicos_temp ({', '.join(campos_sql)}) VALUES ({', '.join(['%s']*len(campos_sql))}) ON CONFLICT DO NOTHING"
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.executemany(query, registros)

        log.mensagem, log.status = erros.to_json(), "finalizado"
        log.save()
    except Exception as e:
        LogSincronizacao.objects.filter(id=job_id).update(status="erro", mensagem=str(e))
    finally:
        if os.path.exists(arquivo_path): os.remove(arquivo_path)


@shared_task(bind=True)
def task_processar_armadilhas(self, job_id, arquivo_path):
    try:
        log = LogSincronizacao.objects.get(id=job_id)
        erros = ErrorLogger()
        df_temp = pd.read_excel(arquivo_path, header=None)
        h_idx = next((i for i, row in df_temp.iterrows() if any("Número" in str(x) for x in row)), 0)
        df = pd.read_excel(arquivo_path, header=h_idx).dropna(how='all')

        # --- VALIDAÇÃO DE SEGURANÇA ---
        colunas_limpas = [str(c).strip() for c in df.columns]
        if "Tipo Imóvel" not in colunas_limpas or "Tipo Armadilha" not in colunas_limpas:
            raise ValueError("Arquivo inválido! O arquivo enviado não possui as colunas estruturais de Armadilhas.")

        DE_PARA = {
            'Número': 'numero', 'Município': 'municipio', 'Localidade': 'localidade',
            'Endereço': 'endereco', 'Complemento': 'complemento', 'Quarteiroes': 'quarteiroes',
            'Tipo Imóvel': 'tipo_imovel', 'Tipo Armadilha': 'tipo_armadilha',
            'Latitude': 'latitude', 'Longitude': 'longitude'
        }
        df.columns = [str(c).strip() for c in df.columns]
        mapa_final = {col(df, k): v for k, v in DE_PARA.items() if col(df, k)}
        df.rename(columns=mapa_final, inplace=True)

        campos_sql = list(DE_PARA.values())
        registros = []
        for idx, r in df.iterrows():
            lt, ln = r.get('latitude'), r.get('longitude')
            if pd.isna(lt) or pd.isna(ln): continue
            registros.append([None if pd.isna(r.get(c)) else r.get(c) for c in campos_sql])

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
        if os.path.exists(arquivo_path): os.remove(arquivo_path)