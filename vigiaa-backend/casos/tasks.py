import os
import logging
import pandas as pd
import geocoder
import hashlib
import unicodedata
from celery import shared_task
from django.db import connection, transaction
from django.contrib.gis.geos import Point

# Importação relativa
from .models import (
    LogSincronizacao, PontoEstrategicoTemp, FocoTemp,
    ArmadilhaTemp, CasoPositivoTemp, CasoPositivoTempGL
)

logger = logging.getLogger(__name__)

# --- 1. AUXILIARES DE TRATAMENTO ---

DEFAULT_STR = "NÃO INFORMADO"

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
    # Tenta número serial do Excel
    try:
        f = float(val)
        if not pd.isna(f) and f > 1000:  # sanity check: evita converter números pequenos
            dt = pd.Timestamp('1899-12-30') + pd.Timedelta(days=int(f))
            return dt.strftime('%d/%m/%Y')
    except (ValueError, TypeError):
        pass
    # Tenta parsear como data diretamente
    try:
        ts = pd.Timestamp(val)
        if pd.notna(ts):
            return ts.strftime('%d/%m/%Y')
    except Exception:
        pass
    # Fallback: retorna como string limpa (sem " 00:00:00")
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

    # Número serial do Excel (ex: 45995)
    try:
        num = float(val)
        if pd.isna(num):
            return None
        # Se for um número plausível como serial de data Excel (> 1000)
        if num > 1000:
            try:
                dt = pd.Timestamp('1899-12-30') + pd.Timedelta(days=int(num))
                return str(dt.date())[:maxlen]
            except:
                pass
    except (ValueError, TypeError):
        pass

    # Já é um datetime/Timestamp do pandas
    try:
        if hasattr(val, 'date'):
            return str(val.date())[:maxlen]
    except:
        pass

    # String — tenta parsear como data
    s = str(val).strip()
    if not s or s.upper() == 'NAN':
        return None
    try:
        return str(pd.to_datetime(s, dayfirst=True).date())[:maxlen]
    except:
        pass

    # Retorna como string pura (pode já estar formatada corretamente)
    return s[:maxlen]

def _geocodificar_endereco(endereco, bairro):
    def_lat, def_lon = -27.022986, -48.652135
    if not endereco: return def_lat, def_lon
    try:
        query = f"{str(endereco).upper()}, {bairro or ''}, CAMBORIÚ, SC, BRASIL"
        g = geocoder.arcgis(query, timeout=5)
        if g.ok and g.latlng: return float(g.latlng[0]), float(g.latlng[1])
    except: pass
    return def_lat, def_lon

# --- 2. TASK POSITIVOS ---

