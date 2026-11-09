import os
import re
import json
from django.core.cache import cache
import pandas as pd
from difflib import get_close_matches
import unicodedata
from casos.utils.jobs import criar_job
from django.conf import settings
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.core.files.storage import FileSystemStorage
from rest_framework.permissions import IsAuthenticated
from .models import LogSincronizacao
from .tasks import (
    task_processar_positivos, 
    task_processar_pontos, 
    task_processar_focos, 
    task_processar_armadilhas,
    task_geoprocessar_pendentes,
    task_processar_ovitrampas
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
        'longitude': 'Longitude'
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
    }
}

# FUNÇÕES AUXILIARES 

def _salvar_arquivo_temporario(job_id, arquivo):
    """Salva o arquivo em media/temp_uploads para que o Celery possa acessá-lo"""
    path_dir = os.path.join(settings.MEDIA_ROOT, "temp_uploads")
    os.makedirs(path_dir, exist_ok=True)
    
    nome_seguro = f"{job_id}_{arquivo.name.replace(' ', '_')}"
    caminho_final = os.path.join(path_dir, nome_seguro)
    
    with open(caminho_final, 'wb+') as destination:
        for chunk in arquivo.chunks():
            destination.write(chunk)
    return caminho_final


def _parse_mapeamento(request):
    """Extrai e converte a string JSON vinda tanto do DRF (request.data) quanto do Django (request.POST)"""
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
    except Exception as e:
        print(f"⚠️ [VIEWS.PY] Erro ao converter JSON: {e}", flush=True)
        return None


def _normalizar_texto(texto):
    """Remove acentos, caracteres especiais e converte para caixa alta."""
    if not texto:
        return ""
    nfkd = unicodedata.normalize('NFKD', str(texto))
    sem_acento = "".join([c for c in nfkd if not unicodedata.combining(c)])
    return re.sub(r'[^A-Z0-9]', '', sem_acento.upper())


