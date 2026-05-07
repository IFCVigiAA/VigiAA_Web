from django.core.management.base import BaseCommand
from django.db import transaction

from casos.models import CasoPositivo, Foco, PontoEstrategico, Armadilha
from casos.importadores._utils import hash_registro


class Command(BaseCommand):
    help = "Preenche hash_registro para dados existentes e remove duplicados que colidem."

    def handle(self, *args, **options):
        self._backfill_casos()
        self._backfill_focos()
        self._backfill_pontos()
        self._backfill_armadilhas()
        self.stdout.write(self.style.SUCCESS("✅ Backfill concluído."))

    def _geom_k(self, g):
        if not g:
            return ""
        return f"{round(g.x,6)},{round(g.y,6)}"

    def _backfill_casos(self):
        qs = CasoPositivo.objects.filter(hash_registro__isnull=True)
        updated = 0
        deleted = 0

        for c in qs.iterator(chunk_size=1000):
            h = hash_registro(
                "CASO_POSITIVO",
                c.sinan or "",
                c.notificacao.isoformat() if c.notificacao else "",
                c.inicio_sintomas.isoformat() if c.inicio_sintomas else "",
                c.bairro or "",
                self._geom_k(c.geometry),
                c.resultado or "",
            )

            if CasoPositivo.objects.filter(hash_registro=h).exclude(pk=c.pk).exists():
                c.delete()
                deleted += 1
                continue

            c.hash_registro = h
            c.save(update_fields=["hash_registro"])
            updated += 1

        self.stdout.write(f"Casos positivos: {updated} atualizados | {deleted} duplicados removidos")

    def _backfill_focos(self):
        qs = Foco.objects.filter(hash_registro__isnull=True)
        updated = 0
        deleted = 0

        for f in qs.iterator(chunk_size=1000):
            h = hash_registro(
                "FOCO",
                f.n_foco,
                f.localidade,
                f.imovel,
                f.deposito,
                f.tipo_atividade,
                f.data_coleta.isoformat() if f.data_coleta else "",
                self._geom_k(f.geometry),
            )

            if Foco.objects.filter(hash_registro=h).exclude(pk=f.pk).exists():
                f.delete()
                deleted += 1
                continue

            f.hash_registro = h
            f.save(update_fields=["hash_registro"])
            updated += 1

        self.stdout.write(f"Focos: {updated} atualizados | {deleted} duplicados removidos")

    def _backfill_pontos(self):
        qs = PontoEstrategico.objects.filter(hash_registro__isnull=True)
        updated = 0
        deleted = 0

        for p in qs.iterator(chunk_size=1000):
            h = hash_registro(
                "PONTO",
                p.numero,
                p.municipio,
                p.localidade,
                p.endereco,
                p.complemento,
                p.quarteiroes,
                self._geom_k(p.geometry),
            )

            if PontoEstrategico.objects.filter(hash_registro=h).exclude(pk=p.pk).exists():
                p.delete()
                deleted += 1
                continue

            p.hash_registro = h
            p.save(update_fields=["hash_registro"])
            updated += 1

        self.stdout.write(f"Pontos: {updated} atualizados | {deleted} duplicados removidos")

    def _backfill_armadilhas(self):
        qs = Armadilha.objects.filter(hash_registro__isnull=True)
        updated = 0
        deleted = 0

        for a in qs.iterator(chunk_size=1000):
            h = hash_registro(
                "ARMADILHA",
                a.numero,
                a.municipio,
                a.localidade,
                a.endereco,
                a.complemento or "",
                a.tipo_imovel,
                a.tipo_armadilha,
                a.quarteiroes,
                self._geom_k(a.geometry),
            )

            if Armadilha.objects.filter(hash_registro=h).exclude(pk=a.pk).exists():
                a.delete()
                deleted += 1
                continue

            a.hash_registro = h
            a.save(update_fields=["hash_registro"])
            updated += 1

        self.stdout.write(f"Armadilhas: {updated} atualizados | {deleted} duplicados removidos")