@shared_task(bind=True)
def task_processar_positivos(self, job_id, arquivo_path):
    try:
        log = LogSincronizacao.objects.get(id=job_id)
        df = pd.read_excel(arquivo_path)

        c_inicio = col(df, "INÍCIO SINTOMAS", "INICIO SINTOMAS")
        c_nome   = col(df, "NOME")
        c_sinan  = col(df, "SINAN")
        c_end    = col(df, "ENDEREÇO", "ENDERECO")
        c_nasc   = col(df, "DATA DE NASCIMENTO")
        c_notif  = col(df, "NOTIFICAÇÃO", "NOTIFICACAO")
        c_bairro = col(df, "BAIRRO")
        c_sit    = col(df, "SITUAÇÃO", "SITUACAO")
        c_local  = col(df, "LOCAL DE ATENDIMENTO")
        c_mae    = col(df, "NOME DA MÃE", "NOME DA MAE")
        c_obs    = col(df, "OBSERVAÇÕES", "OBSERVACOES")
        c_res    = col(df, "RESULTADO")
        c_aplic  = col(df, "APLICAÇÃO", "APLICACAO")
        c_agentes = col(df, "AGENTE(S)", "AGENTES")
        c_prim   = col(df, "1ª VISITA", "1A VISITA")
        c_obs2   = col(df, "UNNAMED: 15", "UNNAMED:15", "OBSERVACAO2")

        for c in [c_inicio, c_nasc, c_notif]:
            if c: df[c] = corrigir_datas_mistas(df[c])

        if c_inicio:
            datas_validas = df[c_inicio].dropna()
            ponto_partida = datas_validas.iloc[0] if not datas_validas.empty else pd.to_datetime("2026-01-01")
            df[c_inicio] = df[c_inicio].fillna(ponto_partida)
            df[c_inicio] = df[c_inicio].ffill()

        df = df.dropna(subset=[c_nome]) if c_nome else df
        df['temp_hash'] = df.apply(lambda r: hashlib.sha256(
            f"POS|{str(r.get(c_sinan))}|{str(r.get(c_nome))}|{str(r.get(c_nasc))}".encode()
        ).hexdigest(), axis=1)
        df = df.drop_duplicates(subset=['temp_hash'])

        params_temp = []
        params_gl   = []

        for _, r in df.iterrows():
            nome_v = str(r.get(c_nome) or "").strip().upper()
            if not nome_v or nome_v == 'NAN': continue

            sinan_v  = str(r.get(c_sinan) or "").strip()
            end_v    = str(r.get(c_end) or "").strip().upper()
            dt_ini   = r.get(c_inicio).date() if pd.notna(r.get(c_inicio)) else None
            dt_nasc  = r.get(c_nasc).date()   if pd.notna(r.get(c_nasc))   else None
            dt_notif = r.get(c_notif).date()  if pd.notna(r.get(c_notif))  else None

            bairro_v  = str(r.get(c_bairro))[:50]   if pd.notna(r.get(c_bairro))  else None
            local_v   = str(r.get(c_local))[:100]   if pd.notna(r.get(c_local))   else None
            sit_v     = str(r.get(c_sit))[:255]     if pd.notna(r.get(c_sit))     else None
            mae_v     = str(r.get(c_mae))[:255]     if pd.notna(r.get(c_mae))     else None
            obs_v     = str(r.get(c_obs))[:255]     if pd.notna(r.get(c_obs))     else None
            res_v     = str(r.get(c_res))[:50]      if pd.notna(r.get(c_res))     else None
            aplic_v   = str(r.get(c_aplic))[:50]    if pd.notna(r.get(c_aplic))   else None
            agentes_v = str(r.get(c_agentes))[:100] if pd.notna(r.get(c_agentes)) else None
            # prim_visita é string mas pode vir como:
            #   - número serial do Excel (ex: 45995)
            #   - objeto datetime/Timestamp (ex: 2025-06-27 00:00:00)
            #   - texto puro (ex: "LUCIANE", "22/02/2025")
            _prim_raw = r.get(c_prim)
            if _prim_raw is None or (isinstance(_prim_raw, float) and pd.isna(_prim_raw)):
                prim_v = None
            else:
                _prim_str = str(_prim_raw).strip()
                # Serial numérico do Excel (ex: 45995)
                try:
                    _num = float(_prim_raw)
                    if not pd.isna(_num) and _num > 1000:
                        _dt = pd.Timestamp('1899-12-30') + pd.Timedelta(days=int(_num))
                        prim_v = _dt.strftime('%d/%m/%Y')
                    else:
                        prim_v = _prim_str[:50]
                except (ValueError, TypeError):
                    # Datetime/Timestamp (ex: 2025-06-27 00:00:00)
                    if hasattr(_prim_raw, 'strftime'):
                        prim_v = _prim_raw.strftime('%d/%m/%Y')
                    # String que parece data (contém / ou - e tem dígitos)
                    elif any(c.isdigit() for c in _prim_str) and ('/' in _prim_str or '-' in _prim_str):
                        try:
                            prim_v = pd.to_datetime(_prim_str, dayfirst=True).strftime('%d/%m/%Y')
                        except Exception:
                            prim_v = _prim_str[:50]
                    else:
                        # Texto puro (ex: "LUCIANE", "MAYON") — salva como está
                        prim_v = _prim_str[:50]
            obs2_v    = str(r.get(c_obs2))[:255]    if pd.notna(r.get(c_obs2))    else None

            h = r['temp_hash']
            sinan_int = int(float(sinan_v)) if sinan_v and sinan_v != 'nan' else None
            lat, lon  = _geocodificar_endereco(end_v, bairro_v)

            params_temp.append((
                h, nome_v, end_v, sinan_int, dt_ini, dt_notif, dt_nasc, bairro_v,
                local_v, sit_v, mae_v, obs_v, res_v, aplic_v, agentes_v, prim_v, obs2_v
            ))
            params_gl.append((
                h, nome_v, end_v, sinan_int, dt_ini, dt_notif, dt_nasc, bairro_v,
                local_v, sit_v, mae_v, obs_v, res_v, aplic_v, agentes_v, prim_v, obs2_v,
                f"POINT({lon} {lat})"
            ))

        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute('DELETE FROM casos_positivos_temp')
                cursor.execute('DELETE FROM casos_positivos_temp_gl')

                cursor.executemany("""
                    INSERT INTO casos_positivos_temp
                    (hash_registro, nome, endereco, sinan, inicio_sintomas, notificacao, data_nasc,
                     bairro, local_atendimento, situacao, nome_mae, observacoes, resultado,
                     aplicacao, agentes, prim_visita, observacao2)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (hash_registro) DO NOTHING
                """, params_temp)

                cursor.executemany("""
                    INSERT INTO casos_positivos_temp_gl
                    (hash_registro, nome, endereco, sinan, inicio_sintomas, notificacao, data_nasc,
                     bairro, local_atendimento, situacao, nome_mae, observacoes, resultado,
                     aplicacao, agentes, prim_visita, observacao2, geometry)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,ST_GeomFromText(%s,4674))
                    ON CONFLICT (hash_registro) DO NOTHING
                """, params_gl)

        log.status, log.progresso = "finalizado", 100
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

        # -----------------------------------------------------------------
        # Passo 1: detectar qual linha é o cabeçalho
        # -----------------------------------------------------------------
        df_raw = pd.read_excel(arquivo_path, header=None)

        h_idx = None
        for idx, row in df_raw.iterrows():
            normalized_vals = [_normalize(str(x)) for x in row]
            if any(
                v in ("N FOCO", "NO FOCO", "NFOCO") or "N FOCO" in v
                for v in normalized_vals
            ):
                h_idx = idx
                break

        if h_idx is None:
            # Fallback: linha 3 (índice 2) — padrão visual da planilha
            h_idx = 2
            logger.warning("[FOCOS] 'N FOCO' não encontrado — fallback h_idx=2")

        logger.warning(f"[FOCOS DEBUG] h_idx={h_idx} | raw: {list(df_raw.iloc[h_idx])}")

        # -----------------------------------------------------------------
        # Passo 2: reler usando h_idx como linha de cabeçalho
        # -----------------------------------------------------------------
        df = pd.read_excel(arquivo_path, header=h_idx)
        df = df.dropna(how='all')  # remove linhas totalmente vazias

        logger.warning(f"[FOCOS DEBUG] colunas={list(df.columns)} | linhas={len(df)}")

        # Mapeia colunas
        c_nfoco    = col(df, "Nº FOCO", "N FOCO", "NO FOCO", "NFOCO")
        c_regional = col(df, "REGIONAL")
        c_mun      = col(df, "MUNICÍPIO", "MUNICIPIO")
        c_local    = col(df, "LOCALIDADE")
        c_end      = col(df, "RUA/NÚMERO", "RUA/NUMERO", "RUA NUMERO", "ENDEREÇO", "ENDERECO")
        c_comp     = col(df, "COMPLEMENTO")
        c_quart    = col(df, "QUARTEIRÃO", "QUARTEIRAO")
        c_imovel   = col(df, "IMÓVEL", "IMOVEL")
        c_deposito = col(df, "DEPÓSITO", "DEPOSITO")
        c_tipo_atv = col(df, "TIPO DE ATIVIDADE", "TIPO ATIVIDADE")
        c_dt_col   = col(df, "DATA DA COLETA",  "DATA COLETA")
        c_dt_ent   = col(df, "DATA DA ENTRADA", "DATA ENTRADA")
        c_dt_exam  = col(df, "DATA DO EXAME",   "DATA EXAME")
        c_aeg_aq   = col(df, "A. AEGYPTI FORMAS AQUATICAS",    "A AEGYPTI FORMAS AQUATICAS",
                            "A. AEGYPTI FORM. AQUATICAS")
        c_aeg_ad   = col(df, "A. AEGYPTI FORMAS ADULTAS",      "A AEGYPTI FORMAS ADULTAS",
                            "A. AEGYPTI FORM. ADULTAS")
        c_alb_aq   = col(df, "A. ALBOPICTUS FORMAS AQUATICAS", "A ALBOPICTUS FORMAS AQUATICAS",
                            "A. ALBOPICTUS FORM. AQUATICAS")
        c_alb_ad   = col(df, "A. ALBOPICTUS FORMAS ADULTAS",   "A ALBOPICTUS FORMAS ADULTAS",
                            "A. ALBOPICTUS FORM. ADULTAS")
        c_ovo      = col(df, "OVO A. AEGYPTI", "OVO A AEGYPTI")
        c_lat      = col(df, "LATITUDE")
        c_lon      = col(df, "LONGITUDE")

        logger.warning(
            f"[FOCOS DEBUG] c_lat={c_lat} | c_lon={c_lon} | c_nfoco={c_nfoco} | "
            f"c_mun={c_mun} | c_local={c_local} | c_end={c_end}"
        )
        if c_lat:
            logger.warning(f"[FOCOS DEBUG] primeiras lats: {df[c_lat].head(5).tolist()}")
        else:
            logger.warning("[FOCOS DEBUG] *** LATITUDE não mapeada! Verifique o cabeçalho. ***")

        # Corrige datas e preenche vazios com o valor do registro anterior (ffill)
        for c in [c_dt_col, c_dt_ent, c_dt_exam]:
            if c:
                df[c] = corrigir_datas_mistas(df[c])
                df[c] = df[c].ffill()

        def _int_safe(val):
            try:
                if pd.isna(val): return 0
                return int(float(val))
            except: return 0

        def _date_safe(r, c, *fallbacks):
            """Retorna a data do campo c, ou tenta os fallbacks em ordem."""
            for campo in (c, *fallbacks):
                if not campo: continue
                v = r.get(campo)
                if v is None or (isinstance(v, float) and pd.isna(v)): continue
                try: return pd.Timestamp(v).date()
                except: continue
            return None

        objs    = []
        pulados = 0
        for _, r in df.iterrows():
            lt = r.get(c_lat) if c_lat else None
            ln = r.get(c_lon) if c_lon else None
            if lt is None or (isinstance(lt, float) and pd.isna(lt)):
                pulados += 1
                continue

            h = hashlib.sha256(
                f"FOCO|{r.get(c_nfoco)}|{lt}|{ln}".encode()
            ).hexdigest()

            # Datas NOT NULL: fallback em cascata entre as três colunas
            dt_col  = _date_safe(r, c_dt_col,  c_dt_ent,  c_dt_exam)
            dt_ent  = _date_safe(r, c_dt_ent,  c_dt_col,  c_dt_exam)
            dt_exam = _date_safe(r, c_dt_exam, c_dt_col,  c_dt_ent)

            objs.append(FocoTemp(
                hash_registro               = h,
                n_foco                      = _get_str(r, c_nfoco,    30),
                regional                    = _get_str(r, c_regional, 20),
                municipio                   = _get_str(r, c_mun,      50),
                localidade                  = _get_str(r, c_local,    100),
                rua_numero                  = _get_str(r, c_end,      255),
                complemento                 = _get_str(r, c_comp,     255, default=""),
                quarteirao                  = _get_str(r, c_quart,    50),
                imovel                      = _get_str(r, c_imovel,   50),
                deposito                    = _get_str(r, c_deposito, 100),
                tipo_atividade              = _get_str(r, c_tipo_atv, 50),
                data_coleta                 = dt_col,
                data_entrada                = dt_ent,
                data_exame                  = dt_exam,
                a_aegypti_form_aquaticas    = _int_safe(r.get(c_aeg_aq)),
                a_aegypti_form_adultas      = _int_safe(r.get(c_aeg_ad)),
                a_albopictus_form_aquaticas = _int_safe(r.get(c_alb_aq)),
                a_albopictus_form_adultas   = _int_safe(r.get(c_alb_ad)),
                ovo_a_aegypti               = _int_safe(r.get(c_ovo)),
                geometry                    = Point(float(ln), float(lt), srid=4674),
                latitude                    = float(lt),
                longitude                   = float(ln),
            ))

        logger.warning(f"[FOCOS DEBUG] prontos={len(objs)} | pulados={pulados}")

        with transaction.atomic():
            FocoTemp.objects.all().delete()
            FocoTemp.objects.bulk_create(objs)

        logger.warning(f"[FOCOS DEBUG] inseridos={len(objs)}")
        log.status = "finalizado"
        log.save()

    except Exception as e:
        logger.error(f"[FOCOS ERRO] {str(e)}", exc_info=True)
        LogSincronizacao.objects.filter(id=job_id).update(status="erro", mensagem=str(e))
    finally:
        if os.path.exists(arquivo_path):
            try: os.remove(arquivo_path)
            except: pass

