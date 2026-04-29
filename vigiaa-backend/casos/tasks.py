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
    def add_erro(erros, tipo, linha, coluna=None, valor=None, erro=None, detalhe=None):
        erros.append({
            "tipo": tipo,
            "linha": linha,
            "coluna": coluna,
            "valor": str(valor)[:100] if valor is not None else None,
            "erro": erro,
            "detalhe": detalhe
        })

    try:
        log = LogSincronizacao.objects.get(id=job_id)
        erros_log = {"planilha": [], "geoprocessamento": []}

        df_bruto = pd.read_excel(arquivo_path)
        df = df_bruto.dropna(how='all')
        linhas_vazias = len(df_bruto) - len(df)
        if linhas_vazias > 0:
            add_erro(erros_log["planilha"], "estrutura", "N/A", erro=f"{linhas_vazias} linhas em branco ignoradas")

        c_inicio  = col(df, "INÍCIO SINTOMAS", "INICIO SINTOMAS")
        c_nome    = col(df, "NOME")
        c_sinan   = col(df, "SINAN")
        c_end     = col(df, "ENDEREÇO", "ENDERECO")
        c_nasc    = col(df, "DATA DE NASCIMENTO")
        c_notif   = col(df, "NOTIFICAÇÃO", "NOTIFICACAO")
        c_bairro  = col(df, "BAIRRO")
        c_sit     = col(df, "SITUAÇÃO", "SITUACAO")
        c_local   = col(df, "LOCAL DE ATENDIMENTO")
        c_mae     = col(df, "NOME DA MÃE", "NOME DA MAE")
        c_obs     = col(df, "OBSERVAÇÕES", "OBSERVACOES")
        c_res     = col(df, "RESULTADO")
        c_aplic   = col(df, "APLICAÇÃO", "APLICACAO")
        c_agentes = col(df, "AGENTE(S)", "AGENTES")
        c_prim    = col(df, "1ª VISITA", "1A VISITA")
        c_obs2    = col(df, "UNNAMED: 15", "UNNAMED:15", "OBSERVACAO2")

        # validação de colunas obrigatórias
        obrigatorias = {"NOME": c_nome, "SINAN": c_sinan, "ENDEREÇO": c_end}
        for nome, ref in obrigatorias.items():
            if ref is None:
                add_erro(erros_log["planilha"], "estrutura", None, nome, None, "coluna ausente")

        for c in [c_inicio, c_nasc, c_notif]:
            if c:
                df[c] = corrigir_datas_mistas(df[c])

        if c_inicio:
            datas_validas = df[c_inicio].dropna()
            ponto_partida = datas_validas.iloc[0] if not datas_validas.empty else pd.to_datetime("2026-01-01")
            df[c_inicio] = df[c_inicio].fillna(ponto_partida)
            df[c_inicio] = df[c_inicio].ffill()

        df['temp_hash'] = df.apply(lambda r: hashlib.sha256(
            f"POS|{str(r.get(c_sinan))}|{str(r.get(c_nome))}|{str(r.get(c_nasc))}".encode()
        ).hexdigest(), axis=1)
        df = df.drop_duplicates(subset=['temp_hash'])

        # Coordenadas default para comparação
        DEF_LAT, DEF_LON = -27.022986, -48.652135

        params_temp = []
        params_gl   = []

        for idx, r in df.iterrows():
            linha_excel = idx + 2

            try:
                nome_v = str(r.get(c_nome) or "").strip().upper()
                if not nome_v or nome_v == 'NAN':
                    add_erro(erros_log["planilha"], "preenchimento", linha_excel, "NOME", r.get(c_nome), "campo obrigatório vazio")
                    continue

                sinan_raw = r.get(c_sinan)
                try:
                    sinan_int = int(float(sinan_raw)) if sinan_raw and str(sinan_raw) != 'nan' else None
                except:
                    add_erro(erros_log["planilha"], "preenchimento", linha_excel, "SINAN", sinan_raw, "valor inválido", "não é número")
                    sinan_int = None

                end_v = str(r.get(c_end) or "").strip().upper()
                if not end_v:
                    add_erro(erros_log["planilha"], "preenchimento", linha_excel, "ENDEREÇO", r.get(c_end), "campo vazio")

                try:
                    dt_ini = r.get(c_inicio).date() if pd.notna(r.get(c_inicio)) else None
                except:
                    add_erro(erros_log["planilha"], "preenchimento", linha_excel, "INÍCIO SINTOMAS", r.get(c_inicio), "data inválida")
                    dt_ini = None

                try:
                    dt_nasc = r.get(c_nasc).date() if pd.notna(r.get(c_nasc)) else None
                except:
                    add_erro(erros_log["planilha"], "preenchimento", linha_excel, "DATA NASCIMENTO", r.get(c_nasc), "data inválida")
                    dt_nasc = None

                try:
                    dt_notif = r.get(c_notif).date() if pd.notna(r.get(c_notif)) else None
                except:
                    add_erro(erros_log["planilha"], "preenchimento", linha_excel, "NOTIFICAÇÃO", r.get(c_notif), "data inválida")
                    dt_notif = None

                bairro_v  = str(r.get(c_bairro))[:50]   if pd.notna(r.get(c_bairro))  else None
                local_v   = str(r.get(c_local))[:100]   if pd.notna(r.get(c_local))   else None
                sit_v     = str(r.get(c_sit))[:255]     if pd.notna(r.get(c_sit))     else None
                mae_v     = str(r.get(c_mae))[:255]     if pd.notna(r.get(c_mae))     else None
                obs_v     = str(r.get(c_obs))[:255]     if pd.notna(r.get(c_obs))     else None
                res_v     = str(r.get(c_res))[:50]      if pd.notna(r.get(c_res))     else None
                aplic_v   = str(r.get(c_aplic))[:50]    if pd.notna(r.get(c_aplic))   else None
                agentes_v = str(r.get(c_agentes))[:100] if pd.notna(r.get(c_agentes)) else None

                prim_v = _formatar_data_visita(r.get(c_prim))
                obs2_v = str(r.get(c_obs2))[:255] if pd.notna(r.get(c_obs2)) else None

                h = r['temp_hash']

                # --- GEOCODIFICAÇÃO com log de falha ---
                lat, lon = _geocodificar_endereco(end_v, bairro_v)

                if lat == DEF_LAT and lon == DEF_LON:
                    add_erro(
                        erros_log["geoprocessamento"],
                        "geocodificacao",
                        linha_excel,
                        "ENDEREÇO",
                        end_v,
                        erro="geocodificação falhou",
                        detalhe="usando coordenada default do município"
                    )

                params_temp.append((
                    h, nome_v, end_v, sinan_int, dt_ini, dt_notif, dt_nasc, bairro_v,
                    local_v, sit_v, mae_v, obs_v, res_v, aplic_v, agentes_v, prim_v, obs2_v
                ))

                params_gl.append((
                    h, nome_v, end_v, sinan_int, dt_ini, dt_notif, dt_nasc, bairro_v,
                    local_v, sit_v, mae_v, obs_v, res_v, aplic_v, agentes_v, prim_v, obs2_v,
                    f"POINT({lon} {lat})"
                ))

            except Exception as e:
                add_erro(erros_log["planilha"], "sistema", linha_excel, erro="erro inesperado", detalhe=str(e))

        with transaction.atomic():
            with connection.cursor() as cursor:
                # FIX: geometry adicionada ao ON CONFLICT DO UPDATE para registros
                # que já existiam no banco receberem a geometria correta ao reprocessar.
                sql = """
                    INSERT INTO {tabela}
                    (hash_registro, nome, endereco, sinan, inicio_sintomas, notificacao, data_nasc,
                     bairro, local_atendimento, situacao, nome_mae, observacoes, resultado,
                     aplicacao, agentes, prim_visita, observacao2 {extra_col})
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s {extra_val})
                    ON CONFLICT (hash_registro) DO UPDATE SET
                        situacao    = EXCLUDED.situacao,
                        resultado   = EXCLUDED.resultado,
                        observacoes = EXCLUDED.observacoes,
                        endereco    = EXCLUDED.endereco,
                        bairro      = EXCLUDED.bairro,
                        prim_visita = EXCLUDED.prim_visita,
                        observacao2 = EXCLUDED.observacao2
                        {extra_update}
                """
                cursor.executemany(
                    sql.format(
                        tabela="casos_positivos_temp",
                        extra_col="",
                        extra_val="",
                        extra_update=""
                    ),
                    params_temp
                )
                cursor.executemany(
                    sql.format(
                        tabela="casos_positivos_temp_gl",
                        extra_col=", geometry",
                        extra_val=", ST_GeomFromText(%s, 4674)",
                        extra_update=", geometry = EXCLUDED.geometry"  # FIX: atualiza geometria no conflito
                    ),
                    params_gl
                )

        log.mensagem = json.dumps({
            "resumo": {
                "total_erros": len(erros_log["planilha"]) + len(erros_log["geoprocessamento"]),
                "planilha": len(erros_log["planilha"]),
                "geoprocessamento": len(erros_log["geoprocessamento"])
            },
            "erros": erros_log
        }, ensure_ascii=False, indent=2)

        log.status = "finalizado"
        log.save()

    except Exception as e:
        LogSincronizacao.objects.filter(id=job_id).update(status="erro", mensagem=str(e))

    finally:
        if os.path.exists(arquivo_path):
            try: os.remove(arquivo_path)
            except: pass


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


# --- 5. TASK ARMADILHAS ---
# Planilha: título L1, "Município: X" L2, cabeçalho L4 → header=3
# Colunas: Número, Município, Localidade, Endereço, Complemento, Quarteiroes,
#          Tipo Imóvel, Tipo Armadilha, Latitude, Longitude

@shared_task(bind=True)
def task_processar_armadilhas(self, job_id, arquivo_path):
    try:
        log = LogSincronizacao.objects.get(id=job_id)
        erros = ErrorLogger()
        df_temp = pd.read_excel(arquivo_path, header=None)
        h_idx = next((i for i, row in df_temp.iterrows() if any("Número" in str(x) for x in row)), 0)
        df = pd.read_excel(arquivo_path, header=h_idx).dropna(how='all')

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