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

# --- 1. REGRAS DE NEGÓCIO E CORREÇÕES ---
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
    "RIO SENA":"RUA RIO SENNA",
    "LEANDRO BERTOLDI - ": "RUA LEANDRO BERTOLDI",
    "RUA LEANDRO BERTOLDISN": "RUA LEANDRO BERTOLDI",
    "RUA FRANCISCO GARCIA , 961 CENTRO": "RUA FRANCISCO GARCIA, 961",
    "RUA JOÃO MORAES, 4590": "RUA JOÃO MORAES",
    "RUA TEREZA EVANGELISTA GONÇALVES, 360, TABULEIRO": "RUA TEREZA EVANGELISTA GONÇALVES, TABULEIRO",
    "RUA IJUI": "RUA RIO IJUÍ",
    "RUA SANTA CECILIA, 504": "RUA SANTA CECÍLIA",    
    "RUA SAMARINO, 414, SANTA REGINA, CAMBORIU": "RUA SAN MARINO, 414, SANTA REGINA, CAMBORIU"
}

COORDS_FIXAS = {
    "RUA SÃO BRÁS": (-27.0246740, -48.6405868),
    "JOSÉ BERNARDES PASSOS": (-27.0307410, -48.6461234),
    "FINLANDIA": (-27.0367205, -48.6751566),
    "RUA RIO SOLIMOES": (-27.0323908, -48.6451871),
    "BR 101 KM 532 MARGINAL, TABULEIRO, CAMBORIÚ":(-26.999199,-48.647584),
    "RODOVIA BR 101": (-26.999199,-48.647584),
    "RUA MONTE ALEGRE": (-27.001054,-48.661927),
    "RUA JURI SILVA": (-27.0307275,-48.6497894)
}

# --- 2. UTILS ---
def _get_str(r, col_name, max_len=100, default="ND"):
    val = r.get(col_name)
    if pd.isna(val) or val is None: return default
    return str(val).strip()[:max_len]

def _get_int(r, col_name):
    val = r.get(col_name)
    if pd.isna(val) or val is None: return 0
    try: return int(float(val))
    except: return 0

# --- 3. TASKS ---

@shared_task(bind=True)
def task_processar_positivos(self, job_id, arquivo_path):
    try:
        log = LogSincronizacao.objects.get(id=job_id)
        df = pd.read_excel(arquivo_path)
        log.status = "finalizado"; log.save()
    except Exception as e:
        LogSincronizacao.objects.filter(id=job_id).update(status="erro", mensagem=str(e))

