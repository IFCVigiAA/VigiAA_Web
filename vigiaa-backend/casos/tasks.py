import os
import pandas as pd
import numpy as np
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

# --- NORMALIZAÇÃO ---
def _normalize(s):
    if not s: return ""
    s = str(s).strip().upper()
    s = unicodedata.normalize("NFKD", s).encode("ASCII", "ignore").decode("ASCII")
    return " ".join(s.split())

# 🔥 COL AGORA MUITO MAIS INTELIGENTE
def col(df, *nomes):
    cols_norm = {_normalize(c): c for c in df.columns}

    for n in nomes:
        n_norm = _normalize(n)

        # match exato
        if n_norm in cols_norm:
            return cols_norm[n_norm]

        # match parcial forte
        for c_norm, c_real in cols_norm.items():
            if n_norm in c_norm or c_norm in n_norm:
                return c_real

    return None

# 🔥 MELHORADO: não mascarar erro silencioso
def _get_val(r, col_name, default="ND"):
    if not col_name:
        return default

    val = r.get(col_name)

    if pd.isna(val):
        return default

    val = str(val).strip()

    if not val or val.upper() in ["NAN", "NONE"]:
        return default

    return val

def _get_int(r, col_name):
    if not col_name:
        return 0
    val = r.get(col_name)
    if pd.isna(val):
        return 0
    try:
        return int(float(val))
    except:
        return 0

def fix_date(val):
    if pd.isna(val) or val is pd.NaT:
        return None
    try:
        return pd.to_datetime(val).date()
    except:
        return None

def corrigir_datas_mistas(serie):
    numeros_excel = pd.to_numeric(serie, errors='coerce')
    datas_dos_numeros = pd.to_datetime(numeros_excel, unit='D', origin='1899-12-30')
    textos_puros = serie.where(numeros_excel.isna(), pd.NaT)
    datas_dos_textos = pd.to_datetime(textos_puros, errors='coerce', dayfirst=True)
    return datas_dos_textos.fillna(datas_dos_numeros)

# --- GEO ---
def _geo_limpa(endereco, bairro):
    try:
        query = f"{endereco}, {bairro}, CAMBORIÚ, SC, BRASIL"
        g = geocoder.arcgis(query, timeout=5)
        if g.ok and g.latlng:
            return g.latlng
    except:
        pass
    return (-27.022986, -48.652135)

# ---------------- POSITIVOS ----------------
@shared_task(bind=True)
def task_processar_positivos(self, job_id, arquivo_path):
    try:
        log = LogSincronizacao.objects.get(id=job_id)
        df = pd.read_excel(arquivo_path)

        c_nome = col(df, "NOME")
        c_end = col(df, "ENDEREÇO", "ENDERECO")
        c_bairro = col(df, "BAIRRO")
        c_ini = col(df, "INÍCIO SINTOMAS")
        c_nasc = col(df, "DATA DE NASCIMENTO")
        c_sinan = col(df, "SINAN")

        if c_ini: df[c_ini] = corrigir_datas_mistas(df[c_ini]).ffill()
        if c_nasc: df[c_nasc] = corrigir_datas_mistas(df[c_nasc])

        df = df.dropna(subset=[c_nome]) if c_nome else df

        params_temp = []
        params_gl = []

        for _, r in df.iterrows():
            nome = _get_val(r, c_nome, "NÃO INFORMADO")
            endereco = _get_val(r, c_end, "NÃO INFORMADO")
            bairro = _get_val(r, c_bairro, "ND")

            lat, lon = _geo_limpa(endereco, bairro)

            h = hashlib.sha256(f"{nome}|{_get_val(r, c_nasc)}|{_get_val(r, c_ini)}".encode()).hexdigest()

            base = (
                h, nome, endereco,
                _get_val(r, col(df, "LOCAL DE ATENDIMENTO")),
                fix_date(r.get(c_ini)),
                fix_date(r.get(col(df, "NOTIFICAÇÃO"))),
                _get_int(r, c_sinan) or None,
                bairro,
                fix_date(r.get(c_nasc)),
                _get_val(r, col(df, "OBSERVAÇÕES"), ""),
                _get_val(r, col(df, "RESULTADO"), ""),
                _get_val(r, col(df, "SITUAÇÃO"), "")
            )

            params_temp.append(base)
            params_gl.append(base + (f"POINT({lon} {lat})",))

        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM casos_positivos_temp")
                cursor.execute("DELETE FROM casos_positivos_temp_gl")

                cursor.executemany("""
                    INSERT INTO casos_positivos_temp 
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """, params_temp)

                cursor.executemany("""
                    INSERT INTO casos_positivos_temp_gl 
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,ST_GeomFromText(%s,4674))
                """, params_gl)

        log.status = "finalizado"
        log.progresso = 100
        log.save()

    except Exception as e:
        LogSincronizacao.objects.filter(id=job_id).update(status="erro", mensagem=str(e))
    finally:
        if os.path.exists(arquivo_path):
            os.remove(arquivo_path)

