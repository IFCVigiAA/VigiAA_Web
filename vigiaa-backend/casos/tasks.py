import os
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

# --- 1. AUXILIARES DE TRATAMENTO ---

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
        c_nome = col(df, "NOME")
        c_sinan = col(df, "SINAN")
        c_end = col(df, "ENDEREÇO", "ENDERECO")
        c_nasc = col(df, "DATA DE NASCIMENTO")
        c_notif = col(df, "NOTIFICAÇÃO", "NOTIFICACAO")
        c_bairro = col(df, "BAIRRO")
        c_sit = col(df, "SITUAÇÃO", "SITUACAO")
        c_local = col(df, "LOCAL DE ATENDIMENTO")
        c_mae = col(df, "NOME DA MÃE", "NOME DA MAE")
        c_obs = col(df, "OBSERVAÇÕES", "OBSERVACOES")
        c_res = col(df, "RESULTADO")
        c_aplic = col(df, "APLICAÇÃO", "APLICACAO")
        c_agentes = col(df, "AGENTE(S)", "AGENTES")
        c_prim = col(df, "1ª VISITA", "1A VISITA")
        c_obs2 = col(df, "UNNAMED: 15", "UNNAMED:15", "OBSERVACAO2")

        for c in [c_inicio, c_nasc, c_notif]:
            if c: df[c] = corrigir_datas_mistas(df[c])
        
        if c_inicio:
            datas_validas = df[c_inicio].dropna()
            ponto_partida = datas_validas.iloc[0] if not datas_validas.empty else pd.to_datetime("2026-01-01")
            df[c_inicio] = df[c_inicio].fillna(ponto_partida)
            df = df.sort_values(by=c_inicio, ascending=True).reset_index(drop=True)
            df[c_inicio] = df[c_inicio].ffill()

        df = df.dropna(subset=[c_nome]) if c_nome else df
        df['temp_hash'] = df.apply(lambda r: hashlib.sha256(
            f"POS|{str(r.get(c_sinan))}|{str(r.get(c_nome))}|{str(r.get(c_nasc))}".encode()
        ).hexdigest(), axis=1)
        df = df.drop_duplicates(subset=['temp_hash'])

        params_temp = []
        params_gl = []

        for _, r in df.iterrows():
            nome_v = str(r.get(c_nome) or "").strip().upper()
            if not nome_v or nome_v == 'NAN': continue
            
            sinan_v = str(r.get(c_sinan) or "").strip()
            end_v = str(r.get(c_end) or "").strip().upper()
            dt_ini = r.get(c_inicio).date() if pd.notna(r.get(c_inicio)) else None
            dt_nasc = r.get(c_nasc).date() if pd.notna(r.get(c_nasc)) else None
            dt_notif = r.get(c_notif).date() if pd.notna(r.get(c_notif)) else None
            
            bairro_v = str(r.get(c_bairro))[:50] if pd.notna(r.get(c_bairro)) else None
            local_v = str(r.get(c_local))[:100] if pd.notna(r.get(c_local)) else None
            sit_v = str(r.get(c_sit))[:255] if pd.notna(r.get(c_sit)) else None
            mae_v = str(r.get(c_mae))[:255] if pd.notna(r.get(c_mae)) else None
            obs_v = str(r.get(c_obs))[:255] if pd.notna(r.get(c_obs)) else None
            res_v = str(r.get(c_res))[:50] if pd.notna(r.get(c_res)) else None
            aplic_v = str(r.get(c_aplic))[:50] if pd.notna(r.get(c_aplic)) else None
            agentes_v = str(r.get(c_agentes))[:100] if pd.notna(r.get(c_agentes)) else None
            prim_v = str(r.get(c_prim))[:50] if pd.notna(r.get(c_prim)) else None
            obs2_v = str(r.get(c_obs2))[:255] if pd.notna(r.get(c_obs2)) else None

            h = r['temp_hash']
            sinan_int = int(float(sinan_v)) if sinan_v and sinan_v != 'nan' else None
            lat, lon = _geocodificar_endereco(end_v, bairro_v)

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
                
                sql_temp = """
                    INSERT INTO casos_positivos_temp 
                    (hash_registro, nome, endereco, sinan, inicio_sintomas, notificacao, data_nasc, 
                    bairro, local_atendimento, situacao, nome_mae, observacoes, resultado, aplicacao, agentes, prim_visita, observacao2)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (hash_registro) DO NOTHING
                """
                cursor.executemany(sql_temp, params_temp)

                sql_gl = """
                    INSERT INTO casos_positivos_temp_gl 
                    (hash_registro, nome, endereco, sinan, inicio_sintomas, notificacao, data_nasc, 
                    bairro, local_atendimento, situacao, nome_mae, observacoes, resultado, aplicacao, agentes, prim_visita, observacao2, geometry)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, ST_GeomFromText(%s, 4674))
                    ON CONFLICT (hash_registro) DO NOTHING
                """
                cursor.executemany(sql_gl, params_gl)

        log.status, log.progresso = "finalizado", 100; log.save()

    except Exception as e:
        LogSincronizacao.objects.filter(id=job_id).update(status="erro", mensagem=str(e))
    
    finally:
        # AQUI ESTÁ A MÁGICA: Independente do que acontecer, o arquivo é deletado.
        if os.path.exists(arquivo_path):
            try: os.remove(arquivo_path)
            except: pass

