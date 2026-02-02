from django.db import models


class Caso(models.Model):
    cidade = models.CharField(max_length=100)
    quantidade = models.IntegerField()
    data = models.DateField()

    def __str__(self):
        return f"{self.cidade} - {self.data}"


class CasoPositivo(models.Model):
    endereco = models.CharField(max_length=255)
    data_notificacao = models.DateField()
    sinan = models.CharField(max_length=50)

    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"SINAN {self.sinan}"


class Foco(models.Model):
    numero_foco = models.CharField(max_length=50)
    data_coleta = models.DateField()
    latitude = models.FloatField()
    longitude = models.FloatField()

    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Foco {self.numero_foco}"


class Armadilha(models.Model):
    tipo_armadilha = models.CharField(max_length=100)
    latitude = models.FloatField()
    longitude = models.FloatField()

    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.tipo_armadilha


class PontoEstrategico(models.Model):
    latitude = models.FloatField()
    longitude = models.FloatField()

    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Ponto ({self.latitude}, {self.longitude})"
    
class Importacao(models.Model):
    tipo = models.CharField(max_length=50)
    nome_arquivo = models.CharField(max_length=255)
    hash = models.CharField(max_length=64)
    criado_em = models.DateTimeField(auto_now_add=True)