# VIEWS DE AUTENTICAÇÃO E STATUS 

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
            "mensagem": proc.mensagem
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
        job.id, caminho,
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
            val_str = str(val).replace('\n', ' ').strip()
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

        # Estrutura original mantida por tipo de planilha
        SINONIMOS_POR_TIPO = {
            'casos': {
                'local_atendimento': ['LOCAL NOTIFICAÇÃO', 'LOCAL NOTIFICACAO', 'LOCAL ATENDIMENTO'],
                'notificacao': ['DATA NOT.', 'DATA NOTIFICAÇÃO', 'DATA NOTIFICACAO'],
                'inicio_sintomas': ['INICIO SINTOMAS', 'INÍCIO SINTOMAS'],
                'sinan': ['SINAN', 'NÚMERO DO SINAN', 'NUMERO DO SINAN'],
                'nome': ['NOME COMPLETO', 'NOME', 'PACIENTE'],
                'data_nasc': ['NASCIMENTO', 'DATA DE NASCIMENTO', 'DATA NASC'],
                'sexo': ['SEXO', 'GÊNERO', 'GENERO'],
                'endereco': ['ENDEREÇO', 'ENDERECO', 'RUA/NÚMERO', 'RUA/NUMERO'],
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
                'setor_distrito': [
                    'SETOR/DISTRITO DA OVITRAMPA', 
                    'SETOR / DISTRITO DA OVITRAMPA', 
                    'SETOR/DISTRITO', 
                    'SETOR / DISTRITO', 
                    'SETOR', 
                    'DISTRITO'
                ],
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
                'codigo': ['Nº FOCO', 'N° FOCO', 'Nº PE / CÓDIGO', 'Nº PE', 'CÓDIGO PE', 'CÓDIGO', 'PE'],
                'numero': ['Nº FOCO', 'N° FOCO', 'Nº PE / CÓDIGO', 'Nº PE', 'CÓDIGO PE', 'CÓDIGO', 'PE'],
                'regional': ['REGIONAL'],
                'municipio': ['MUNICÍPIO', 'MUNICIPIO'],
                'bairro': ['LOCALIDADE', 'BAIRRO / LOCALIDADE', 'BAIRRO'],
                'localidade': ['LOCALIDADE', 'BAIRRO / LOCALIDADE', 'BAIRRO'],
                'endereco': ['RUA/NÚMERO', 'RUA/NUMERO', 'ENDEREÇO', 'ENDERECO'],
                'rua_numero': ['RUA/NÚMERO', 'RUA/NUMERO', 'ENDEREÇO', 'ENDERECO'],
                'complemento': ['COMPLEMENTO'],
                'quarteirao': ['QUARTEIRÃO', 'QUARTEIRAO', 'QUARTEIRÕES', 'QUARTEIROES', 'QUARTEIRAO(S)'],
                'quarteiroes': ['QUARTEIRÃO', 'QUARTEIRAO', 'QUARTEIRÕES', 'QUARTEIROES', 'QUARTEIRAO(S)'],
                'imovel': ['IMÓVEL', 'IMOVEL', 'TIPO IMÓVEL'],
                'deposito': ['DEPÓSITO', 'DEPOSITO'],
                'tipo_atividade': ['TIPO DE ATIVIDADE', 'TIPO ATIVIDADE', 'ATIVIDADE'],
                'atividade': ['TIPO DE ATIVIDADE', 'TIPO ATIVIDADE', 'ATIVIDADE'],
                'tipo': ['TIPO DE ATIVIDADE', 'TIPO ATIVIDADE', 'ATIVIDADE'],
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
                'rua_numero': ['RUA/NÚMERO', 'RUA/NUMERO', 'ENDEREÇO', 'ENDERECO'],
                'endereco': ['RUA/NÚMERO', 'RUA/NUMERO', 'ENDEREÇO', 'ENDERECO'],
                'complemento': ['COMPLEMENTO'],
                'quarteirao': ['QUARTEIRÃO', 'QUARTEIRAO'],
                'imovel': ['IMÓVEL', 'IMOVEL'],
                'deposito': ['DEPÓSITO', 'DEPOSITO'],
                'tipo_atividade': ['TIPO DE ATIVIDADE', 'TIPO ATIVIDADE', 'ATIVIDADE', 'TIPO DE ATIVIDADES'],
                'atividade': ['TIPO DE ATIVIDADE', 'TIPO ATIVIDADE', 'ATIVIDADE'],
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
                'endereco': ['RUA/NÚMERO', 'ENDEREÇO', 'ENDERECO'],
                'rua_numero': ['RUA/NÚMERO', 'ENDEREÇO', 'ENDERECO'],
                'complemento': ['COMPLEMENTO'],
                'quarteirao': ['QUARTEIRÃO', 'QUARTEIRAO'],
                'tipo_imovel': ['TIPO IMÓVEL', 'IMÓVEL', 'IMOVEL'],
                'imovel': ['TIPO IMÓVEL', 'IMÓVEL', 'IMOVEL'],
                'latitude': ['LATITUDE', 'LAT'],
                'longitude': ['LONGITUDE', 'LONG', 'LNG'],
            },
        }

        de_para_ativo = SINONIMOS_POR_TIPO.get(tipo_planilha, {})
        mapeamento_sugerido = {}

        colunas_norm_map = {_normalizar_texto(col): col for col in colunas_planilha}

        for campo_bd in campos_banco.keys():
            mapeado = False
            sinonimos = de_para_ativo.get(campo_bd, [])

            if 'ativ' in campo_bd.lower():
                sinonimos = list(set(sinonimos + ['TIPO DE ATIVIDADE', 'TIPO ATIVIDADE', 'ATIVIDADE']))

            if 'quart' in campo_bd.lower():
                sinonimos = list(set(sinonimos + ['QUARTEIRÃO', 'QUARTEIRAO', 'QUARTEIRÕES']))

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
        print(f'❌ Erro ao extrair cabeçalho: {e}', flush=True)
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
        mapeamento_customizado=mapeamento_dict
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
        mapeamento_customizado=mapeamento_dict
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
        mapeamento_customizado=mapeamento_dict
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
def upload_planilhas(request):
    """View genérica/legada mantida para compatibilidade de rotas antigas"""
    return upload_casos_positivos(request)


# --- VIEWS DE EXECUÇÃO / SINCRONIZAÇÃO ---

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def disparar_geoprocessamento(request):
    job = LogSincronizacao.objects.create(
        tipo="geoprocessamento", 
        nome_arquivo="N/A", 
        status="processando",
        mensagem="Iniciando geoprocessamento dos endereços..."
    )
    
    task_geoprocessar_pendentes.delay(job.id)
    
    return JsonResponse({
        "status": "sucesso", 
        "message": "Geoprocessamento iniciado em segundo plano!",
        "job_id": job.id
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def sincronizar_oficial_api(request):
    """Dispara a sincronização assíncrona TEMP -> OFICIAL via Celery"""
    try:
        job = LogSincronizacao.objects.create(
            tipo="sincronizacao",
            nome_arquivo="Sincronização Geral",
            status="processando",
            progresso=0,
            mensagem="Iniciando sincronização entre bancos..."
        )


        task_sincronizar_oficial.delay(job.id)


        return JsonResponse({"sucesso": True, "job_id": job.id})

    except Exception as e:
        return JsonResponse({"status": "erro", "mensagem": str(e)}, status=500)