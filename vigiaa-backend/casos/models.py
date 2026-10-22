from django.contrib.gis.db import models
from django.db.models import Q


class Caso(models.Model):
    cidade = models.CharField(max_length=100)
    quantidade = models.IntegerField()
    data = models.DateField()

    def __str__(self):
        return f"{self.cidade} - {self.data}"


class CasoPositivo(models.Model):
    local_atendimento = models.CharField(max_length=100, null=True, blank=True)
    notificacao = models.DateField(null=True, blank=True)
    inicio_sintomas = models.DateField(null=True, blank=True)
    sinan = models.BigIntegerField(null=True, blank=True)
    nome = models.CharField(max_length=150, null=True, blank=True)
    data_nasc = models.DateField(null=True, blank=True)
    sexo = models.CharField(max_length=20, null=True, blank=True)
    endereco = models.CharField(max_length=255, null=True, blank=True)
    bairro = models.CharField(max_length=100, null=True, blank=True)
    resultado = models.CharField(max_length=50, null=True, blank=True)
    situacao = models.CharField(max_length=50, null=True, blank=True)
    observacoes = models.TextField(null=True, blank=True)
    geometry = models.PointField(srid=4674, null=True, blank=True)
    hash_registro = models.CharField(max_length=64, unique=True, null=True, blank=True)

    class Meta:
        db_table = 'casos_positivos'
        constraints = [
            models.UniqueConstraint(
                fields=["hash_registro"],
                condition=Q(hash_registro__isnull=False),
                name="uq_casos_positivos_hash_registro",
            )
        ]

    def __str__(self):
        return f"SINAN {self.sinan}"


class Foco(models.Model):
    n_foco = models.CharField(max_length=50, null=True, blank=True)
    regional = models.CharField(max_length=100, null=True, blank=True)
    municipio = models.CharField(max_length=100, null=True, blank=True)
    localidade = models.CharField(max_length=100, null=True, blank=True)
    rua_numero = models.CharField(max_length=255, null=True, blank=True)
    complemento = models.CharField(max_length=100, null=True, blank=True)
    quarteirao = models.CharField(max_length=50, null=True, blank=True)
    imovel = models.CharField(max_length=100, null=True, blank=True)
    deposito = models.CharField(max_length=100, null=True, blank=True)
    tipo_atividade = models.CharField(max_length=100, null=True, blank=True)
    data_coleta = models.DateField(null=True, blank=True)
    data_entrada = models.DateField(null=True, blank=True)
    data_exame = models.DateField(null=True, blank=True)
    a_aegypti_form_aquaticas = models.IntegerField(default=0)
    a_albopictus_form_aquaticas = models.IntegerField(default=0)
    latitude = models.CharField(max_length=50, null=True, blank=True)
    longitude = models.CharField(max_length=50, null=True, blank=True)
    geometry = models.PointField(srid=4674, null=True, blank=True)
    hash_registro = models.CharField(max_length=64, unique=True, null=True, blank=True)

    class Meta:
        db_table = 'focos_aedes'
        constraints = [
            models.UniqueConstraint(
                fields=["hash_registro"],
                condition=Q(hash_registro__isnull=False),
                name="uq_focos_aedes_hash_registro",
            )
        ]

    def __str__(self):
        return f"Foco {self.n_foco}"


class PontoEstrategico(models.Model):
    n_pe = models.CharField(max_length=50, null=True, blank=True)
    regional = models.CharField(max_length=100, null=True, blank=True)
    municipio = models.CharField(max_length=100, null=True, blank=True)
    localidade = models.CharField(max_length=100, null=True, blank=True)
    endereco = models.CharField(max_length=255, null=True, blank=True)
    complemento = models.CharField(max_length=100, null=True, blank=True)
    quarteiroes = models.CharField(max_length=50, null=True, blank=True)
    imovel = models.CharField(max_length=100, null=True, blank=True)
    deposito = models.CharField(max_length=100, null=True, blank=True)
    tipo_atividade = models.CharField(max_length=100, null=True, blank=True)
    data_coleta = models.DateField(null=True, blank=True)
    data_entrada = models.DateField(null=True, blank=True)
    data_exame = models.DateField(null=True, blank=True)
    a_aegypti_form_aquaticas = models.IntegerField(default=0)
    a_albopictus_form_aquaticas = models.IntegerField(default=0)
    latitude = models.CharField(max_length=50, null=True, blank=True)
    longitude = models.CharField(max_length=50, null=True, blank=True)
    geometry = models.PointField(srid=4674, null=True, blank=True)
    hash_registro = models.CharField(max_length=64, unique=True, null=True, blank=True)

    class Meta:
        db_table = 'pontos_estrategicos'
        constraints = [
            models.UniqueConstraint(
                fields=["hash_registro"],
                condition=Q(hash_registro__isnull=False),
                name="uq_pontos_estrategicos_hash_registro",
            )
        ]

    def __str__(self):
        return f"Ponto {self.numero}"


