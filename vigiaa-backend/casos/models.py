from django.db import models


class Caso(models.Model):
    cidade = models.CharField(max_length=100)
    quantidade = models.IntegerField()
    data = models.DateField()