@shared_task(bind=True)
def task_processar_focos(self, job_id, arquivo_path):
    try:
        log = LogSincronizacao.objects.get(id=job_id)
        
        # LER SEM CABEÇALHO PARA ESCANEAR ONDE ESTÁ A TABELA
        df_raw = pd.read_excel(arquivo_path, header=None)
        
        skip_index = None
        for i, row in df_raw.iterrows():
            # Procura por "Nº FOCO" ou "N FOCO" em qualquer lugar da linha
            row_str = " ".join([str(x).upper() for x in row.values if pd.notna(x)])
            if "Nº FOCO" in row_str or "N FOCO" in row_str:
                skip_index = i
                break
        
        if skip_index is None:
            raise Exception("Não encontrei o cabeçalho 'Nº Foco' na planilha.")

        # Recarrega o DataFrame a partir da linha correta
        df = pd.read_excel(arquivo_path, skiprows=skip_index)
        
        # Limpar nomes das colunas
        df.columns = [str(c).strip().upper() for c in df.columns]

        objs = []
        for _, r in df.iterrows():
            nf_val = r.get('Nº FOCO') or r.get('N FOCO')
            
            # Se a linha não tem número de foco, ignora (fim da tabela ou linha vazia)
            if pd.isna(nf_val) or str(nf_val).strip() == "":
                continue
            
            lat = r.get('LATITUDE')
            lon = r.get('LONGITUDE')
            
            # Se não tem coordenada, usa Camboriú central como fallback para não perder o registro
            try:
                lat_f = float(lat) if pd.notna(lat) else -27.022986
                lon_f = float(lon) if pd.notna(lon) else -48.652135
            except:
                lat_f, lon_f = -27.022986, -48.652135

            h = hashlib.sha256(f"FOCO|{nf_val}|{lat_f}|{lon_f}".encode()).hexdigest()
            
            objs.append(FocoTemp(
                hash_registro=h,
                n_foco=str(nf_val)[:30],
                regional=_get_str(r, 'REGIONAL', 100),
                municipio=_get_str(r, 'MUNICÍPIO', 100),
                localidade=_get_str(r, 'LOCALIDADE', 100),
                rua_numero=_get_str(r, 'RUA/NÚMERO', 200),
                complemento=_get_str(r, 'COMPLEMENTO', 255),
                quarteirao=_get_str(r, 'QUARTEIRÃO', 50),
                imovel=_get_str(r, 'IMÓVEL', 50),
                deposito=_get_str(r, 'DEPÓSITO', 100),
                tipo_atividade=_get_str(r, 'TIPO DE ATIVIDADE', 50),
                data_coleta=pd.to_datetime(r.get('DATA DA COLETA'), errors='coerce'),
                data_entrada=pd.to_datetime(r.get('DATA DE ENTRADA'), errors='coerce'),
                data_exame=pd.to_datetime(r.get('DATA DO EXAME'), errors='coerce'),
                a_aegypti_form_aquaticas=_get_int(r, 'A. AEGYPTI FORMAS AQUÁTICAS'),
                a_aegypti_form_adultas=_get_int(r, 'A. AEGYPTI FORMAS ADULTAS'),
                a_albopictus_form_aquaticas=_get_int(r, 'A. ALBOPICTUS FORMAS AQUÁTICAS'),
                a_albopictus_form_adultas=_get_int(r, 'A. ALBOPICTUS FORMAS ADULTAS'),
                ovo_a_aegypti=_get_int(r, 'OVO A. AEGYPTI'),
                latitude=lat_f,
                longitude=lon_f,
                geometry=Point(lon_f, lat_f, srid=4674)
            ))

        with transaction.atomic():
            FocoTemp.objects.all().delete()
            if objs:
                FocoTemp.objects.bulk_create(objs, ignore_conflicts=True)
            
        log.status = "finalizado"
        log.progresso = 100
        log.mensagem = f"Sucesso: {len(objs)} focos processados."
        log.save()

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
        df.columns = [str(c).strip().upper() for c in df.columns]
        objs = []
        for _, r in df.iterrows():
            lat, lon = r.get('LATITUDE'), r.get('LONGITUDE')
            if pd.isna(lat): continue
            num = r.get('NUMERO') or r.get('NÚMERO')
            h = hashlib.sha256(f"PONTO|{num}|{lat}".encode()).hexdigest()
            objs.append(PontoEstrategicoTemp(hash_registro=h, numero=str(num), localidade=_get_str(r, 'LOCALIDADE'), endereco=_get_str(r, 'ENDERECO'), complemento=_get_str(r, 'COMPLEMENTO'), geometry=Point(float(lon), float(lat), srid=4674), latitude=float(lat), longitude=float(lon)))
        with transaction.atomic():
            PontoEstrategicoTemp.objects.all().delete()
            PontoEstrategicoTemp.objects.bulk_create(objs, ignore_conflicts=True)
        log.status, log.progresso = "finalizado", 100; log.save()
    except Exception as e:
        LogSincronizacao.objects.filter(id=job_id).update(status="erro", mensagem=str(e))
    finally:
        if os.path.exists(arquivo_path): os.remove(arquivo_path)

@shared_task(bind=True)
def task_processar_armadilhas(self, job_id, arquivo_path):
    try:
        log = LogSincronizacao.objects.get(id=job_id)
        df = pd.read_excel(arquivo_path, header=3)
        df.columns = [str(c).strip().upper() for c in df.columns]
        objs = []
        for _, r in df.iterrows():
            lat, lon = r.get('LATITUDE'), r.get('LONGITUDE')
            if pd.isna(lat): continue
            num = r.get('NUMERO') or r.get('NÚMERO')
            h = hashlib.sha256(f"ARM|{num}|{lon}".encode()).hexdigest()
            objs.append(ArmadilhaTemp(hash_registro=h, numero=str(num), localidade=_get_str(r, 'LOCALIDADE'), complemento=_get_str(r, 'COMPLEMENTO'), tipo_imovel=_get_str(r, 'TIPO IMOVEL'), tipo_armadilha=_get_str(r, 'TIPO ARMADILHA'), geometry=Point(float(lon), float(lat), srid=4674), latitude=float(lat), longitude=float(lon)))
        with transaction.atomic():
            ArmadilhaTemp.objects.all().delete()
            ArmadilhaTemp.objects.bulk_create(objs, ignore_conflicts=True)
        log.status, log.progresso = "finalizado", 100; log.save()
    except Exception as e:
        LogSincronizacao.objects.filter(id=job_id).update(status="erro", mensagem=str(e))
    finally:
        if os.path.exists(arquivo_path): os.remove(arquivo_path)