class Armadilha(models.Model):
    numero = models.CharField(max_length=50)
    municipio = models.CharField(max_length=100)
    localidade = models.CharField(max_length=100)
    endereco = models.CharField(max_length=150)
    complemento = models.CharField(max_length=255, null=True, blank=True)
    quarteiroes = models.CharField(max_length=50)
    tipo_imovel = models.CharField(max_length=50)
    tipo_armadilha = models.CharField(max_length=50)
    geometry = models.PointField(srid=4674)
    hash_registro = models.CharField(max_length=64, null=True, blank=True, db_index=True)
    class Meta:
        db_table = "relat_arm"
        constraints = [
            models.UniqueConstraint(
                fields=["hash_registro"],
                condition=Q(hash_registro__isnull=False),
                name="uq_relat_arm_hash_registro",
            )
        ]

    def __str__(self):
        return f"Armadilha {self.numero} - {self.tipo_armadilha}"


class LogSincronizacao(models.Model):
    tipo = models.CharField(max_length=50)
    nome_arquivo = models.CharField(max_length=255)
    hash = models.CharField(max_length=64)

    status = models.CharField(max_length=50, default="iniciando")
    progresso = models.IntegerField(default=0)
    mensagem = models.TextField(blank=True)

    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "logs_sincronizacao"

    def __str__(self):
        return f"{self.tipo} - {self.nome_arquivo}"

class CasoPositivoTemp(models.Model):
    local_atendimento = models.CharField(max_length=100, null=True, blank=True)
    notificacao = models.DateField(null=True, blank=True)
    inicio_sintomas = models.DateField(null=True, blank=True)
    sinan = models.BigIntegerField(null=True, blank=True)
    nome = models.CharField(max_length=150, null=True, blank=True)
    data_nasc = models.DateField(null=True, blank=True)
    sexo = models.CharField(max_length=20, null=True, blank=True)
    endereco = models.CharField(max_length=255, null=True, blank=True)
    bairro = models.CharField(max_length=100, null=True, blank=True)
    resultado = models.CharField(max_length=50, null=True, blank=True)
    latitude = models.CharField(max_length=50, null=True, blank=True)
    longitude = models.CharField(max_length=50, null=True, blank=True)
    situacao = models.CharField(max_length=50, null=True, blank=True)
    observacoes = models.TextField(null=True, blank=True)
    hash_registro = models.CharField(max_length=64, unique=True, null=True, blank=True)

    class Meta:
        db_table = 'casos_positivos_temp'
        managed = False


class CasoPositivoTempGL(models.Model):
    local_atendimento = models.CharField(max_length=100, null=True, blank=True)
    notificacao = models.DateField(null=True, blank=True)
    inicio_sintomas = models.DateField(null=True, blank=True)
    sinan = models.BigIntegerField(null=True, blank=True)
    nome = models.CharField(max_length=150, null=True, blank=True)
    data_nasc = models.DateField(null=True, blank=True)
    sexo = models.CharField(max_length=20, null=True, blank=True)
    endereco = models.CharField(max_length=255, null=True, blank=True)
    bairro = models.CharField(max_length=100, null=True, blank=True)
    resultado = models.CharField(max_length=50, null=True, blank=True)
    situacao = models.CharField(max_length=50, null=True, blank=True)
    observacoes = models.TextField(null=True, blank=True)
    geometry = models.PointField(srid=4674, null=True, blank=True)
    hash_registro = models.CharField(max_length=64, unique=True, null=True, blank=True)

    class Meta:
        db_table = 'casos_positivos_temp_gl'
        managed = False


class FocoTemp(models.Model):
    n_foco = models.CharField(max_length=50, null=True, blank=True)
    regional = models.CharField(max_length=100, null=True, blank=True)
    municipio = models.CharField(max_length=100, null=True, blank=True)
    localidade = models.CharField(max_length=100, null=True, blank=True)
    rua_numero = models.CharField(max_length=255, null=True, blank=True)
    complemento = models.CharField(max_length=100, null=True, blank=True)
    quarteirao = models.CharField(max_length=50, null=True, blank=True)
    imovel = models.CharField(max_length=100, null=True, blank=True)
    deposito = models.CharField(max_length=100, null=True, blank=True)
    tipo_atividade = models.CharField(max_length=100, null=True, blank=True)
    data_coleta = models.DateField(null=True, blank=True)
    data_entrada = models.DateField(null=True, blank=True)
    data_exame = models.DateField(null=True, blank=True)
    a_aegypti_form_aquaticas = models.IntegerField(default=0)
    a_albopictus_form_aquaticas = models.IntegerField(default=0)
    latitude = models.CharField(max_length=50, null=True, blank=True)
    longitude = models.CharField(max_length=50, null=True, blank=True)
    geometry = models.PointField(srid=4674, null=True, blank=True)
    hash_registro = models.CharField(max_length=64, unique=True, null=True, blank=True)

    class Meta:
        db_table = 'focos_aedes_temp'
        managed = False

