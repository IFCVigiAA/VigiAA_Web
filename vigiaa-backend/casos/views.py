import os
import re
import json
import unicodedata
import pandas as pd
from django.db import connections
from django.conf import settings
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import LogSincronizacao
from .tasks import (
    task_processar_positivos,
    task_processar_pontos,
    task_processar_focos,
    task_processar_armadilhas,
    task_geoprocessar_pendentes,
    task_processar_ovitrampas,
)

CAMPOS_BANCO_POR_TIPO = {
    'casos': {
        'local_atendimento': 'Local de Notificação / Atendimento',
        'notificacao': 'Data da Notificação',
        'inicio_sintomas': 'Data de Início dos Sintomas',
        'sinan': 'Número do SINAN',
        'nome': 'Nome Completo',
        'data_nasc': 'Data de Nascimento',
        'sexo': 'Sexo',
        'endereco': 'Endereço Completo',
        'bairro': 'Bairro',
        'resultado': 'Resultado Final',
        'latitude': 'Latitude',
        'longitude': 'Longitude',
        'situacao': 'Situação do Caso',
        'observacoes': 'Observações',
    },
    'pontos': {
        'numero': 'Nº PE / Código',
        'regional': 'Regional',
        'municipio': 'Município',
        'localidade': 'Bairro / Localidade',
        'endereco': 'Endereço',
        'complemento': 'Complemento',
        'quarteiroes': 'Quarteirão',
        'imovel': 'Imóvel',
        'deposito': 'Depósito',
        'tp_atividade': 'Tipo de Atividade',
        'data_coleta': 'Data da Coleta',
        'data_entrada': 'Data de Entrada',
        'data_exame': 'Data do Exame',
        'aegypti_aquaticas': 'A. aegypti formas aquáticas',
        'albopictus_aquaticas': 'A. albopictus formas aquáticas',
        'latitude': 'Latitude',
        'longitude': 'Longitude',
    },
    'focos': {
        'n_foco': 'Nº Foco',
        'regional': 'Regional',
        'municipio': 'Município',
        'localidade': 'Bairro',
        'rua_numero': 'Endereço',
        'complemento': 'Complemento',
        'quarteirao': 'Quarteirão',
        'imovel': 'Imóvel',
        'deposito': 'Depósito',
        'tipo_atividade': 'Tipo de Atividade',
        'data_coleta': 'Data da Coleta',
        'data_entrada': 'Data de Entrada',
        'data_exame': 'Data do Exame',
        'a_aegypti_form_aquaticas': 'A. aegypti formas aquáticas',
        'a_aegypti_form_adultas': 'A. aegypti formas adultas',
        'a_albopictus_form_aquaticas': 'A. albopictus formas aquáticas',
        'a_albopictus_form_adultas': 'A. albopictus formas adultas',
        'ovo_a_aegypti': 'A. aegypti ovos',
        'latitude': 'Latitude',
        'longitude': 'Longitude',
    },
    'armadilhas': {
        'numero': 'Número / Código da Armadilha',
        'municipio': 'Município',
        'localidade': 'Localidade / Bairro',
        'endereco': 'Endereço',
        'complemento': 'Complemento',
        'quarteiroes': 'Quarteirões',
        'tipo_imovel': 'Tipo de Imóvel',
        'tipo_armadilha': 'Tipo de Armadilha',
        'latitude': 'Latitude',
        'longitude': 'Longitude',
    },
    'ovitrampas': {
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
    },
}


def _salvar_arquivo_temporario(job_id, arquivo):
    """Salva o arquivo em media/temp_uploads para que o Celery possa acessá-lo."""
    path_dir = os.path.join(settings.MEDIA_ROOT, "temp_uploads")
    os.makedirs(path_dir, exist_ok=True)

    nome_seguro = f"{job_id}_{arquivo.name.replace(' ', '_')}"
    caminho_final = os.path.join(path_dir, nome_seguro)

    with open(caminho_final, 'wb+') as destination:
        for chunk in arquivo.chunks():
            destination.write(chunk)
    return caminho_final


