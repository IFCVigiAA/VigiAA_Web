from django.contrib import admin
from .models import (
    CasoPositivo,
    Foco,
    Armadilha,
    PontoEstrategico,
)

admin.site.register(CasoPositivo)
admin.site.register(Foco)
admin.site.register(Armadilha)
admin.site.register(PontoEstrategico)