class PontoEstrategicoTemp(models.Model):
    n_pe = models.CharField(max_length=50, null=True, blank=True)
    regional = models.CharField(max_length=100, null=True, blank=True)
    municipio = models.CharField(max_length=100, null=True, blank=True)
    localidade = models.CharField(max_length=100, null=True, blank=True)
    endereco = models.CharField(max_length=255, null=True, blank=True)
    complemento = models.CharField(max_length=100, null=True, blank=True)
    quarteiroes = models.CharField(max_length=50, null=True, blank=True)
    imovel = models.CharField(max_length=100, null=True, blank=True)
    deposito = models.CharField(max_length=100, null=True, blank=True)
    tipo_atividade = models.CharField(max_length=100, null=True, blank=True)
    data_coleta = models.DateField(null=True, blank=True)
    data_entrada = models.DateField(null=True, blank=True)
    data_exame = models.DateField(null=True, blank=True)
    a_aegypti_form_aquaticas = models.IntegerField(default=0)
    a_albopictus_form_aquaticas = models.IntegerField(default=0)
    latitude = models.CharField(max_length=50, null=True, blank=True)
    longitude = models.CharField(max_length=50, null=True, blank=True)
    geometry = models.PointField(srid=4674, null=True, blank=True)
    hash_registro = models.CharField(max_length=64, unique=True, null=True, blank=True)

    class Meta:
        db_table = 'pontos_estrategicos_temp'
        managed = False



class ArmadilhaTemp(models.Model):
    numero = models.CharField(max_length=50, null=True, blank=True)
    municipio = models.CharField(max_length=100, null=True, blank=True)
    localidade = models.CharField(max_length=100, null=True, blank=True)
    endereco = models.CharField(max_length=150, null=True, blank=True)
    complemento = models.CharField(max_length=225, null=True, blank=True)
    quarteiroes = models.CharField(max_length=50, null=True, blank=True)
    tipo_imovel = models.CharField(max_length=50, null=True, blank=True)
    tipo_armadilha = models.CharField(max_length=50, null=True, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    geometry = models.PointField(srid=4674, null=True, blank=True, editable=False)
    hash_registro = models.CharField(max_length=64, null=True, blank=True, db_index=True, editable=False)
    class Meta:
        db_table = "relat_arm_temp"
        managed = False

class Ovitrampa(models.Model):
    id_ovitrampa = models.CharField(max_length=50, null=True, blank=True)
    endereco = models.CharField(max_length=255, null=True, blank=True)
    numero = models.CharField(max_length=20, null=True, blank=True)
    complemento_tipo = models.CharField(max_length=100, null=True, blank=True)
    bairro = models.CharField(max_length=100, null=True, blank=True)
    localizacao = models.CharField(max_length=150, null=True, blank=True)
    setor_distrito = models.CharField(max_length=100, null=True, blank=True)
    responsavel = models.CharField(max_length=150, null=True, blank=True)
    quarteirao = models.CharField(max_length=50, null=True, blank=True)
    data_exame = models.DateField(null=True, blank=True)
    ovos_aegypti = models.IntegerField(null=True, blank=True, default=0)
    ovos_albopictus = models.IntegerField(null=True, blank=True, default=0)
    outros_ovos = models.IntegerField(null=True, blank=True, default=0)
    tipo = models.CharField(max_length=50, null=True, blank=True)
    acoes = models.TextField(null=True, blank=True)
    geometry = models.PointField(srid=4674, null=True, blank=True)
    hash_registro = models.CharField(max_length=64, null=True, blank=True, db_index=True)

    class Meta:
        db_table = "ovitrampas"
        managed = False


class OvitrampaTemp(models.Model):
    id_ovitrampa = models.CharField(max_length=50, null=True, blank=True)
    endereco = models.CharField(max_length=255, null=True, blank=True)
    numero = models.CharField(max_length=20, null=True, blank=True)
    complemento_tipo = models.CharField(max_length=100, null=True, blank=True)
    bairro = models.CharField(max_length=100, null=True, blank=True)
    localizacao = models.CharField(max_length=150, null=True, blank=True)
    setor_distrito = models.CharField(max_length=100, null=True, blank=True)
    responsavel = models.CharField(max_length=150, null=True, blank=True)
    quarteirao = models.CharField(max_length=50, null=True, blank=True)
    data_exame = models.DateField(null=True, blank=True)
    ovos_aegypti = models.IntegerField(null=True, blank=True, default=0)
    ovos_albopictus = models.IntegerField(null=True, blank=True, default=0)
    outros_ovos = models.IntegerField(null=True, blank=True, default=0)
    tipo = models.CharField(max_length=50, null=True, blank=True)
    latitude = models.CharField(max_length=100, null=True, blank=True)
    longitude = models.CharField(max_length=100, null=True, blank=True)
    acoes = models.TextField(null=True, blank=True)
    geometry = models.PointField(srid=4674, null=True, blank=True, editable=False)
    hash_registro = models.CharField(max_length=64, null=True, blank=True, db_index=True, editable=False)

    class Meta:
        db_table = "ovitrampas_temp"
        managed = False  