def _parse_mapeamento(request):
    """Extrai e converte a string JSON vinda tanto do DRF quanto do Django."""
    mapeamento_raw = None
    if hasattr(request, 'data'):
        mapeamento_raw = request.data.get("mapeamento", None)
    if not mapeamento_raw:
        mapeamento_raw = request.POST.get("mapeamento", None)

    if not mapeamento_raw:
        return None

    try:
        if isinstance(mapeamento_raw, str):
            return json.loads(mapeamento_raw)
        return mapeamento_raw
    except Exception:
        return None


def _normalizar_texto(texto):
    """Remove acentos, caracteres especiais e converte para caixa alta."""
    if not texto:
        return ""
    nfkd = unicodedata.normalize('NFKD', str(texto))
    sem_acento = "".join([c for c in nfkd if not unicodedata.combining(c)])
    return re.sub(r'[^A-Z0-9]', '', sem_acento.upper())


# ==============================================================================
# ENDPOINTS DE CONFIGURAÇÃO DINÂMICA DO MUNICÍPIO
# ==============================================================================

@api_view(["GET"])
@permission_classes([AllowAny])
def municipios_disponiveis(request):
    """Busca municípios na tabela nacional municipios_br_ibge sem depender de extensão externa."""
    q = str(request.GET.get("q", "")).strip()
    db_alias = 'ofc' if 'ofc' in connections else 'default'
    acentos = 'ÁÀÂÃÄÉÈÊËÍÌÎÏÓÒÔÕÖÚÙÛÜÇáàâãäéèêëíìîïóòôõöúùûüç'
    sem_acentos = 'AAAAAEEEEIIIIOOOOOUUUUCaaaaaeeeeiiiiooooouuuuc'

    try:
        with connections[db_alias].cursor() as cursor:
            if q:
                cursor.execute(f"""
                    SELECT "CD_MUN", "NM_MUN", "SIGLA_UF", "NM_UF"
                    FROM municipios_br_ibge
                    WHERE TRANSLATE("NM_MUN", '{acentos}', '{sem_acentos}') ILIKE TRANSLATE(%s, '{acentos}', '{sem_acentos}')
                       OR "CD_MUN"::text LIKE %s
                    ORDER BY 
                        CASE WHEN TRANSLATE("NM_MUN", '{acentos}', '{sem_acentos}') ILIKE TRANSLATE(%s, '{acentos}', '{sem_acentos}') THEN 0 ELSE 1 END,
                        "NM_MUN", 
                        "SIGLA_UF"
                    LIMIT 30
                """, [f"%{q}%", f"{q}%", f"{q}%"])
            else:
                cursor.execute("""
                    SELECT "CD_MUN", "NM_MUN", "SIGLA_UF", "NM_UF"
                    FROM municipios_br_ibge
                    ORDER BY "NM_MUN", "SIGLA_UF"
                    LIMIT 50
                """)
            rows = cursor.fetchall()

        resultados = [
            {
                "cd_mun": row[0],
                "nome": row[1],
                "uf": row[2],
                "uf_nome": row[3],
                "label": f"{row[1]} - {row[2]}",
            }
            for row in rows
        ]
        return Response({"municipios": resultados})
    except Exception as e:
        return Response({"erro": str(e)}, status=500)


@api_view(["POST"])
@permission_classes([AllowAny])
def definir_municipio(request):
    """Atualiza a vw_municipio no PostGIS para o município selecionado pelo usuário."""
    cd_mun = str(request.data.get("cd_mun", "")).strip()
    if not cd_mun or not re.match(r'^\d{7}$', cd_mun):
        return Response({"erro": "Código IBGE (cd_mun) inválido."}, status=400)

    db_alias = 'ofc' if 'ofc' in connections else 'default'
    try:
        with connections[db_alias].cursor() as cursor:
            cursor.execute("""
                SELECT "CD_MUN", "NM_MUN", "SIGLA_UF"
                FROM municipios_br_ibge
                WHERE "CD_MUN"::text = %s
                LIMIT 1
            """, [cd_mun])
            mun = cursor.fetchone()

            if not mun:
                return Response({"erro": "Município não encontrado na base do IBGE."}, status=404)

            cursor.execute(f"""
                CREATE OR REPLACE VIEW vw_municipio AS
                SELECT
                    id,
                    geom,
                    "CD_MUN",
                    "NM_MUN",
                    "CD_RGI",
                    "NM_RGI",
                    "CD_RGINT",
                    "NM_RGINT",
                    "CD_UF",
                    "NM_UF",
                    "SIGLA_UF",
                    "CD_REGIA",
                    "NM_REGIA",
                    "SIGLA_RG",
                    "CD_CONCU",
                    "NM_CONCU",
                    "AREA_KM2",
                    ST_Y(ST_Transform(ST_PointOnSurface(geom), 4674)) AS latitude,
                    ST_X(ST_Transform(ST_PointOnSurface(geom), 4674)) AS longitude
                FROM municipios_br_ibge
                WHERE "CD_MUN"::text = '{cd_mun}';
            """)

        return Response({
            "sucesso": True,
            "cd_mun": mun[0],
            "nome": mun[1],
            "uf": mun[2],
            "mensagem": f"Município ativo alterado para {mun[1]} - {mun[2]}.",
        })
    except Exception as e:
        return Response({"erro": str(e)}, status=500)


