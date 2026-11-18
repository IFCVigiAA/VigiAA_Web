import os
import re
import json
import calendar
import logging
import unicodedata
from datetime import datetime
import pandas as pd
import geocoder
from celery import shared_task
from django.db import connection, connections, transaction
from casos.utils.log_errors import ErrorLogger
from .models import LogSincronizacao

logger = logging.getLogger(__name__)


# ==============================================================================
# CONFIGURAÇÕES DINÂMICAS DO MUNICÍPIO (POSTGIS / VW_MUNICIPIO)
# ==============================================================================

def _get_municipio_ativo():
    """
    Consulta a vw_municipio no banco oficial para descobrir dinamicamente
    qual município está ativo nesta instalação, seu centroide e seu polígono.
    """
    db_alias = 'ofc' if 'ofc' in connections else 'default'
    try:
        with connections[db_alias].cursor() as cursor:
            cursor.execute("""
                SELECT 
                    "CD_MUN",
                    "NM_MUN",
                    "SIGLA_UF",
                    latitude,
                    longitude
                FROM vw_municipio
                LIMIT 1
            """)
            row = cursor.fetchone()

        if row:
            return {
                "cd_mun": row[0],
                "nome": str(row[1]).strip(),
                "uf": str(row[2]).strip(),
                "centro": (float(row[3]), float(row[4])),
            }
    except Exception as e:
        logger.warning(f"Falha ao consultar vw_municipio: {e}")

    return {
        "cd_mun": None,
        "nome": "",
        "uf": "",
        "centro": (-15.793889, -47.882778),
    }


def _ponto_pertence_ao_municipio(lat, lng):
    """
    Usa o PostGIS (ST_Contains) contra o polígono oficial da vw_municipio
    para garantir que a coordenada geocodificada cai realmente dentro da cidade.
    """
    db_alias = 'ofc' if 'ofc' in connections else 'default'
    try:
        with connections[db_alias].cursor() as cursor:
            cursor.execute("""
                SELECT EXISTS (
                    SELECT 1 
                    FROM vw_municipio 
                    WHERE ST_Contains(
                        ST_Transform(geom, 4674), 
                        ST_SetSRID(ST_MakePoint(%s, %s), 4674)
                    )
                )
            """, [float(lng), float(lat)])
            return cursor.fetchone()[0]
    except Exception:
        return True


# ==============================================================================
# FUNÇÕES DE TRATAMENTO TEXTUAL, DATAS E COORDENADAS
# ==============================================================================

def _normalizar_texto(texto):
    if pd.isna(texto) or texto is None:
        return ""
    s = str(texto).strip().lower()
    s = ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
    s = re.sub(r'[.ªº]', '', s)
    return s.replace(' ', '_')


def _limpar_endereco_generico(endereco_atual):
    """Normaliza abreviações comuns sem regras específicas de cidade."""
    if pd.isna(endereco_atual) or not endereco_atual:
        return ""
    rua = str(endereco_atual).upper().strip()
    rua = re.sub(r'\bAV\.?\s+', 'AVENIDA ', rua)
    rua = re.sub(r'\bR\.?\s+', 'RUA ', rua)
    rua = re.sub(r'\bTRAV\.?\s+', 'TRAVESSA ', rua)
    rua = re.sub(r'\s+', ' ', rua)
    return rua


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


