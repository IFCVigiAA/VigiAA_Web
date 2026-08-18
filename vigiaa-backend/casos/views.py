import os
import re
import json
import pandas as pd
from difflib import get_close_matches

from django.conf import settings
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import LogSincronizacao
from .tasks import (
    task_processar_positivos, 
    task_processar_pontos, 
    task_processar_focos, 
    task_processar_armadilhas,
    task_geoprocessar_pendentes
)

# Dicionários de colunas esperadas pelo Banco para cada tipo de planilha
CAMPOS_BANCO_POR_TIPO = {
    'casos': {
        'nome': 'Nome do Paciente',
        'endereco': 'Endereço Completo',
        'bairro': 'Bairro',
        'sinan': 'Número do SINAN',
        'inicio_sintomas': 'Data de Início dos Sintomas',
        'notificacao': 'Data da Notificação',
        'data_nasc': 'Data de Nascimento',
        'local_atendimento': 'Local de Atendimento',
        'nome_mae': 'Nome da Mãe',
        'resultado': 'Resultado (Ex: Positivo)'
    },
    'pontos': {
        'numero': 'Número / Código do Ponto',
        'municipio': 'Município',
        'localidade': 'Localidade / Bairro',
        'endereco': 'Endereço / Logradouro',
        'quarteiroes': 'Quarteirões',
        'complemento': 'Complemento',
        'latitude': 'Latitude',
        'longitude': 'Longitude'
    },
    'focos': {
        'n_foco': 'Nº do Foco',
        'regional': 'Regional',
        'municipio': 'Município',
        'localidade': 'Localidade / Bairro',
        'rua_numero': 'Rua / Número',
        'complemento': 'Complemento',
        'quarteirao': 'Quarteirão',
        'imovel': 'Tipo de Imóvel',
        'deposito': 'Tipo de Depósito',
        'tipo_atividade': 'Tipo de Atividade',
        'data_coleta': 'Data da Coleta',
        'data_entrada': 'Data de Entrada',
        'data_exame': 'Data do Exame',
        'a_aegypti_form_aquaticas': 'Aedes Aegypti (Formas Aquáticas)',
        'a_aegypti_form_adultas': 'Aedes Aegypti (Formas Adultas)',
        'a_albopictus_form_aquaticas': 'Aedes Albopictus (Formas Aquáticas)',
        'a_albopictus_form_adultas': 'Aedes Albopictus (Formas Adultas)',
        'ovo_a_aegypti': 'Ovos Aedes Aegypti',
        'latitude': 'Latitude',
        'longitude': 'Longitude'
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
    }
}


# --- FUNÇÕES AUXILIARES ---

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
    # Tenta resgatar pelo request.data (padrão DRF) e fallback para request.POST
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


# --- VIEWS DE AUTENTICAÇÃO E STATUS ---

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
        proc = LogSincronizacao.objects.get(id=job_id)
        return JsonResponse({
            "status": proc.status,
            "progresso": proc.progresso,
            "mensagem": proc.mensagem
        })
    except LogSincronizacao.DoesNotExist:
        return JsonResponse({"erro": "Job não encontrado"}, status=404)


# --- EXTRAÇÃO DE CABEÇALHO E SUGESTÃO ---

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def extrair_cabecalho_e_sugerir(request):
    arquivo = request.FILES.get("arquivo")
    celula_cabecalho = request.POST.get("celula_cabecalho", None)
    tipo_planilha = request.POST.get("tipo", "casos")

    if not arquivo:
        return JsonResponse({"erro": "Nenhum arquivo enviado"}, status=400)

    try:
        h_idx = None
        if celula_cabecalho:
            match = re.search(r'\d+', str(celula_cabecalho))
            if match:
                h_idx = max(0, int(match.group()) - 1)

        engine = 'odf' if arquivo.name.endswith('.ods') else None

        if h_idx is None:
            df_temp = pd.read_excel(arquivo, header=None, engine=engine)
            h_idx = next(
                (i for i, row in df_temp.iterrows() if any(
                    k in str(x).upper() for x in row for k in ["NOME", "SINAN", "NÚMERO", "NUMERO", "FOCO", "ARMADILHA"]
                )), 
                0
            )

        arquivo.seek(0)
        df = pd.read_excel(arquivo, header=h_idx, nrows=2, engine=engine)
        colunas_planilha = [str(c).strip() for c in df.columns if not str(c).startswith('Unnamed')]

        campos_banco = CAMPOS_BANCO_POR_TIPO.get(tipo_planilha, CAMPOS_BANCO_POR_TIPO['casos'])

        mapeamento_sugerido = {}
        colunas_norm = {col.lower().replace(' ', '').replace('_', ''): col for col in colunas_planilha}

        for campo_bd, label in campos_banco.items():
            matches = get_close_matches(campo_bd, colunas_norm.keys(), n=1, cutoff=0.3)
            if matches:
                mapeamento_sugerido[campo_bd] = colunas_norm[matches[0]]
            else:
                mapeamento_sugerido[campo_bd] = None

        return Response({
            "colunas_planilha": colunas_planilha,
            "campos_banco": campos_banco,
            "mapeamento_sugerido": mapeamento_sugerido
        })

    except Exception as e:
        return JsonResponse({"erro": f"Falha ao ler cabeçalho da planilha: {str(e)}"}, status=400)


# --- VIEWS DE UPLOAD ---

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def upload_casos_positivos(request):
    # Suporte a DRF request.data e request.FILES
    arquivo = (
        request.FILES.get("positivos") 
        or request.FILES.get("casos")
        or request.data.get("positivos")
        or request.data.get("casos")
    )
    celula_cabecalho = request.data.get("celula_cabecalho") or request.POST.get("celula_cabecalho", None)
    mapeamento_dict = _parse_mapeamento(request)

    print("\n" + "="*60, flush=True)
    print(">>> [VIEWS.PY] MAPEAMENTO ENCONTRADO:", mapeamento_dict, flush=True)
    print("="*60 + "\n", flush=True)

    if not arquivo:
        return JsonResponse({"erro": "Arquivo de positivos não enviado"}, status=400)

    job = LogSincronizacao.objects.create(tipo="positivos", nome_arquivo=arquivo.name, status="na_fila")
    caminho = _salvar_arquivo_temporario(job.id, arquivo)
    
    task_processar_positivos.delay(
        job.id, 
        caminho, 
        celula_cabecalho=celula_cabecalho, 
        mapeamento_customizado=mapeamento_dict
    )
    
    return JsonResponse({"sucesso": True, "job_id": job.id})


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


# --- VIEW DE GEOPROCESSAMENTO ---

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