@api_view(["GET"])
@permission_classes([AllowAny])
def config_municipio_ativo(request):
    """Retorna os metadados e coordenadas centrais da cidade configurada na vw_municipio."""
    db_alias = 'ofc' if 'ofc' in connections else 'default'
    try:
        with connections[db_alias].cursor() as cursor:
            cursor.execute("""
                SELECT 
                    "CD_MUN",
                    "NM_MUN",
                    "NM_UF",
                    "SIGLA_UF",
                    latitude,
                    longitude,
                    ST_XMin(ST_Transform(geom, 4674)) AS min_lng,
                    ST_YMin(ST_Transform(geom, 4674)) AS min_lat,
                    ST_XMax(ST_Transform(geom, 4674)) AS max_lng,
                    ST_YMax(ST_Transform(geom, 4674)) AS max_lat
                FROM vw_municipio
                LIMIT 1
            """)
            row = cursor.fetchone()

        if not row:
            return Response({"erro": "Município não configurado na vw_municipio"}, status=404)

        return Response({
            "cd_mun": row[0],
            "nome": row[1],
            "uf_nome": row[2],
            "uf": row[3],
            "centro": {
                "lat": float(row[4]),
                "lng": float(row[5]),
            },
            "bounds": [
                [float(row[7]), float(row[6])],
                [float(row[9]), float(row[8])],
            ],
        })
    except Exception as e:
        return Response({"erro": str(e)}, status=500)


# ==============================================================================
# AUTENTICAÇÃO, STATUS E UPLOAD DE PLANILHAS
# ==============================================================================

@login_required
def me(request):
    u = request.user
    return JsonResponse({
        "authenticated": True,
        "username": u.username,
        "is_staff": u.is_staff,
        "is_superuser": u.is_superuser,
    })


