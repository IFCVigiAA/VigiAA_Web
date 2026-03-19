import os
import pandas as pd
import geocoder
import hashlib
import unicodedata
from celery import shared_task
from django.db import connection, transaction
from django.contrib.gis.geos import Point

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

def _get_str(r, col_name, max_len=100, default="NÃO INFORMADO"):
    if not col_name or pd.isna(r.get(col_name)): return default
    val = str(r.get(col_name)).strip()
    if not val or val.upper() == "NAN": return default
    return val[:max_len]

def _get_int(r, col_name):
    if not col_name or pd.isna(r.get(col_name)): return 0
    try: return int(float(r.get(col_name)))
    except: return 0


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
        c_res = col(df, "RESULTADO")
        c_aplic = col(df, "APLICAÇÃO", "APLICACAO")
        c_agentes = col(df, "AGENTE(S)", "AGENTES")
        c_prim = col(df, "1ª VISITA", "1A VISITA")
        c_obs = col(df, "OBSERVAÇÕES", "OBSERVACOES")

        for c in [c_inicio, c_nasc, c_notif]:
            if c: df[c] = corrigir_datas_mistas(df[c])
        
        if c_inicio:
            df[c_inicio] = df[c_inicio].ffill()

        df = df.dropna(subset=[c_nome]) if c_nome else df
        
        # Geramos o hash com o nome, mas não salvamos ele no banco!
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
            
            bairro_v = _get_str(r, c_bairro, 50, None)
            local_v = _get_str(r, c_local, 100, None)
            sit_v = _get_str(r, c_sit, 255, None)
            obs_v = _get_str(r, c_obs, 255, None)
            res_v = _get_str(r, c_res, 50, None)
            aplic_v = _get_str(r, c_aplic, 50, None)
            agentes_v = _get_str(r, c_agentes, 100, None)
            prim_v = _get_str(r, c_prim, 50, None)

            h = r['temp_hash']
            sinan_int = int(float(sinan_v)) if sinan_v and sinan_v != 'nan' else None
            lat, lon = _geocodificar_endereco(end_v, bairro_v)

            params_temp.append((
                h, local_v, dt_ini, dt_notif, sinan_int, bairro_v, dt_nasc, 
                obs_v, res_v, aplic_v, agentes_v, prim_v, sit_v, lat, lon
            ))

            params_gl.append((
                h, local_v, dt_ini, dt_notif, sinan_int, bairro_v, dt_nasc, 
                obs_v, res_v, aplic_v, agentes_v, prim_v, sit_v, f"POINT({lon} {lat})"
            ))

        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute('DELETE FROM casos_positivos_temp')
                cursor.execute('DELETE FROM casos_positivos_temp_gl')
                
                # Inserção perfeitamente alinhada com o seu models.py
                sql_temp = """
                    INSERT INTO casos_positivos_temp 
                    (hash_registro, local_atendimento, inicio_sintomas, notificacao, sinan, 
                    bairro, data_nasc, observacoes, resultado, aplicacao, agentes, prim_visita, situacao, latitude, longitude)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (hash_registro) DO NOTHING
                """
                cursor.executemany(sql_temp, params_temp)

                sql_gl = """
                    INSERT INTO casos_positivos_temp_gl 
                    (hash_registro, local_atendimento, inicio_sintomas, notificacao, sinan, 
                    bairro, data_nasc, observacoes, resultado, aplicacao, agentes, prim_visita, situacao, geometry)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, ST_GeomFromText(%s, 4674))
                    ON CONFLICT (hash_registro) DO NOTHING
                """
                cursor.executemany(sql_gl, params_gl)

        log.status, log.progresso = "finalizado", 100; log.save()

    except Exception as e:
        LogSincronizacao.objects.filter(id=job_id).update(status="erro", mensagem=str(e))
    
    finally:
        if os.path.exists(arquivo_path):
            try: os.remove(arquivo_path)
            except: pass


