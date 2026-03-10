from django.core.management.base import BaseCommand
from django.db import connections, models
from django.contrib.gis.db import models as gis_models
from casos.models import (
    CasoPositivoTempGL,
    FocoTemp,
    PontoEstrategicoTemp,
    ArmadilhaTemp,
)
import os


def _db_columns(using: str, table: str) -> set[str]:
    with connections[using].cursor() as cur:
        cur.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema='public' AND table_name=%s
            """,
            [table],
        )
        return {r[0] for r in cur.fetchall()}


def _is_geom_field(f) -> bool:
    return isinstance(f, gis_models.GeometryField)


def _geom_to_ewkb(v):
    if v is None:
        return None
    try:
        return bytes(v.ewkb)
    except Exception:
        return None


def _sync_sql_upsert(
    Model: type[models.Model],
    dst_table: str,
    dst_using="oficial",
    src_using="default",
):
    """
    Sincroniza dados do banco TEMP (default)
    para o banco OFICIAL (oficial).

    Faz INSERT ou UPDATE baseado em hash_registro.
    """

    dst_cols = _db_columns(dst_using, dst_table)
    if not dst_cols:
        return 0, 0

    model_fields = [
        f for f in Model._meta.local_concrete_fields if not f.primary_key
    ]
    fields = [f for f in model_fields if f.column in dst_cols]

    if not fields:
        return 0, 0

    has_hash = "hash_registro" in dst_cols and any(
        f.column == "hash_registro" for f in fields
    )

    cols_sql = ", ".join(f'"{f.column}"' for f in fields)

    placeholders = []
    for f in fields:
        if _is_geom_field(f):
            placeholders.append("ST_GeomFromEWKB(%s)")
        else:
            placeholders.append("%s")

    placeholders_sql = ", ".join(placeholders)

    update_sql = ""
    if has_hash:
        update_fields = [f for f in fields if f.column != "hash_registro"]
        set_clause = ", ".join(
            f'"{f.column}" = EXCLUDED."{f.column}"'
            for f in update_fields
        )
        update_sql = f' ON CONFLICT ("hash_registro") DO UPDATE SET {set_clause}'

    sql = f"""
        INSERT INTO "{dst_table}" ({cols_sql})
        VALUES ({placeholders_sql})
        {update_sql}
        RETURNING (xmax = 0) AS inserted;
    """

    inseridos = 0
    atualizados = 0

    with connections[dst_using].cursor() as cur:
        for obj in Model.objects.using(src_using).iterator(chunk_size=2000):

            vals = []
            for f in fields:
                v = getattr(obj, f.attname)
                if _is_geom_field(f):
                    vals.append(_geom_to_ewkb(v))
                else:
                    vals.append(v)

            cur.execute(sql, vals)
            inserted = cur.fetchone()[0]

            if inserted:
                inseridos += 1
            else:
                atualizados += 1

    return inseridos, atualizados


class Command(BaseCommand):
    help = "Sincroniza dados do DB temporário (default) para o DB oficial (oficial)."

    def handle(self, *args, **options):
        from django.conf import settings

        self.stdout.write("\n=======================================")
        self.stdout.write("INICIANDO SINCRONIZAÇÃO OFICIAL")
        self.stdout.write("=======================================\n")

        db = settings.DATABASES["default"]
        self.stdout.write(
            f"DB TEMP: {db.get('ENGINE')} | {db.get('NAME')} | {db.get('HOST')}\n"
        )

        total_inseridos = 0
        total_atualizados = 0

        # =========================
        # CASOS POSITIVOS
        # =========================
        self.stdout.write("→ Sincronizando casos_positivos...")
        ins, upd = _sync_sql_upsert(
            CasoPositivoTempGL,
            dst_table="casos_positivos",
        )
        self.stdout.write(f"   Inseridos: {ins}")
        self.stdout.write(f"   Atualizados: {upd}\n")
        total_inseridos += ins
        total_atualizados += upd

        # =========================
        # FOCOS AEDES
        # =========================
        self.stdout.write("→ Sincronizando focos_aedes...")
        ins, upd = _sync_sql_upsert(
            FocoTemp,
            dst_table="focos_aedes",
        )
        self.stdout.write(f"   Inseridos: {ins}")
        self.stdout.write(f"   Atualizados: {upd}\n")
        total_inseridos += ins
        total_atualizados += upd

        # =========================
        # PONTOS ESTRATÉGICOS
        # =========================
        self.stdout.write("→ Sincronizando pontos_estrategicos...")
        ins, upd = _sync_sql_upsert(
            PontoEstrategicoTemp,
            dst_table="pontos_estrategicos",
        )
        self.stdout.write(f"   Inseridos: {ins}")
        self.stdout.write(f"   Atualizados: {upd}\n")
        total_inseridos += ins
        total_atualizados += upd

        # =========================
        # ARMADILHAS
        # =========================
        self.stdout.write("→ Sincronizando relat_arm...")
        ins, upd = _sync_sql_upsert(
            ArmadilhaTemp,
            dst_table="relat_arm",
        )
        self.stdout.write(f"   Inseridos: {ins}")
        self.stdout.write(f"   Atualizados: {upd}\n")
        total_inseridos += ins
        total_atualizados += upd

        self.stdout.write("=======================================")
        self.stdout.write("SINCRONIZAÇÃO FINALIZADA")
        self.stdout.write(f"TOTAL INSERIDOS: {total_inseridos}")
        self.stdout.write(f"TOTAL ATUALIZADOS: {total_atualizados}")
        self.stdout.write(
            f"TOTAL GERAL PROCESSADO: {total_inseridos + total_atualizados}"
        )
        self.stdout.write("=======================================\n")