def _corrigir_coordenadas_escalavel(df, coluna):
    """
    Usa a mediana da coluna como referência para identificar coordenadas
    que perderam a vírgula e corrige a escala.
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


def _extrair_data_ultimo_dia_mes(nome_arquivo):
    """Extrai mês e ano do nome do arquivo e retorna a data do último dia do mês."""
    agora = datetime.now()
    mes, ano = None, agora.year
    nome_clean = nome_arquivo.lower()

    meses_extenso = {
        'janeiro': 1, 'jan': 1,
        'fevereiro': 2, 'fev': 2,
        'marco': 3, 'mar': 3, 'março': 3,
        'abril': 4, 'abr': 4,
        'maio': 5, 'mai': 5,
        'junho': 6, 'jun': 6,
        'julho': 7, 'jul': 7,
        'agosto': 8, 'ago': 8,
        'setembro': 9, 'set': 9,
        'outubro': 10, 'out': 10,
        'novembro': 11, 'nov': 11,
        'dezembro': 12, 'dez': 12,
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
# GEOCODIFICAÇÃO EM CASCATA GENÉRICA
# ==============================================================================

def _geocodificar_cascata(endereco, bairro):
    mun = _get_municipio_ativo()
    centro_lat, centro_lng = mun["centro"]
    sufixo_cidade = ", ".join(filter(None, [mun["nome"], mun["uf"], "BRASIL"]))

    rua = _limpar_endereco_generico(endereco) if endereco else ""
    bairro_str = str(bairro).upper().strip() if bairro and pd.notna(bairro) else ""

    if (not rua or rua == "NAN") and (not bairro_str or bairro_str == "NAN"):
        return centro_lat, centro_lng

    # 1. Busca Endereço Completo via ArcGIS
    if rua and rua != "NAN":
        query_rua = ", ".join([p for p in [rua, bairro_str, sufixo_cidade] if p])
        try:
            g = geocoder.arcgis(query_rua, timeout=5)
            if g.ok and g.latlng:
                lat, lng = float(g.latlng[0]), float(g.latlng[1])
                if _ponto_pertence_ao_municipio(lat, lng):
                    return lat, lng
        except Exception:
            pass

    # 2. Fallback: busca centroide do Bairro no PostGIS (vw_bairros_mun_ibge) ou ArcGIS
    if bairro_str and bairro_str != "NAN":
        db_alias = 'ofc' if 'ofc' in connections else 'default'
        try:
            with connections[db_alias].cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        ST_Y(ST_Transform(ST_PointOnSurface(geom), 4674)),
                        ST_X(ST_Transform(ST_PointOnSurface(geom), 4674))
                    FROM vw_bairros_mun_ibge
                    WHERE UPPER(UNACCENT("Nome")) = UPPER(UNACCENT(%s))
                    LIMIT 1
                """, [bairro_str])
                row_bairro = cursor.fetchone()
                if row_bairro and row_bairro[0] and row_bairro[1]:
                    return float(row_bairro[0]), float(row_bairro[1])
        except Exception:
            pass

        query_bairro = ", ".join([p for p in [f"BAIRRO {bairro_str}", sufixo_cidade] if p])
        try:
            g = geocoder.arcgis(query_bairro, timeout=5)
            if g.ok and g.latlng:
                lat, lng = float(g.latlng[0]), float(g.latlng[1])
                if _ponto_pertence_ao_municipio(lat, lng):
                    return lat, lng
        except Exception:
            pass

    return centro_lat, centro_lng


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

        mun = _get_municipio_ativo()
        centro_lat, centro_lng = mun["centro"]

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
                'notificação', 'notificacao', 'sinan', 'sintomas',
                'resultado', 'situacao', 'bairro', 'endereco',
                'sexo', 'nascimento', 'nome',
            }
            melhor_linha, max_matches = 0, 0
            for i, row in df_raw.iterrows():
                valores_linha = set(str(v).strip().lower() for v in row.values if pd.notna(v))
                matches = len(valores_linha.intersection(TERMOS_RECONHECIDOS))
                if matches > max_matches:
                    max_matches = matches
                    melhor_linha = i
            h_idx = melhor_linha if max_matches >= 2 else 3

        df = pd.read_excel(arquivo_path, header=h_idx, engine=engine).dropna(how='all')
        df.columns = [str(c).replace('\n', ' ').strip() for c in df.columns]

        if not df.empty:
            primeira_coluna = df.columns[0]
            df = df[~df[primeira_coluna].astype(str).str.upper().str.contains('TOTAL', na=False)]

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
            'local_atendimento', 'notificacao', 'inicio_sintomas', 'sinan',
            'nome', 'data_nasc', 'sexo', 'endereco', 'bairro',
            'resultado', 'situacao', 'observacoes',
        ]

        total_registros = len(df)
        if total_registros == 0:
            log.status = 'erro'
            log.mensagem = 'Nenhum caso positivo válido encontrado.'
            log.save(update_fields=['status', 'mensagem'])
            return

        registros = []

        for current_idx, (idx, r) in enumerate(df.iterrows(), start=1):
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

            if lat_val is None or lon_val is None:
                lat_arc, lon_arc = _geocodificar_cascata(end_str, bairro_str)
                lat_val = lat_arc if lat_arc is not None else centro_lat
                lon_val = lon_arc if lon_arc is not None else centro_lng

            valores = []
            for campo_bd in campos_db:
                coluna_planilha = DE_PARA.get(campo_bd)

                if campo_bd == 'endereco' and (not coluna_planilha or coluna_planilha not in df.columns):
                    coluna_planilha = col_end_nome
                elif campo_bd == 'bairro' and (not coluna_planilha or coluna_planilha not in df.columns):
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
                            if (pd.isna(val) or str(val).strip().upper() in ['NAN', 'NONE', 'NAT', 'NULL', ''])
                            else str(val).strip()
                        )
                else:
                    valores.append(None)

            lat_str = str(lat_val) if lat_val is not None else None
            lon_str = str(lon_val) if lon_val is not None else None

            valores.extend([lat_str, lon_str, lon_val, lat_val])
            registros.append(valores)

            if current_idx % 2 == 0 or current_idx == total_registros:
                pct = int((current_idx / total_registros) * 100)
                log.progresso = min(pct, 99)
                log.mensagem = f'Geoprocessando e importando... {current_idx}/{total_registros} registros ({pct}%)'
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
        log.mensagem = f'Sucesso! {len(registros)} casos positivos processados e acumulados.'
        log.save(update_fields=['status', 'progresso', 'mensagem'])

    except Exception as e:
        LogSincronizacao.objects.filter(id=job_id).update(status='erro', mensagem=str(e))
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
                    f"POINT({lon} {lat})",
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
# 3. TASK FOCOS
# ==============================================================================

