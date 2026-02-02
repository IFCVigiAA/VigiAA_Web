from django.contrib import admin
from .models import (
    Caso,
    CasoPositivo,
    Foco,
    Armadilha,
    PontoEstrategico,
    Importacao
)

admin.site.register(Caso)
admin.site.register(CasoPositivo)
admin.site.register(Foco)
admin.site.register(Armadilha)
admin.site.register(PontoEstrategico)
admin.site.register(Importacao)