from django.shortcuts import render
from django.http import JsonResponse
from .models import Caso


def listar_casos(request):
    casos = list(Caso.objects.values())
    return JsonResponse(casos, safe=False)