@shared_task(bind=True)
def task_processar_focos(self, job_id, arquivo_path, celula_cabecalho=None, mapeamento_customizado=None):
    try:
        log = LogSincronizacao.objects.get(id=job_id)
        erros = ErrorLogger()

        _, ext = os.path.splitext(arquivo_path)
        ext = ext.lower()
        engine = 'odf' if ext == '.ods' else ('xlrd' if ext == '.xls' else 'openpyxl')

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
                'imovel', 'deposito', 'latitude', 'longitude', 'aquaticas',
            }

            melhor_linha, max_matches = 0, 0
            for i, row in df_raw.iterrows():
                valores_linha = set(_normalizar_texto(str(v)) for v in row.values if pd.notna(v))
                matches = len(valores_linha.intersection(TERMOS_RECONHECIDOS))
                if matches > max_matches:
                    max_matches = matches
                    melhor_linha = i

            h_idx = melhor_linha if max_matches >= 3 else 0

        df = pd.read_excel(arquivo_path, header=h_idx, engine=engine).dropna(how='all')
        df.columns = [str(c).replace('\n', ' ').strip() for c in df.columns]

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

        campos_sql = list(DE_PARA_PADRAO.keys())
        registros = []

        for idx, r in df.iterrows():
            lt = r.get(col_lat) if col_lat and col_lat in df.columns else None
            ln = r.get(col_lng) if col_lng and col_lng in df.columns else None

            if pd.isna(lt) or pd.isna(ln) or str(lt).strip() in ['None', 'nan', '0', '']:
                erros.add("geoprocessamento", linha=idx + h_idx + 2, erro="coordenadas ausentes ou invalidas")
                continue

            try:
                float(str(lt).replace(',', '.'))
                float(str(ln).replace(',', '.'))
            except (ValueError, TypeError):
                continue

            valores = []
            for campo_bd in campos_sql:
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
                    valores.append(0 if is_contagem else None)

            registros.append(valores)

        if not registros:
            log.status = "erro"
            log.mensagem = "Nenhum foco válido encontrado. Verifique as colunas de Latitude e Longitude."
            log.save()
            return

        placeholders = ["%s"] * len(campos_sql)
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
            except Exception:
                pass


# ==============================================================================
# 4. TASK PONTOS ESTRATÉGICOS
# ==============================================================================

