from django.contrib.gis.db import models


class Caso(models.Model):
    cidade = models.CharField(max_length=100)
    quantidade = models.IntegerField()
    data = models.DateField()

    def __str__(self):
        return f"{self.cidade} - {self.data}"


class CasoPositivo(models.Model):
    local_atendimento = models.CharField(max_length=100, null=True, blank=True)
    inicio_sintomas = models.DateField(null=True, blank=True)
    notificacao = models.DateField(null=True, blank=True)
    sinan = models.IntegerField(null=True, blank=True)
    bairro = models.CharField(max_length=50, null=True, blank=True)
    data_nasc = models.DateField(null=True, blank=True)
    observacoes = models.CharField(max_length=255, null=True, blank=True)
    resultado = models.CharField(max_length=50, null=True, blank=True)
    aplicacao = models.CharField(max_length=50, null=True, blank=True)
    agentes = models.CharField(max_length=100, null=True, blank=True)
    prim_visita = models.CharField(max_length=50, null=True, blank=True)
    situacao = models.CharField(max_length=255, null=True, blank=True)
    geometry = models.PointField(srid=4674)
    hash_registro = models.CharField(max_length=64, unique=True, db_index=True)
    class Meta:
        db_table = "casos_positivos"

    def __str__(self):
        return f"SINAN {self.sinan}"


class Foco(models.Model):
    n_foco = models.CharField(max_length=30)
    localidade = models.CharField(max_length=100)
    imovel = models.CharField(max_length=50)
    deposito = models.CharField(max_length=100)
    tipo_atividade = models.CharField(max_length=50)
    data_coleta = models.DateField()

    a_aegypti_form_aquaticas = models.IntegerField()
    a_aegypti_form_adultas = models.IntegerField()
    a_albopictus_form_aquaticas = models.IntegerField()
    a_albopictus_form_adultas = models.IntegerField()
    ovo_a_aegypti = models.IntegerField()

    geometry = models.PointField(srid=4674)

    class Meta:
        db_table = "focos_aedes"

    def __str__(self):
        return f"Foco {self.n_foco}"


class PontoEstrategico(models.Model):
    numero = models.CharField(max_length=50)
    municipio = models.CharField(max_length=100)
    localidade = models.CharField(max_length=100)
    endereco = models.CharField(max_length=150)
    quarteiroes = models.CharField(max_length=50)
    complemento = models.CharField(max_length=100)
    geometry = models.PointField(srid=4674)

    class Meta:
        db_table = "pontos_estrategicos"

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

    class Meta:
        db_table = "relat_arm"

    def __str__(self):
        return f"Armadilha {self.numero} - {self.tipo_armadilha}"


class Importacao(models.Model):
    tipo = models.CharField(max_length=50)
    nome_arquivo = models.CharField(max_length=255)
    hash = models.CharField(max_length=64)
    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.tipo} - {self.nome_arquivo}"