# --- 4. TASK PONTOS ESTRATÉGICOS ---
# Planilha: título L1, "Município: X" L2, cabeçalho L4 → header=3
# Colunas: Número, Município, Localidade, Endereço, Quarteiroes, Complemento, Latitude, Longitude

@shared_task(bind=True)
def task_processar_pontos(self, job_id, arquivo_path):
    try:
        log = LogSincronizacao.objects.get(id=job_id)
        df = pd.read_excel(arquivo_path, header=3)
        df = df.dropna(how='all')

        c_num   = col(df, "NÚMERO", "NUMERO")
        c_mun   = col(df, "MUNICÍPIO", "MUNICIPIO")
        c_local = col(df, "LOCALIDADE")
        c_end   = col(df, "ENDEREÇO", "ENDERECO")
        c_quart = col(df, "QUARTEIROES", "QUARTEIRAO", "QUARTEIRÕES")
        c_comp  = col(df, "COMPLEMENTO")
        c_lat   = col(df, "LATITUDE")
        c_lon   = col(df, "LONGITUDE")

        objs = []
        for _, r in df.iterrows():
            lt = r.get(c_lat) if c_lat else None
            ln = r.get(c_lon) if c_lon else None
            if lt is None or (isinstance(lt, float) and pd.isna(lt)):
                continue

            h = hashlib.sha256(f"PONTO|{r.get(c_num)}|{lt}".encode()).hexdigest()

            objs.append(PontoEstrategicoTemp(
                hash_registro = h,
                numero        = _get_str(r, c_num,   50),
                municipio     = _get_str(r, c_mun,   100),
                localidade    = _get_str(r, c_local, 100),
                endereco      = _get_str(r, c_end,   255),
                quarteiroes   = _get_str(r, c_quart, 50),
                complemento   = _get_str(r, c_comp,  255, default=""),
                geometry      = Point(float(ln), float(lt), srid=4674),
                latitude      = float(lt),
                longitude     = float(ln),
            ))

        with transaction.atomic():
            PontoEstrategicoTemp.objects.all().delete()
            PontoEstrategicoTemp.objects.bulk_create(objs)

        log.status = "finalizado"
        log.save()

    except Exception as e:
        LogSincronizacao.objects.filter(id=job_id).update(status="erro", mensagem=str(e))
    finally:
        if os.path.exists(arquivo_path):
            try: os.remove(arquivo_path)
            except: pass