# --- 3. TASKS DE FOCOS, PONTOS E ARMADILHAS ---
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
        
        c_nfoco = col(df, "N FOCO", "Nº Foco")
        c_loc = col(df, "LOCALIDADE")
        c_imovel = col(df, "IMOVEL")
        c_deposito = col(df, "DEPOSITO")
        c_ativ = col(df, "TIPO DE ATIVIDADE", "TIPO ATIVIDADE")
        c_data = col(df, "DATA DA COLETA", "DATA COLETA")
        c_lat = col(df, "LATITUDE")
        c_lon = col(df, "LONGITUDE")
        
        c_aeg_aq = col(df, "A. aegypti formas aquáticas", "A. aegypti formas aquaticas")
        c_aeg_ad = col(df, "A. aegypti formas adultas")
        c_albo_aq = col(df, "A. albopictus formas aquáticas", "A. albopictus formas aquaticas")
        c_albo_ad = col(df, "A. albopictus formas adultas")
        c_ovo = col(df, "ovo a. aegypti", "ovo a aegypti")

        if c_data: df[c_data] = corrigir_datas_mistas(df[c_data])

        objs = []
        for _, r in df.iterrows():
            lt, ln = r.get(c_lat), r.get(c_lon)
            if pd.isna(lt): continue
            
            nfoco_v = _get_str(r, c_nfoco, 30)
            h = hashlib.sha256(f"FOCO|{nfoco_v}|{lt}|{ln}".encode()).hexdigest()
            data_v = r.get(c_data).date() if c_data and pd.notna(r.get(c_data)) else pd.Timestamp('today').date()

            objs.append(FocoTemp(
                hash_registro=h,
                n_foco=nfoco_v,
                localidade=_get_str(r, c_loc, 100),
                imovel=_get_str(r, c_imovel, 50),
                deposito=_get_str(r, c_deposito, 100),
                tipo_atividade=_get_str(r, c_ativ, 50),
                data_coleta=data_v,
                a_aegypti_form_aquaticas=_get_int(r, c_aeg_aq),
                a_aegypti_form_adultas=_get_int(r, c_aeg_ad),
                a_albopictus_form_aquaticas=_get_int(r, c_albo_aq),
                a_albopictus_form_adultas=_get_int(r, c_albo_ad),
                ovo_a_aegypti=_get_int(r, c_ovo),
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
        
        c_num = col(df, "NUMERO", "Número")
        c_mun = col(df, "MUNICIPIO", "Município")
        c_loc = col(df, "LOCALIDADE")
        c_end = col(df, "ENDERECO", "Endereço")
        c_quart = col(df, "QUARTEIROES", "Quarteirão")
        c_comp = col(df, "COMPLEMENTO")
        c_lat = col(df, "LATITUDE")
        c_lon = col(df, "LONGITUDE")

        objs = []
        for _, r in df.iterrows():
            lt, ln = r.get(c_lat), r.get(c_lon)
            if pd.isna(lt): continue
            
            num_v = _get_str(r, c_num, 50)
            h = hashlib.sha256(f"PONTO|{num_v}|{lt}".encode()).hexdigest()
            
            objs.append(PontoEstrategicoTemp(
                hash_registro=h,
                numero=num_v,
                municipio=_get_str(r, c_mun, 100),
                localidade=_get_str(r, c_loc, 100),
                endereco=_get_str(r, c_end, 150),
                quarteiroes=_get_str(r, c_quart, 50),
                complemento=_get_str(r, c_comp, 100, ""),
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
        
        c_num = col(df, "NUMERO", "Número")
        c_mun = col(df, "MUNICIPIO", "Município")
        c_loc = col(df, "LOCALIDADE")
        c_end = col(df, "ENDERECO", "Endereço")
        c_comp = col(df, "COMPLEMENTO")
        c_quart = col(df, "QUARTEIROES", "Quarteirão")
        c_tipo_im = col(df, "TIPO IMOVEL", "Tipo de Imóvel")
        c_tipo_arm = col(df, "TIPO ARMADILHA")
        c_lat = col(df, "LATITUDE")
        c_lon = col(df, "LONGITUDE")

        objs = []
        for _, r in df.iterrows():
            lt, ln = r.get(c_lat), r.get(c_lon)
            if pd.isna(lt): continue
            
            num_v = _get_str(r, c_num, 50)
            h = hashlib.sha256(f"ARM|{num_v}|{ln}".encode()).hexdigest()
            
            objs.append(ArmadilhaTemp(
                hash_registro=h,
                numero=num_v,
                municipio=_get_str(r, c_mun, 100),
                localidade=_get_str(r, c_loc, 100),
                endereco=_get_str(r, c_end, 150),
                complemento=_get_str(r, c_comp, 225, ""),
                quarteiroes=_get_str(r, c_quart, 50),
                tipo_imovel=_get_str(r, c_tipo_im, 50),
                tipo_armadilha=_get_str(r, c_tipo_arm, 50),
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