# --- TASKS DE FOCOS, PONTOS E ARMADILHAS ---

@shared_task(bind=True)
def task_processar_focos(self, job_id, arquivo_path):
    try:
        log = LogSincronizacao.objects.get(id=job_id)
        df_raw = pd.read_excel(arquivo_path, header=None)
        h_idx = 0
        for idx, row in df_raw.iterrows():
            if any("N FOCO" in _normalize(str(x)) for x in row):
                h_idx = idx + 1; break
        df = pd.read_excel(arquivo_path, skiprows=h_idx)
        objs = []
        for _, r in df.iterrows():
            lt, ln = r.get(col(df, "LATITUDE")), r.get(col(df, "LONGITUDE"))
            if pd.isna(lt): continue
            h = hashlib.sha256(f"FOCO|{r.get(col(df, 'N FOCO'))}|{lt}|{ln}".encode()).hexdigest()
            objs.append(FocoTemp(
                hash_registro=h, n_foco=str(r.get(col(df, "N FOCO"))),
                geometry=Point(float(ln), float(lt), srid=4674),
                latitude=float(lt), longitude=float(ln)
            ))
        with transaction.atomic():
            FocoTemp.objects.all().delete()
            FocoTemp.objects.bulk_create(objs)
        log.status = "finalizado"; log.save()
    except Exception as e:
        LogSincronizacao.objects.filter(id=job_id).update(status="erro", mensagem=str(e))
    finally:
        if os.path.exists(arquivo_path):
            try: os.remove(arquivo_path)
            except: pass

@shared_task(bind=True)
def task_processar_pontos(self, job_id, arquivo_path):
    try:
        log = LogSincronizacao.objects.get(id=job_id)
        df = pd.read_excel(arquivo_path, header=3)
        objs = []
        for _, r in df.iterrows():
            lt, ln = r.get(col(df, "LATITUDE")), r.get(col(df, "LONGITUDE"))
            if pd.isna(lt): continue
            h = hashlib.sha256(f"PONTO|{r.get(col(df, 'NUMERO'))}|{lt}".encode()).hexdigest()
            objs.append(PontoEstrategicoTemp(
                hash_registro=h, numero=str(r.get(col(df, "NUMERO"))),
                geometry=Point(float(ln), float(lt), srid=4674),
                latitude=float(lt), longitude=float(ln)
            ))
        with transaction.atomic():
            PontoEstrategicoTemp.objects.all().delete()
            PontoEstrategicoTemp.objects.bulk_create(objs)
        log.status = "finalizado"; log.save()
    except Exception as e:
        LogSincronizacao.objects.filter(id=job_id).update(status="erro", mensagem=str(e))
    finally:
        if os.path.exists(arquivo_path):
            try: os.remove(arquivo_path)
            except: pass

@shared_task(bind=True)
def task_processar_armadilhas(self, job_id, arquivo_path):
    try:
        log = LogSincronizacao.objects.get(id=job_id)
        df = pd.read_excel(arquivo_path, header=3)
        objs = []
        for _, r in df.iterrows():
            lt, ln = r.get(col(df, "LATITUDE")), r.get(col(df, "LONGITUDE"))
            if pd.isna(lt): continue
            h = hashlib.sha256(f"ARM|{r.get(col(df, 'NUMERO'))}|{ln}".encode()).hexdigest()
            objs.append(ArmadilhaTemp(
                hash_registro=h, numero=str(r.get(col(df, "NUMERO"))),
                geometry=Point(float(ln), float(lt), srid=4674),
                latitude=float(lt), longitude=float(ln)
            ))
        with transaction.atomic():
            ArmadilhaTemp.objects.all().delete()
            ArmadilhaTemp.objects.bulk_create(objs)
        log.status = "finalizado"; log.save()
    except Exception as e:
        LogSincronizacao.objects.filter(id=job_id).update(status="erro", mensagem=str(e))
    finally:
        if os.path.exists(arquivo_path):
            try: os.remove(arquivo_path)
            except: pass