# --- 5. TASK ARMADILHAS ---
# Planilha: título L1, "Município: X" L2, cabeçalho L4 → header=3
# Colunas: Número, Município, Localidade, Endereço, Complemento, Quarteiroes,
#          Tipo Imóvel, Tipo Armadilha, Latitude, Longitude

@shared_task(bind=True)
def task_processar_armadilhas(self, job_id, arquivo_path):
    try:
        log = LogSincronizacao.objects.get(id=job_id)
        df = pd.read_excel(arquivo_path, header=3)
        df = df.dropna(how='all')

        c_num      = col(df, "NÚMERO", "NUMERO")
        c_mun      = col(df, "MUNICÍPIO", "MUNICIPIO")
        c_local    = col(df, "LOCALIDADE")
        c_end      = col(df, "ENDEREÇO", "ENDERECO")
        c_comp     = col(df, "COMPLEMENTO")
        c_quart    = col(df, "QUARTEIROES", "QUARTEIRAO", "QUARTEIRÕES")
        c_tipo_im  = col(df, "TIPO IMÓVEL", "TIPO IMOVEL")
        c_tipo_arm = col(df, "TIPO ARMADILHA")
        c_lat      = col(df, "LATITUDE")
        c_lon      = col(df, "LONGITUDE")

        objs = []
        for _, r in df.iterrows():
            lt = r.get(c_lat) if c_lat else None
            ln = r.get(c_lon) if c_lon else None
            if lt is None or (isinstance(lt, float) and pd.isna(lt)):
                continue

            h = hashlib.sha256(f"ARM|{r.get(c_num)}|{ln}".encode()).hexdigest()

            objs.append(ArmadilhaTemp(
                hash_registro  = h,
                numero         = _get_str(r, c_num,      50),
                municipio      = _get_str(r, c_mun,      100),
                localidade     = _get_str(r, c_local,    100),
                endereco       = _get_str(r, c_end,      255),
                complemento    = _get_str(r, c_comp,     255, default=""),
                quarteiroes    = _get_str(r, c_quart,    50),
                tipo_imovel    = _get_str(r, c_tipo_im,  50),
                tipo_armadilha = _get_str(r, c_tipo_arm, 50),
                geometry       = Point(float(ln), float(lt), srid=4674),
                latitude       = float(lt),
                longitude      = float(ln),
            ))

        with transaction.atomic():
            ArmadilhaTemp.objects.all().delete()
            ArmadilhaTemp.objects.bulk_create(objs)

        log.status = "finalizado"
        log.save()

    except Exception as e:
        LogSincronizacao.objects.filter(id=job_id).update(status="erro", mensagem=str(e))
    finally:
        if os.path.exists(arquivo_path):
            try: os.remove(arquivo_path)
            except: pass