# ---------------- FOCOS ----------------
@shared_task(bind=True)
def task_processar_focos(self, job_id, arquivo_path):
    try:
        log = LogSincronizacao.objects.get(id=job_id)

        df_raw = pd.read_excel(arquivo_path, header=None)
        skip = 0

        for i, row in df_raw.iterrows():
            if any("FOCO" in _normalize(str(x)) for x in row.values):
                skip = i
                break

        df = pd.read_excel(arquivo_path, skiprows=skip)

        c_nf = col(df, "N FOCO", "Nº FOCO")
        c_lat = col(df, "LATITUDE")
        c_lon = col(df, "LONGITUDE")

        objs = []

        for _, r in df.iterrows():
            nf = _get_val(r, c_nf, None)
            if not nf:
                continue

            lat, lon = r.get(c_lat), r.get(c_lon)
            if pd.isna(lat):
                continue

            objs.append(FocoTemp(
                hash_registro=hashlib.sha256(f"FOCO|{nf}|{lat}".encode()).hexdigest(),
                n_foco=nf,
                municipio="CAMBORIÚ",
                localidade=_get_val(r, col(df, "LOCALIDADE")),
                rua_numero=_get_val(r, col(df, "RUA/NÚMERO", "RUA/NUMERO")),
                geometry=Point(float(lon), float(lat), srid=4674),
                latitude=float(lat),
                longitude=float(lon)
            ))

        with transaction.atomic():
            FocoTemp.objects.all().delete()
            if objs:
                FocoTemp.objects.bulk_create(objs, ignore_conflicts=True)

        log.status = "finalizado"
        log.progresso = 100
        log.save()

    except Exception as e:
        LogSincronizacao.objects.filter(id=job_id).update(status="erro", mensagem=str(e))
    finally:
        if os.path.exists(arquivo_path):
            os.remove(arquivo_path)

# ---------------- PONTOS ----------------
@shared_task(bind=True)
def task_processar_pontos(self, job_id, arquivo_path):
    try:
        log = LogSincronizacao.objects.get(id=job_id)

        df = pd.read_excel(arquivo_path, header=3)

        # 🔥 CORREÇÃO PRINCIPAL
        df.columns = [_normalize(c) for c in df.columns]

        c_num = col(df, "NUMERO")
        c_mun = col(df, "MUNICIPIO")
        c_loc = col(df, "LOCALIDADE")
        c_end = col(df, "ENDERECO")
        c_qua = col(df, "QUARTEIROES")
        c_com = col(df, "COMPLEMENTO")
        c_lat = col(df, "LATITUDE")
        c_lon = col(df, "LONGITUDE")

        objs = []

        for _, r in df.iterrows():
            lat, lon = r.get(c_lat), r.get(c_lon)
            if pd.isna(lat) or pd.isna(lon):
                continue

            numero = _get_val(r, c_num, "S/N")

            objs.append(PontoEstrategicoTemp(
                hash_registro=hashlib.sha256(f"PONTO|{numero}|{lat}".encode()).hexdigest(),
                numero=numero,
                municipio=_get_val(r, c_mun, "CAMBORIÚ"),
                localidade=_get_val(r, c_loc),
                endereco=_get_val(r, c_end),
                quarteiroes=_get_val(r, c_qua),
                complemento=_get_val(r, c_com),
                geometry=Point(float(lon), float(lat), srid=4674),
                latitude=float(lat),
                longitude=float(lon)
            ))

        with transaction.atomic():
            PontoEstrategicoTemp.objects.all().delete()
            if objs:
                PontoEstrategicoTemp.objects.bulk_create(objs, ignore_conflicts=True)

        log.status = "finalizado"
        log.progresso = 100
        log.save()

    except Exception as e:
        LogSincronizacao.objects.filter(id=job_id).update(status="erro", mensagem=str(e))
    finally:
        if os.path.exists(arquivo_path):
            os.remove(arquivo_path)

# ---------------- ARMADILHAS ----------------
@shared_task(bind=True)
def task_processar_armadilhas(self, job_id, arquivo_path):
    try:
        log = LogSincronizacao.objects.get(id=job_id)

        df = pd.read_excel(arquivo_path, header=3)

        c_num = col(df, "NUMERO", "NÚMERO")
        c_lat = col(df, "LATITUDE")
        c_lon = col(df, "LONGITUDE")

        objs = []

        for _, r in df.iterrows():
            lat, lon = r.get(c_lat), r.get(c_lon)
            if pd.isna(lat):
                continue

            num = _get_val(r, c_num, "S/N")

            objs.append(ArmadilhaTemp(
                hash_registro=hashlib.sha256(f"ARM|{num}|{lat}".encode()).hexdigest(),
                numero=num,
                municipio=_get_val(r, col(df, "MUNICIPIO")),
                localidade=_get_val(r, col(df, "LOCALIDADE")),
                endereco=_get_val(r, col(df, "ENDERECO")),
                complemento=_get_val(r, col(df, "COMPLEMENTO")),
                quarteiroes=_get_val(r, col(df, "QUARTEIROES")),
                tipo_imovel=_get_val(r, col(df, "TIPO IMOVEL")),
                tipo_armadilha=_get_val(r, col(df, "TIPO ARMADILHA")),
                geometry=Point(float(lon), float(lat), srid=4674),
                latitude=float(lat),
                longitude=float(lon)
            ))

        with transaction.atomic():
            ArmadilhaTemp.objects.all().delete()
            ArmadilhaTemp.objects.bulk_create(objs, ignore_conflicts=True)

        log.status = "finalizado"
        log.progresso = 100
        log.save()

    except Exception as e:
        LogSincronizacao.objects.filter(id=job_id).update(status="erro", mensagem=str(e))
    finally:
        if os.path.exists(arquivo_path):
            os.remove(arquivo_path)