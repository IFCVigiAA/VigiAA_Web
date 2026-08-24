import os
import re
import json
import pandas as pd
from difflib import get_close_matches
import unicodedata
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
        'resultado': 'Resultado',
        'aplicacao': 'Data de Aplicação',
        'agentes': 'Agente(s) Responsável(is)',
        'prim_visita': '1ª Visita',
        'situacao': 'Situação do Caso',
        'observacoes': 'Observações',
    },
    'pontos': {
        'municipio': 'Município',
        'localidade': 'Localidade / Bairro',
        'endereco': 'Rua / Logradouro',
        'numero': 'Número do Imóvel (Endereço)',
        'complemento': 'Complemento',
        'quarteiroes': 'Quarteirão / Quarteirões',
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
        'a_aegypti_form_aquaticas': 'A. Aegypti (Formas Aquáticas)',
        'a_albopictus_form_aquaticas': 'A. Albopictus (Formas Aquáticas)',
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



def _normalizar_texto(texto):
    if pd.isna(texto) or texto is None:
        return ""
    s = str(texto).strip().lower()
    s = ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
    s = re.sub(r'[.ªº]', '', s)
    return s.replace(' ', '_')

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def extrair_cabecalho_e_sugerir(request):
    arquivo = (
        request.FILES.get("arquivo") 
        or (hasattr(request, 'data') and request.data.get("arquivo"))
    )
    celula_cabecalho = (
        request.POST.get("celula_cabecalho") 
        or (hasattr(request, 'data') and request.data.get("celula_cabecalho"))
    )
    
    # Garante a captura correta do tipo
    tipo_planilha = str(
        request.data.get("tipo") 
        or request.POST.get("tipo") 
        or "casos"
    ).strip().lower()

    if not arquivo:
        return JsonResponse({"erro": "Nenhum arquivo enviado"}, status=400)

    try:
        engine = 'odf' if arquivo.name.endswith('.ods') else None
        h_idx = None

        if celula_cabecalho:
            match = re.search(r'\d+', str(celula_cabecalho))
            if match:
                h_idx = max(0, int(match.group()) - 1)

        # Varredura inteligente das primeiras 20 linhas
        if h_idx is None:
            df_temp = pd.read_excel(arquivo, header=None, nrows=20, engine=engine)
            
            # Marcadores específicos de cada tipo de tabela (evita pegar cabeçalhos institucionais)
            marcadores_por_tipo = {
                'focos': ["Nº FOCO", "N FOCO", "REGIONAL", "ATIVIDADE", "DATA DA COLETA", "DATA DE ENTRADA"],
                'armadilhas': ["TIPO ARMADILHA", "TIPO IMÓVEL", "TIPO IMOVEL", "NÚMERO", "NUMERO"],
                'pontos': ["PONTO", "QUARTEIRÕES", "QUARTEIROES", "COMPLEMENTO"],
                'casos': ["SINAN", "PACIENTE", "INÍCIO SINTOMAS", "INICIO SINTOMAS", "DATA NOT"]
            }
            
            termos_alvo = marcadores_por_tipo.get(tipo_planilha, [])
            termos_gerais = ["SINAN", "Nº FOCO", "N FOCO", "REGIONAL", "TIPO ARMADILHA", "QUARTEIRÃO", "PACIENTE"]

            for i, row in df_temp.iterrows():
                # Conta quantas colunas não-nulas existem na linha
                celulas_texto = [str(x).upper().strip() for x in row.values if pd.notna(x) and str(x).strip() != '']
                linha_completa = " ".join(celulas_texto)
                
                # Cabeçalhos institucionais costumam ter apenas 1 célula preenchida
                # Cabeçalhos reais têm múltiplas colunas preenchidas (> 2)
                if len(celulas_texto) >= 3:
                    if any(t in linha_completa for t in termos_alvo) or any(t in linha_completa for t in termos_gerais):
                        h_idx = i
                        break

            if h_idx is None:
                # Fallback: pega a primeira linha com mais de 3 colunas preenchidas
                for i, row in df_temp.iterrows():
                    validos = [x for x in row.values if pd.notna(x) and str(x).strip() != '']
                    if len(validos) >= 4:
                        h_idx = i
                        break
                if h_idx is None:
                    h_idx = 0

        # Lê apenas 2 linhas a partir do cabeçalho detectado
        arquivo.seek(0)
        df = pd.read_excel(arquivo, header=h_idx, nrows=2, engine=engine)
        
        colunas_planilha = [
            str(c).replace('\n', ' ').strip() 
            for c in df.columns 
            if not str(c).startswith('Unnamed') and str(c).strip() != ''
        ]

        # Resgata os campos do banco garantindo fallback seguro
        campos_banco = CAMPOS_BANCO_POR_TIPO.get(tipo_planilha)
        if not campos_banco:
            # Fallback caso a chave venha como 'foco' em vez de 'focos'
            for k in CAMPOS_BANCO_POR_TIPO:
                if k in tipo_planilha or tipo_planilha in k:
                    campos_banco = CAMPOS_BANCO_POR_TIPO[k]
                    break
        if not campos_banco:
            campos_banco = CAMPOS_BANCO_POR_TIPO['casos']

        # Fuzzy matching
        mapeamento_sugerido = {}
        colunas_norm = {
            _normalizar_texto(col): col 
            for col in colunas_planilha
        }

        for campo_bd, label in campos_banco.items():
            chave_busca = _normalizar_texto(campo_bd)
            matches = get_close_matches(chave_busca, colunas_norm.keys(), n=1, cutoff=0.3)
            if matches:
                mapeamento_sugerido[campo_bd] = colunas_norm[matches[0]]
            else:
                mapeamento_sugerido[campo_bd] = None

        print(f"\n{'='*50}")
        print(f">>> [EXTRAIR CABEÇALHO] Tipo: {tipo_planilha} | Linha encontrada: {h_idx}")
        print(f">>> [EXTRAIR CABEÇALHO] Colunas extraídas ({len(colunas_planilha)}): {colunas_planilha}")
        print(f">>> [EXTRAIR CABEÇALHO] Campos do Banco ({len(campos_banco)}): {list(campos_banco.keys())}")
        print(f"{'='*50}\n", flush=True)

        return Response({
            "colunas_planilha": colunas_planilha,
            "campos_banco": campos_banco,
            "mapeamento_sugerido": mapeamento_sugerido
        })

    except Exception as e:
        print(f"❌ Erro ao extrair cabeçalho: {e}", flush=True)
        return JsonResponse({"erro": f"Falha ao ler cabeçalho: {str(e)}"}, status=400)


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