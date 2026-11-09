import uuid
from django.core.cache import cache

TTL = 60 * 60 * 6  # 6h

def _key(job_id):
    return f"job_status_{job_id}"

def criar_job(tipo="", nome_arquivo=""):
    job_id = uuid.uuid4().hex
    cache.set(_key(job_id), {
        "status": "na_fila", "progresso": 0, "mensagem": "Na fila...",
        "tipo": tipo, "arquivo": nome_arquivo,
    }, TTL)
    return job_id

def atualizar_job(job_id, **campos):
    dados = cache.get(_key(job_id)) or {}
    dados.update(campos)
    cache.set(_key(job_id), dados, TTL)

class JobLog:
    """Mesma interface do model: .status, .progresso, .mensagem e .save()"""
    def __init__(self, job_id):
        self.job_id = job_id
        d = cache.get(_key(job_id)) or {}
        self.status = d.get("status", "na_fila")
        self.progresso = d.get("progresso", 0)
        self.mensagem = d.get("mensagem", "")

    def save(self, update_fields=None):
        atualizar_job(self.job_id, status=self.status,
                      progresso=self.progresso, mensagem=self.mensagem)