@shared_task(bind=True)
def task_processar_pontos(self, job_id, arquivo_path, celula_cabecalho=None, mapeamento_customizado=None):
    try:
        log = LogSincronizacao.objects.get(id=job_id)
        mun = _get_municipio_ativo()
        municipio_padrao = mun["nome"].upper() if mun["nome"] else None

        _, ext = os.path.splitext(arquivo_path)
        ext = ext.lower()
        engine = 'odf' if ext == '.ods' else ('xlrd' if ext == '.xls' else 'openpyxl')

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
                'atividade', 'tipo_atividade', 'coleta', 'exame', 'latitude', 'longitude',
            }

            melhor_linha, max_matches = 0, 0
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
            'longitude': 'LONGITUDE',
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
                float(str(lt).replace(',', '.'))
                float(str(ln).replace(',', '.'))
            except (ValueError, TypeError):
                continue

            valores_finais = []
            for campo_bd in campos_sql:
                coluna_planilha = DE_PARA.get(campo_bd)
                if coluna_planilha and coluna_planilha in df.columns:
                    val = r.get(coluna_planilha)

                    if campo_bd in ['data_coleta', 'data_entrada', 'data_exame']:
                        valores_finais.append(_parse_data_segura(val))
                    elif campo_bd in ['aegypti_aquaticas', 'albopictus_aquaticas']:
                        val_num = pd.to_numeric(val, errors='coerce')
                        valores_finais.append(0 if pd.isna(val_num) else int(val_num))
                    elif campo_bd == 'municipio':
                        v_str = str(val).strip() if pd.notna(val) else ""
                        valores_finais.append(v_str if v_str and v_str.upper() not in ['NAN', 'NONE', 'NULL'] else municipio_padrao)
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
                        valores_finais.append(municipio_padrao)
                    else:
                        valores_finais.append(None)

            registros.append(valores_finais)

        if not registros:
            log.status = "erro"
            log.mensagem = "Nenhum ponto estratégico válido encontrado. Verifique as colunas de Latitude e Longitude."
            log.save()
            return

        placeholders = ["%s"] * len(campos_sql)
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
            except Exception:
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
            h_idx = next(
                (i for i, row in df_temp.iterrows() if any("Número" in str(x) or "Tipo Armadilha" in str(x) for x in row)),
                0,
            )

        df = pd.read_excel(arquivo_path, header=h_idx, engine=engine).dropna(how='all')
        colunas_limpas = [str(c).strip() for c in df.columns]
        if "Tipo Imóvel" not in colunas_limpas or "Tipo Armadilha" not in colunas_limpas:
            raise ValueError("Arquivo inválido para Armadilhas.")

        DE_PARA = mapeamento_customizado or {
            'numero': 'Número',
            'municipio': 'Município',
            'localidade': 'Localidade',
            'endereco': 'Endereço',
            'complemento': 'Complemento',
            'quarteiroes': 'Quarteiroes',
            'tipo_imovel': 'Tipo Imóvel',
            'tipo_armadilha': 'Tipo Armadilha',
            'latitude': 'Latitude',
            'longitude': 'Longitude',
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
            except Exception:
                pass


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
                'ovitrampa', 'id_ovitrampa', 'n_ovitrampa', 'endereco',
                'bairro', 'exame', 'coleta', 'ovos',
                'aegypti', 'albopictus', 'latitude', 'longitude',
            }

            melhor_linha, max_matches = 0, 0
            for i, row in df_raw.iterrows():
                valores_linha = set(str(v).strip().lower() for v in row.values if str(v).strip() != '')
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
            df = df[~df[primeira_coluna].astype(str).str.upper().str.contains('TOTAL', na=False)]

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

            if pd.isna(val_id_raw) or str(val_id_raw).strip().upper() in ['NAN', 'NONE', 'NAT', 'NULL', '']:
                continue

            id_str = str(val_id_raw).strip()
            if id_str.endswith('.0'):
                id_str = id_str[:-2]

            valores = []
            for campo_bd in campos_sql:
                coluna_planilha = DE_PARA.get(campo_bd)
                val = r.get(coluna_planilha) if coluna_planilha and coluna_planilha in df.columns else None
                val_str = str(val).strip() if val is not None else ''
                val_upper = val_str.upper()

                if campo_bd == 'data_exame':
                    dt_parsed = _parse_data_segura(val) if val_upper not in ['NULL', 'NONE', 'NAN', ''] else None
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
                    'localizacao', 'complemento_tipo', 'setor_distrito',
                    'responsavel', 'quarteirao', 'tipo', 'acoes',
                    'endereco', 'numero', 'bairro',
                ]:
                    valores.append('' if val_upper in ['NULL', 'NONE', 'NAN', ''] else val_str)

                else:
                    valores.append(None if (pd.isna(val) or val_upper in ['NAN', 'NONE', 'NAT', 'NULL', '']) else val_str)

            registros.append(valores)

        if not registros:
            log.status = 'erro'
            log.mensagem = 'Nenhuma ovitrampa válida encontrada na planilha.'
            log.save()
            return

        placeholders = ['%s'] * len(campos_sql)
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
        log.mensagem = f'Sucesso! {len(registros)} ovitrampas processadas e acumuladas.'
        log.save()

    except Exception as e:
        LogSincronizacao.objects.filter(id=job_id).update(status='erro', mensagem=str(e))
    finally:
        if os.path.exists(arquivo_path):
            try:
                os.remove(arquivo_path)
            except Exception:
                pass