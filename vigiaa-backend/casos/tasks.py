import os
import re
import json
import logging
import unicodedata
import difflib
import pandas as pd
import geocoder
import calendar
from datetime import datetime
from django.utils import timezone
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

    for erro, correto in CORRECOES_ENDERECO.items():
        if erro.upper() in rua_tabela:
            rua_tabela = rua_tabela.replace(erro.upper(), correto.upper())

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
# GEOCODIFICAÇÃO EM CASCATA
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

    if bairro_str and bairro_str != "NAN":
        for chave_bairro, coords_bairro in CENTROIDES_BAIRROS.items():
            if chave_bairro in bairro_str:
                return coords_bairro[0], coords_bairro[1]

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


    return CENTRO_MAPA_CAMBORIU[0], CENTRO_MAPA_CAMBORIU[1]

# ==============================================================================
# 1. TASK CASOS POSITIVOS
# ==============================================================================

@shared_task(bind=True)
def task_processar_positivos(
    self,
    job_id,
    arquivo_path,
    celula_cabecalho=None,
    mapeamento_customizado=None,
):
  try:
    log = LogSincronizacao.objects.get(id=job_id)
    log.status = 'processando'
    log.progresso = 0
    log.mensagem = 'Lendo e preparando planilha...'
    log.save(update_fields=['status', 'progresso', 'mensagem'])

    erros = ErrorLogger()

    _, ext = os.path.splitext(arquivo_path)
    ext = ext.lower()
    engine = 'odf' if ext == '.ods' else ('xlrd' if ext == '.xls' else 'openpyxl')

    if isinstance(mapeamento_customizado, str):
      try:
        mapeamento_customizado = json.loads(mapeamento_customizado)
      except Exception:
        mapeamento_customizado = None

    df_raw = pd.read_excel(
        arquivo_path,
        header=None,
        nrows=20,
        engine=engine,
        keep_default_na=False,
    )

    h_idx = None
    if celula_cabecalho:
      match = re.search(r'\d+', str(celula_cabecalho))
      if match:
        h_idx = max(0, int(match.group()) - 1)

    if h_idx is None:
      TERMOS_RECONHECIDOS = {
          'notificação',
          'notificacao',
          'sinan',
          'sintomas',
          'resultado',
          'situacao',
          'bairro',
          'endereco',
          'sexo',
          'nascimento',
          'nome',
      }
      melhor_linha, max_matches = 0, 0
      for i, row in df_raw.iterrows():
        valores_linha = set(
            str(v).strip().lower() for v in row.values if pd.notna(v)
        )
        matches = len(valores_linha.intersection(TERMOS_RECONHECIDOS))
        if matches > max_matches:
          max_matches = matches
          melhor_linha = i
      h_idx = melhor_linha if max_matches >= 2 else 3

    df = pd.read_excel(arquivo_path, header=h_idx, engine=engine).dropna(
        how='all'
    )
    df.columns = [str(c).replace('\n', ' ').strip() for c in df.columns]

    if not df.empty:
      primeira_coluna = df.columns[0]
      df = df[
          ~df[primeira_coluna]
          .astype(str)
          .str.upper()
          .str.contains('TOTAL', na=False)
      ]

    DE_PARA_PADRAO = {
        'local_atendimento': 'LOCAL NOTIFICAÇÃO',
        'notificacao': 'DATA NOT.',
        'inicio_sintomas': 'INICIO SINTOMAS',
        'sinan': 'SINAN',
        'nome': 'NOME COMPLETO',
        'data_nasc': 'NASCIMENTO',
        'sexo': 'SEXO',
        'endereco': 'ENDEREÇO COMPLETO',
        'bairro': 'BAIRRO',
        'resultado': 'RESULTADO',
        'situacao': 'SITUAÇÃO',
        'observacoes': 'OBSERVAÇÃO',
        'latitude': 'LATITUDE',
        'longitude': 'LONGITUDE',
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

    # Identifica colunas de Endereço e Bairro de forma flexível
    col_end_nome = DE_PARA.get('endereco')
    if not col_end_nome or col_end_nome not in df.columns:
      for c in df.columns:
        if 'ENDERE' in c.upper():
          col_end_nome = c
          break

    col_bairro_nome = DE_PARA.get('bairro')
    if not col_bairro_nome or col_bairro_nome not in df.columns:
      for c in df.columns:
        if 'BAIRRO' in c.upper():
          col_bairro_nome = c
          break

    campos_db = [
        'local_atendimento',
        'notificacao',
        'inicio_sintomas',
        'sinan',
        'nome',
        'data_nasc',
        'sexo',
        'endereco',
        'bairro',
        'resultado',
        'situacao',
        'observacoes',
    ]

    total_registros = len(df)
    if total_registros == 0:
      log.status = 'erro'
      log.mensagem = 'Nenhum caso positivo válido encontrado.'
      log.save(update_fields=['status', 'mensagem'])
      return

    registros = []

    for current_idx, (idx, r) in enumerate(df.iterrows(), start=1):
      # Garante inicialização prévia segura das variáveis textuais de endereço
      end_val = r.get(col_end_nome) if col_end_nome else ''
      bairro_val = r.get(col_bairro_nome) if col_bairro_nome else ''

      end_str = str(end_val).strip() if pd.notna(end_val) else ''
      bairro_str = str(bairro_val).strip() if pd.notna(bairro_val) else ''

      lt = r.get(col_lat) if col_lat and col_lat in df.columns else None
      ln = r.get(col_lng) if col_lng and col_lng in df.columns else None

      lat_val, lon_val = None, None
      if (
          pd.notna(lt)
          and pd.notna(ln)
          and str(lt).strip() not in ['None', 'nan', '0', '']
          and str(ln).strip() not in ['None', 'nan', '0', '']
      ):
        try:
          lat_val = float(str(lt).replace(',', '.'))
          lon_val = float(str(ln).replace(',', '.'))
        except (ValueError, TypeError):
          pass

      # Executa a geocodificação em cascata se as coordenadas forem nulas
      if lat_val is None or lon_val is None:
        lat_arc, lon_arc = _geocodificar_cascata(end_str, bairro_str)
        lat_val = lat_arc if lat_arc is not None else -27.0258
        lon_val = lon_arc if lon_arc is not None else -48.6542

      valores = []
      for campo_bd in campos_db:
        coluna_planilha = DE_PARA.get(campo_bd)

        if campo_bd == 'endereco' and (
            not coluna_planilha or coluna_planilha not in df.columns
        ):
          coluna_planilha = col_end_nome
        elif campo_bd == 'bairro' and (
            not coluna_planilha or coluna_planilha not in df.columns
        ):
          coluna_planilha = col_bairro_nome

        if coluna_planilha and coluna_planilha in df.columns:
          val = r.get(coluna_planilha)
          if campo_bd in ['inicio_sintomas', 'notificacao', 'data_nasc']:
            valores.append(_parse_data_segura(val))
          elif campo_bd == 'sinan':
            val_num = pd.to_numeric(val, errors='coerce')
            valores.append(None if pd.isna(val_num) else int(val_num))
          else:
            valores.append(
                None
                if (
                    pd.isna(val)
                    or str(val).strip().upper() in ['NAN', 'NONE', 'NAT', 'NULL', '']
                )
                else str(val).strip()
            )
        else:
          valores.append(None)

      lat_str = str(lat_val) if lat_val is not None else None
      lon_str = str(lon_val) if lon_val is not None else None

      valores.extend([lat_str, lon_str, lon_val, lat_val])
      registros.append(valores)

      # Atualiza o progresso no banco
      if current_idx % 2 == 0 or current_idx == total_registros:
        pct = int((current_idx / total_registros) * 100)
        log.progresso = min(pct, 99)
        log.mensagem = (
            f'Geoprocessando e importando... {current_idx}/{total_registros}'
            f' registros ({pct}%)'
        )
        log.save(update_fields=['progresso', 'mensagem'])

    query = """
            INSERT INTO casos_positivos_temp_gl (
                local_atendimento, notificacao, inicio_sintomas, sinan,
                nome, data_nasc, sexo, endereco, bairro,
                resultado, situacao, observacoes, latitude, longitude, geometry
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                ST_SetSRID(ST_MakePoint(%s::double precision, %s::double precision), 4674)
            )
            ON CONFLICT DO NOTHING
        """

    with transaction.atomic():
      with connection.cursor() as cursor:
        cursor.executemany(query, registros)

    log.status = 'finalizado'
    log.progresso = 100
    log.mensagem = (
        f'Sucesso! {len(registros)} casos positivos processados e acumulados.'
    )
    log.save(update_fields=['status', 'progresso', 'mensagem'])

  except Exception as e:
    LogSincronizacao.objects.filter(id=job_id).update(
        status='erro', mensagem=str(e)
    )
  finally:
    if os.path.exists(arquivo_path):
      try:
        os.remove(arquivo_path)
      except Exception:
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

                if r.get('latitude') and r.get('longitude'):
                    try:
                        lat = float(str(r.get('latitude')).replace(',', '.'))
                        lon = float(str(r.get('longitude')).replace(',', '.'))
                    except (ValueError, TypeError):
                        lat, lon = None, None

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
# AUXILIAR: CORREÇÃO INTELIGENTE DE ESCALA DE COORDENADAS 
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

    if ',' in texto:
        partes = texto.rsplit(',', 1)
        rua_candidata = partes[0].strip()
        sufixo = partes[1].strip()

        match_num = re.search(r'^(?:N[º°\.]?\s*|NUM[º°\.]?\s*)?(\d+[\w\-\/]*|S/?N|SEM N[UÚ]MERO)\b', sufixo, re.IGNORECASE)
        if match_num:
            return rua_candidata, match_num.group(1).upper()[:10]

    if re.search(r'\b(S/?N|SEM N[UÚ]MERO)\b', texto, re.IGNORECASE):
        rua_limpa = re.sub(r'[,.\-]?\s*\b(S/?N|SEM N[UÚ]MERO)\b', '', texto, flags=re.IGNORECASE).strip(' ,-')
        return (rua_limpa if rua_limpa else texto), 'S/N'

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
        while abs(val) > limite_global or (abs(referencia) > 0 and abs(val) > abs(referencia) * 5):
            val /= 10.0
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

        # DE_PARA contendo apenas colunas físicas reais da tabela
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
            'a_aegypti_form_adultas': 'A. AEGYPTI FORMAS ADULTAS',
            'a_albopictus_form_aquaticas': 'A. ALBOPICTUS FORMAS AQUÁTICAS',
            'a_albopictus_form_adultas': 'A. ALBOPICTUS FORMAS ADULTAS',
            'ovo_a_aegypti': 'A. AEGYPTI OVOS',
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
                
                is_contagem = any(term in campo_bd for term in ['aquaticas', 'adultas', 'ovo'])

                if coluna_planilha and coluna_planilha in df.columns:
                    val = r.get(coluna_planilha)

                    if campo_bd in ['data_coleta', 'data_entrada', 'data_exame']:
                        valores.append(_parse_data_segura(val))
                    elif is_contagem:
                        val_num = pd.to_numeric(val, errors='coerce')
                        valores.append(0 if pd.isna(val_num) else int(val_num))
                    else:
                        valores.append(None if (pd.isna(val) or str(val).strip().upper() in ['NAN', 'NONE', 'NAT', '']) else str(val).strip())
                else:
                    if is_contagem:
                        valores.append(0)  # Evita NULL em colunas numéricas NOT NULL
                    else:
                        valores.append(None)

            registros.append(valores)

        if not registros:
            log.status = "erro"
            log.mensagem = "Nenhum foco válido encontrado. Verifique as colunas de Latitude e Longitude."
            log.save()
            return

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
                'pe', 'n_pe', 'numero', 'regional', 'municipio', 'bairro', 'endereco',
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

        # Mapeamento completo batendo com os cabeçalhos da imagem
        DE_PARA_PADRAO = {
            'numero': 'Nº PE',
            'regional': 'REGIONAL',
            'municipio': 'MUNICÍPIO',
            'localidade': 'BAIRRO',
            'endereco': 'ENDEREÇO',
            'complemento': 'COMPLEMENTO',
            'quarteiroes': 'QUARTEIRÃO',
            'imovel': 'IMÓVEL',
            'deposito': 'DEPÓSITO',
            'tp_atividade': 'TIPO DE ATIVIDADE',
            'data_coleta': 'DATA DA COLETA',
            'data_entrada': 'DATA DE ENTRADA',
            'data_exame': 'DATA DO EXAME',
            'aegypti_aquaticas': 'A. AEGYPTI FORMAS AQUÁTICAS',
            'albopictus_aquaticas': 'A. ALBOPICTUS FORMAS AQUÁTICAS',
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
                    elif campo_bd in ['aegypti_aquaticas', 'albopictus_aquaticas']:
                        val_num = pd.to_numeric(val, errors='coerce')
                        valores_finais.append(0 if pd.isna(val_num) else int(val_num))
                    elif campo_bd == 'municipio':
                        # Fallback defensivo NOT NULL
                        v_str = str(val).strip() if pd.notna(val) else ""
                        valores_finais.append(v_str if v_str and v_str.upper() not in ['NAN', 'NONE', 'NULL'] else "CAMBORIÚ")
                    elif campo_bd == 'numero':
                        v_str = str(val).strip() if pd.notna(val) else ""
                        if v_str.endswith('.0'):
                            v_str = v_str[:-2]
                        valores_finais.append(v_str if v_str and v_str.upper() not in ['NAN', 'NONE', 'NULL'] else None)
                    else:
                        valores_finais.append(None if (pd.isna(val) or str(val).strip().upper() in ['NAN', 'NONE', 'NAT', '']) else str(val).strip())
                else:
                    if campo_bd in ['aegypti_aquaticas', 'albopictus_aquaticas']:
                        valores_finais.append(0)
                    elif campo_bd == 'municipio':
                        valores_finais.append("CAMBORIÚ")
                    else:
                        valores_finais.append(None)

            registros.append(valores_finais)

        if not registros:
            log.status = "erro"
            log.mensagem = "Nenhum ponto estratégico válido encontrado. Verifique as colunas de Latitude e Longitude."
            log.save()
            return



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

import calendar
from datetime import datetime
import json
import os
import re
from celery import shared_task
from django.db import connection, transaction
import pandas as pd


def _extrair_data_ultimo_dia_mes(nome_arquivo):
  """Extrai mês e ano do nome do arquivo e retorna a data do último dia do mês."""
  agora = datetime.now()
  mes, ano = None, agora.year
  nome_clean = nome_arquivo.lower()

  meses_extenso = {
      'janeiro': 1,
      'jan': 1,
      'fevereiro': 2,
      'fev': 2,
      'marco': 3,
      'mar': 3,
      'março': 3,
      'abril': 4,
      'abr': 4,
      'maio': 5,
      'mai': 5,
      'junho': 6,
      'jun': 6,
      'julho': 7,
      'jul': 7,
      'agosto': 8,
      'ago': 8,
      'setembro': 9,
      'set': 9,
      'outubro': 10,
      'out': 10,
      'novembro': 11,
      'nov': 11,
      'dezembro': 12,
      'dez': 12,
  }

  match_ano = re.search(r'20\d{2}', nome_clean)
  if match_ano:
    ano = int(match_ano.group())

  for nome_m, num_m in meses_extenso.items():
    if nome_m in nome_clean:
      mes = num_m
      break

  if not mes:
    match_mes = re.search(r'(?:^|[^\d])(0[1-9]|1[0-2])(?:[^\d]|$)', nome_clean)
    if match_mes:
      mes = int(match_mes.group(1))

  if not mes:
    mes = agora.month - 1 if agora.month > 1 else 12
    if mes == 12:
      ano -= 1

  ultimo_dia = calendar.monthrange(ano, mes)[1]
  return datetime(ano, mes, ultimo_dia).date()

# ==============================================================================
# 6. TASK OVITRAMPAS
# ==============================================================================

@shared_task(bind=True)
def task_processar_ovitrampas(
    self,
    job_id,
    arquivo_path,
    celula_cabecalho=None,
    mapeamento_customizado=None,
):
  try:
    log = LogSincronizacao.objects.get(id=job_id)
    erros = ErrorLogger()

    nome_arquivo = os.path.basename(arquivo_path)
    data_fallback_mes = _extrair_data_ultimo_dia_mes(nome_arquivo)

    _, ext = os.path.splitext(arquivo_path)
    ext = ext.lower()
    engine = 'odf' if ext == '.ods' else ('xlrd' if ext == '.xls' else 'openpyxl')

    if isinstance(mapeamento_customizado, str):
      try:
        mapeamento_customizado = json.loads(mapeamento_customizado)
      except Exception:
        mapeamento_customizado = None

    df_raw = pd.read_excel(
        arquivo_path,
        header=None,
        nrows=30,
        engine=engine,
        keep_default_na=False,
    )

    h_idx = None
    if celula_cabecalho:
      match = re.search(r'\d+', str(celula_cabecalho))
      if match:
        h_idx = max(0, int(match.group()) - 1)

    if h_idx is None:
      TERMOS_RECONHECIDOS = {
          'ovitrampa',
          'id_ovitrampa',
          'n_ovitrampa',
          'endereco',
          'bairro',
          'exame',
          'coleta',
          'ovos',
          'aegypti',
          'albopictus',
          'latitude',
          'longitude',
      }

      melhor_linha, max_matches = 0, 0
      for i, row in df_raw.iterrows():
        valores_linha = set(
            str(v).strip().lower() for v in row.values if str(v).strip() != ''
        )
        matches = len(valores_linha.intersection(TERMOS_RECONHECIDOS))
        if matches > max_matches:
          max_matches = matches
          melhor_linha = i

      h_idx = melhor_linha if max_matches >= 2 else 0

    df = pd.read_excel(
        arquivo_path, header=h_idx, engine=engine, keep_default_na=False
    ).dropna(how='all')
    df.columns = [str(c).replace('\n', ' ').strip() for c in df.columns]

    if not df.empty:
      primeira_coluna = df.columns[0]
      df = df[
          ~df[primeira_coluna]
          .astype(str)
          .str.upper()
          .str.contains('TOTAL', na=False)
      ]

    DE_PARA_PADRAO = {
        'id_ovitrampa': 'ID / N. Ovitrampa',
        'endereco': 'Endereço',
        'numero': 'Número do Logradouro',
        'complemento_tipo': 'Complemento / Tipo Imóvel',
        'bairro': 'Bairro',
        'localizacao': 'Localização da Ovitrampa',
        'setor_distrito': 'Setor / Distrito',
        'responsavel': 'Responsável',
        'quarteirao': 'Quarteirão',
        'data_exame': 'Data do Exame',
        'ovos_aegypti': 'Ovo A. Aegypti',
        'ovos_albopictus': 'Ovo A. Albopictus',
        'outros_ovos': 'Outros Ovos',
        'tipo': 'Tipo',
        'latitude': 'Latitude',
        'longitude': 'Longitude',
        'acoes': 'Ações (BRI, UBV e Outras)',
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
      col_id = DE_PARA.get('id_ovitrampa')
      val_id_raw = r.get(col_id) if col_id and col_id in df.columns else None

      if pd.isna(val_id_raw) or str(val_id_raw).strip().upper() in [
          'NAN',
          'NONE',
          'NAT',
          'NULL',
          '',
      ]:
        continue

      id_str = str(val_id_raw).strip()
      if id_str.endswith('.0'):
        id_str = id_str[:-2]

      valores = []
      for campo_bd in campos_sql:
        coluna_planilha = DE_PARA.get(campo_bd)
        val = (
            r.get(coluna_planilha)
            if coluna_planilha and coluna_planilha in df.columns
            else None
        )
        val_str = str(val).strip() if val is not None else ''
        val_upper = val_str.upper()

        if campo_bd == 'data_exame':
          dt_parsed = (
              _parse_data_segura(val)
              if val_upper not in ['NULL', 'NONE', 'NAN', '']
              else None
          )
          valores.append(dt_parsed if dt_parsed else data_fallback_mes)

        elif campo_bd in ['ovos_aegypti', 'ovos_albopictus', 'outros_ovos']:
          if val_upper in ['NULL', 'NONE', 'NAN', '']:
            valores.append(0)
          else:
            val_num = pd.to_numeric(val, errors='coerce')
            valores.append(0 if pd.isna(val_num) else int(val_num))

        elif campo_bd == 'id_ovitrampa':
          valores.append(id_str)

        elif campo_bd in [
            'localizacao',
            'complemento_tipo',
            'setor_distrito',
            'responsavel',
            'quarteirao',
            'tipo',
            'acoes',
            'endereco',
            'numero',
            'bairro',
        ]:
          if val_upper in ['NULL', 'NONE', 'NAN', '']:
            valores.append('')
          else:
            valores.append(val_str)

        else:
          valores.append(
              None
              if (
                  pd.isna(val)
                  or val_upper in ['NAN', 'NONE', 'NAT', 'NULL', '']
              )
              else val_str
          )

      registros.append(valores)

    if not registros:
      log.status = 'erro'
      log.mensagem = 'Nenhuma ovitrampa válida encontrada na planilha.'
      log.save()
      return

    placeholders = ['%s'] * len(DE_PARA_PADRAO.keys())
    query = f"""
            INSERT INTO ovitrampas_temp ({", ".join(campos_sql)}) 
            VALUES ({", ".join(placeholders)}) 
            ON CONFLICT DO NOTHING
        """
    with transaction.atomic():
      with connection.cursor() as cursor:
        cursor.executemany(query, registros)
 
    log.status = 'finalizado'
    log.progresso = 100
    log.mensagem = (
        f'Sucesso! {len(registros)} ovitrampas processadas e acumuladas.'
    )
    log.save()

  except Exception as e:
    LogSincronizacao.objects.filter(id=job_id).update(
        status='erro', mensagem=str(e)
    )
  finally:
    if os.path.exists(arquivo_path):
      try:
        os.remove(arquivo_path)
      except Exception:
        pass