def status_processamento(request, job_id):
    try:
        job_id_int = int(job_id)
        proc = LogSincronizacao.objects.get(id=job_id_int)
        return JsonResponse({
            "status": proc.status,
            "progresso": proc.progresso,
            "mensagem": proc.mensagem,
        })
    except (LogSincronizacao.DoesNotExist, ValueError):
        return JsonResponse({"status": "erro", "mensagem": "Job não encontrado"}, status=404)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def upload_casos_positivos(request):
    arquivo = request.FILES.get("positivos")
    if not arquivo:
        return JsonResponse({"erro": "Arquivo não enviado"}, status=400)

    celula_cabecalho = request.POST.get("celula_cabecalho", None)
    mapeamento_dict = _parse_mapeamento(request)

    job = LogSincronizacao.objects.create(tipo="positivos", nome_arquivo=arquivo.name, status="na_fila")
    caminho = _salvar_arquivo_temporario(job.id, arquivo)

    task_processar_positivos.delay(
        job.id,
        caminho,
        celula_cabecalho=celula_cabecalho,
        mapeamento_customizado=mapeamento_dict,
    )
    return JsonResponse({"sucesso": True, "job_id": job.id})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def extrair_cabecalho_e_sugerir(request):
    arquivo = (
        request.FILES.get('arquivo')
        or request.FILES.get('positivos')
        or (hasattr(request, 'data') and request.data.get('arquivo'))
    )
    celula_cabecalho = request.POST.get('celula_cabecalho') or (
        hasattr(request, 'data') and request.data.get('celula_cabecalho')
    )

    tipo_planilha = (
        str(request.data.get('tipo') or request.POST.get('tipo') or 'casos')
        .strip()
        .lower()
    )

    if not arquivo:
        return JsonResponse({'erro': 'Nenhum arquivo enviado'}, status=400)

    try:
        _, ext = os.path.splitext(arquivo.name)
        ext = ext.lower()
        engine = 'odf' if ext == '.ods' else ('xlrd' if ext == '.xls' else 'openpyxl')
        h_idx = None

        if celula_cabecalho:
            match = re.search(r'\d+', str(celula_cabecalho))
            if match:
                h_idx = max(0, int(match.group()) - 1)

        if h_idx is None:
            arquivo.seek(0)
            df_temp = pd.read_excel(
                arquivo, header=None, nrows=25, engine=engine, keep_default_na=False
            )

            melhor_linha = 0
            max_pontuacao = 0

            for i, row in df_temp.iterrows():
                celulas = [str(x).strip() for x in row.values if str(x).strip() != '']
                if len(celulas) < 3:
                    continue

                celulas_texto = 0
                for c in celulas:
                    c_clean = c.replace('.', '').replace('-', '').replace(',', '').strip()
                    if not c_clean.isdigit():
                        celulas_texto += 1
                if celulas_texto > max_pontuacao:
                    max_pontuacao = celulas_texto
                    melhor_linha = i

            h_idx = melhor_linha

        arquivo.seek(0)

        df_raw = pd.read_excel(
            arquivo,
            header=None,
            nrows=h_idx + 1,
            engine=engine,
            keep_default_na=False,
        )
        linha_cabecalho = df_raw.iloc[h_idx].values

        colunas_planilha = []
        for idx, val in enumerate(linha_cabecalho):
            val_str = str(val).replace(' ', ' ').strip()
            if val_str == '' or val_str.upper() in ['NAN', 'NONE']:
                colunas_planilha.append(f'COLUNA_{idx+1}')
            else:
                colunas_planilha.append(val_str)

        campos_banco = CAMPOS_BANCO_POR_TIPO.get(tipo_planilha)
        if not campos_banco:
            for k in CAMPOS_BANCO_POR_TIPO:
                if k in tipo_planilha or tipo_planilha in k:
                    campos_banco = CAMPOS_BANCO_POR_TIPO[k]
                    break
        if not campos_banco:
            campos_banco = CAMPOS_BANCO_POR_TIPO['casos']

        SINONIMOS_POR_TIPO = {
            'casos': {
                'local_atendimento': ['LOCAL NOTIFICAÇÃO', 'LOCAL NOTIFICACAO', 'LOCAL ATENDIMENTO', 'UNIDADE NOTIFICANTE'],
                'notificacao': ['DATA NOT.', 'DATA NOTIFICAÇÃO', 'DATA NOTIFICACAO'],
                'inicio_sintomas': ['INICIO SINTOMAS', 'INÍCIO SINTOMAS', 'DATA SINTOMAS'],
                'sinan': ['SINAN', 'NÚMERO DO SINAN', 'NUMERO DO SINAN'],
                'nome': ['NOME COMPLETO', 'NOME', 'PACIENTE'],
                'data_nasc': ['NASCIMENTO', 'DATA DE NASCIMENTO', 'DATA NASC'],
                'sexo': ['SEXO', 'GÊNERO', 'GENERO'],
                'endereco': ['ENDEREÇO', 'ENDERECO', 'RUA/NÚMERO', 'RUA/NUMERO', 'LOGRADOURO'],
                'bairro': ['BAIRRO', 'LOCALIDADE', 'BAIRRO / LOCALIDADE'],
                'resultado': ['RESULTADO', 'RESULTADO FINAL'],
                'latitude': ['LATITUDE', 'LAT'],
                'longitude': ['LONGITUDE', 'LONG', 'LNG'],
                'situacao': ['SITUAÇÃO', 'SITUACAO'],
                'observacoes': ['OBSERVAÇÃO', 'OBSERVAÇÕES', 'OBS'],
            },
            'ovitrampas': {
                'id_ovitrampa': ['ID / N. OVITRAMPA', 'ID OVITRAMPA', 'N. OVITRAMPA', 'Nº OVITRAMPA', 'OVITRAMPA'],
                'endereco': ['ENDEREÇO', 'ENDERECO', 'RUA/NÚMERO', 'LOGRADOURO'],
                'numero': ['NÚMERO DO LOGRADOURO', 'NÚMERO', 'NUMERO', 'Nº'],
                'complemento_tipo': ['COMPLEMENTO / TIPO IMÓVEL', 'COMPLEMENTO'],
                'bairro': ['BAIRRO', 'LOCALIDADE', 'BAIRRO / LOCALIDADE'],
                'localizacao': ['LOCALIZAÇÃO DA OVITRAMPA', 'LOCALIZAÇÃO'],
                'setor_distrito': ['SETOR / DISTRITO', 'SETOR/DISTRITO', 'SETOR', 'DISTRITO'],
                'responsavel': ['RESPONSÁVEL', 'AGENTE'],
                'quarteirao': ['QUARTEIRÃO', 'QUARTEIRAO'],
                'data_exame': ['DATA DO EXAME', 'DATA EXAME', 'DATA DA COLETA'],
                'ovos_aegypti': ['OVO A. AEGYPTI', 'OVOS A. AEGYPTI', 'AEGYPTI'],
                'ovos_albopictus': ['OVO A. ALBOPICTUS', 'OVOS A. ALBOPICTUS', 'ALBOPICTUS'],
                'outros_ovos': ['OUTROS OVOS', 'OUTROS'],
                'tipo': ['TIPO'],
                'latitude': ['LATITUDE', 'LAT'],
                'longitude': ['LONGITUDE', 'LONG', 'LNG'],
                'acoes': ['AÇÕES (BRI, UBV E OUTRAS)', 'AÇÕES'],
            },
            'pontos': {
                'codigo': ['Nº PE / CÓDIGO', 'Nº PE', 'N° PE', 'CÓDIGO PE', 'CÓDIGO', 'PE'],
                'numero': ['Nº PE / CÓDIGO', 'Nº PE', 'N° PE', 'CÓDIGO PE', 'CÓDIGO', 'PE'],
                'regional': ['REGIONAL'],
                'municipio': ['MUNICÍPIO', 'MUNICIPIO'],
                'bairro': ['LOCALIDADE', 'BAIRRO / LOCALIDADE', 'BAIRRO'],
                'localidade': ['LOCALIDADE', 'BAIRRO / LOCALIDADE', 'BAIRRO'],
                'endereco': ['RUA/NÚMERO', 'RUA/NUMERO', 'ENDEREÇO', 'ENDERECO', 'LOGRADOURO'],
                'rua_numero': ['RUA/NÚMERO', 'RUA/NUMERO', 'ENDEREÇO', 'ENDERECO', 'LOGRADOURO'],
                'complemento': ['COMPLEMENTO'],
                'quarteirao': ['QUARTEIRÃO', 'QUARTEIRAO', 'QUARTEIRÕES', 'QUARTEIROES'],
                'quarteiroes': ['QUARTEIRÃO', 'QUARTEIRAO', 'QUARTEIRÕES', 'QUARTEIROES'],
                'imovel': ['IMÓVEL', 'IMOVEL', 'TIPO IMÓVEL'],
                'deposito': ['DEPÓSITO', 'DEPOSITO'],
                'tipo_atividade': ['TIPO DE ATIVIDADE', 'TIPO ATIVIDADE', 'ATIVIDADE'],
                'tp_atividade': ['TIPO DE ATIVIDADE', 'TIPO ATIVIDADE', 'ATIVIDADE'],
                'data_coleta': ['DATA DA COLETA', 'DATA COLETA'],
                'data_entrada': ['DATA DE ENTRADA', 'DATA ENTRADA'],
                'data_exame': ['DATA DO EXAME', 'DATA EXAME'],
                'aegypti_aquaticas': ['A. AEGYPTI FORMAS AQUÁTICAS', 'A. AEGYPTI FORMAS AQUATICAS'],
                'albopictus_aquaticas': ['A. ALBOPICTUS FORMAS AQUÁTICAS', 'A. ALBOPICTUS FORMAS AQUATICAS'],
                'latitude': ['LATITUDE', 'LAT'],
                'longitude': ['LONGITUDE', 'LONG', 'LNG'],
            },
            'focos': {
                'n_foco': ['Nº FOCO', 'N FOCO', 'NUMERO FOCO', 'FOCO', 'N° FOCO'],
                'regional': ['REGIONAL'],
                'municipio': ['MUNICÍPIO', 'MUNICIPIO'],
                'bairro': ['LOCALIDADE', 'BAIRRO / LOCALIDADE', 'BAIRRO'],
                'localidade': ['LOCALIDADE', 'BAIRRO / LOCALIDADE', 'BAIRRO'],
                'rua_numero': ['RUA/NÚMERO', 'RUA/NUMERO', 'ENDEREÇO', 'ENDERECO', 'LOGRADOURO'],
                'endereco': ['RUA/NÚMERO', 'RUA/NUMERO', 'ENDEREÇO', 'ENDERECO', 'LOGRADOURO'],
                'complemento': ['COMPLEMENTO'],
                'quarteirao': ['QUARTEIRÃO', 'QUARTEIRAO'],
                'imovel': ['IMÓVEL', 'IMOVEL'],
                'deposito': ['DEPÓSITO', 'DEPOSITO'],
                'tipo_atividade': ['TIPO DE ATIVIDADE', 'TIPO ATIVIDADE', 'ATIVIDADE'],
                'data_coleta': ['DATA DA COLETA', 'DATA COLETA'],
                'data_entrada': ['DATA DE ENTRADA', 'DATA ENTRADA'],
                'data_exame': ['DATA DO EXAME', 'DATA EXAME'],
                'a_aegypti_form_aquaticas': ['A. AEGYPTI FORMAS AQUÁTICAS', 'A. AEGYPTI FORMAS AQUATICAS'],
                'a_aegypti_form_adultas': ['A. AEGYPTI FORMAS ADULTAS'],
                'a_albopictus_form_aquaticas': ['A. ALBOPICTUS FORMAS AQUÁTICAS', 'A. ALBOPICTUS FORMAS AQUATICAS'],
                'a_albopictus_form_adultas': ['A. ALBOPICTUS FORMAS ADULTAS'],
                'ovo_a_aegypti': ['A. AEGYPTI OVOS', 'OVOS A. AEGYPTI'],
                'latitude': ['LATITUDE', 'LAT'],
                'longitude': ['LONGITUDE', 'LONG', 'LNG'],
            },
            'armadilhas': {
                'tipo_armadilha': ['TIPO ARMADILHA', 'ARMADILHA'],
                'numero': ['NÚMERO', 'NUMERO', 'Nº'],
                'municipio': ['MUNICÍPIO', 'MUNICIPIO'],
                'bairro': ['BAIRRO', 'LOCALIDADE', 'BAIRRO / LOCALIDADE'],
                'localidade': ['BAIRRO', 'LOCALIDADE', 'BAIRRO / LOCALIDADE'],
                'endereco': ['RUA/NÚMERO', 'ENDEREÇO', 'ENDERECO', 'LOGRADOURO'],
                'complemento': ['COMPLEMENTO'],
                'quarteiroes': ['QUARTEIRÃO', 'QUARTEIRAO', 'QUARTEIRÕES'],
                'tipo_imovel': ['TIPO IMÓVEL', 'IMÓVEL', 'IMOVEL'],
                'latitude': ['LATITUDE', 'LAT'],
                'longitude': ['LONGITUDE', 'LONG', 'LNG'],
            },
        }

        de_para_ativo = SINONIMOS_POR_TIPO.get(tipo_planilha, {})
        mapeamento_sugerido = {}

        for campo_bd in campos_banco.keys():
            mapeado = False
            sinonimos = de_para_ativo.get(campo_bd, [])

            for s in sinonimos:
                s_norm = _normalizar_texto(s)
                for col in colunas_planilha:
                    if str(col).strip().upper() == str(s).strip().upper() or _normalizar_texto(col) == s_norm:
                        mapeamento_sugerido[campo_bd] = col
                        mapeado = True
                        break
                if mapeado:
                    break

            if not mapeado:
                chave_norm = _normalizar_texto(campo_bd)
                for col in colunas_planilha:
                    if _normalizar_texto(col) == chave_norm:
                        mapeamento_sugerido[campo_bd] = col
                        mapeado = True
                        break

            if not mapeado:
                mapeamento_sugerido[campo_bd] = None

        return Response({
            'colunas_planilha': colunas_planilha,
            'campos_banco': campos_banco,
            'mapeamento_sugerido': mapeamento_sugerido,
        })

    except Exception as e:
        return JsonResponse({'erro': f'Falha ao ler cabeçalho: {str(e)}'}, status=400)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def upload_pontos_estrategicos(request):
    arquivo = request.FILES.get("pontos")
    celula_cabecalho = request.POST.get("celula_cabecalho", None)
    mapeamento_dict = _parse_mapeamento(request)

    if not arquivo:
        return JsonResponse({"erro": "Arquivo de pontos não enviado"}, status=400)

    job = LogSincronizacao.objects.create(tipo="pontos", nome_arquivo=arquivo.name, status="na_fila")
    caminho = _salvar_arquivo_temporario(job.id, arquivo)

    task_processar_pontos.delay(
        job.id,
        caminho,
        celula_cabecalho=celula_cabecalho,
        mapeamento_customizado=mapeamento_dict,
    )
    return JsonResponse({"sucesso": True, "job_id": job.id})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def upload_focos(request):
    arquivo = request.FILES.get("focos")
    celula_cabecalho = request.POST.get("celula_cabecalho", None)
    mapeamento_dict = _parse_mapeamento(request)

    if not arquivo:
        return JsonResponse({"erro": "Arquivo de focos não enviado"}, status=400)

    job = LogSincronizacao.objects.create(tipo="focos", nome_arquivo=arquivo.name, status="na_fila")
    caminho = _salvar_arquivo_temporario(job.id, arquivo)

    task_processar_focos.delay(
        job.id,
        caminho,
        celula_cabecalho=celula_cabecalho,
        mapeamento_customizado=mapeamento_dict,
    )
    return JsonResponse({"sucesso": True, "job_id": job.id})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def upload_armadilhas(request):
    arquivo = request.FILES.get("armadilhas")
    celula_cabecalho = request.POST.get("celula_cabecalho", None)
    mapeamento_dict = _parse_mapeamento(request)

    if not arquivo:
        return JsonResponse({"erro": "Arquivo de armadilhas não enviado"}, status=400)

    job = LogSincronizacao.objects.create(tipo="armadilhas", nome_arquivo=arquivo.name, status="na_fila")
    caminho = _salvar_arquivo_temporario(job.id, arquivo)

    task_processar_armadilhas.delay(
        job.id,
        caminho,
        celula_cabecalho=celula_cabecalho,
        mapeamento_customizado=mapeamento_dict,
    )
    return JsonResponse({"sucesso": True, "job_id": job.id})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def upload_ovitrampas(request):
    arquivo = request.FILES.get("ovitrampas") or request.FILES.get("arquivo")
    celula_cabecalho = request.POST.get("celula_cabecalho", None)
    mapeamento_dict = _parse_mapeamento(request)

    if not arquivo:
        return JsonResponse({"erro": "Arquivo de ovitrampas não enviado"}, status=400)

    job = LogSincronizacao.objects.create(tipo="ovitrampas", nome_arquivo=arquivo.name, status="na_fila")
    caminho = _salvar_arquivo_temporario(job.id, arquivo)

    task_processar_ovitrampas.delay(
        job.id,
        caminho,
        celula_cabecalho=celula_cabecalho,
        mapeamento_customizado=mapeamento_dict,
    )
    return JsonResponse({"sucesso": True, "job_id": job.id})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def disparar_geoprocessamento(request):
    job = LogSincronizacao.objects.create(
        tipo="geoprocessamento",
        nome_arquivo="N/A",
        status="processando",
        mensagem="Iniciando geoprocessamento dos endereços...",
    )

    task_geoprocessar_pendentes.delay(job.id)

    return JsonResponse({
        "status": "sucesso",
        "message": "Geoprocessamento iniciado em segundo plano!",
        "job_id": job.id,
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def sincronizar_oficial_api(request):
    """Dispara a sincronização assíncrona TEMP -> OFICIAL via Celery"""
    try:
        from .tasks import task_sincronizar_oficial

        job = LogSincronizacao.objects.create(
            tipo="sincronizacao",
            nome_arquivo="Sincronização Geral",
            status="processando",
            progresso=0,
            mensagem="Iniciando sincronização entre bancos...",
        )

        task_sincronizar_oficial.delay(job.id)
        return JsonResponse({"sucesso": True, "job_id": job.id})

    except Exception as e:
        return JsonResponse({"status": "erro", "mensagem": str(e)}, status=500)