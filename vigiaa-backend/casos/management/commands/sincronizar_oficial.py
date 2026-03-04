from django.core.management.base import BaseCommand
from django.db import connections, models
from django.contrib.gis.db import models as gis_models
from casos.models import CasoPositivoTempGL, FocoTemp, PontoEstrategicoTemp, ArmadilhaTemp
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


def _sync_sql_insert(
    Model: type[models.Model],
    dst_table: str,
    dst_using="oficial",
    src_using="default",
) -> int:
    """
    Sincroniza dados do Model (origem=temp) para tabela destino no banco oficial.
    """

    src_table = Model._meta.db_table
    dst_cols = _db_columns(dst_using, dst_table)

    if not dst_cols:
        return 0  # tabela destino não existe

    model_fields = [f for f in Model._meta.local_concrete_fields if not f.primary_key]
    fields = [f for f in model_fields if f.column in dst_cols]

    if not fields:
        return 0

    # =========================
    # HASHES EXISTENTES NO DESTINO
    # =========================
    existing_hashes = set()
    if "hash_registro" in dst_cols:
        with connections[dst_using].cursor() as cur:
            cur.execute(
                f'SELECT hash_registro FROM "{dst_table}" WHERE hash_registro IS NOT NULL'
            )
            existing_hashes = {r[0] for r in cur.fetchall()}

    # =========================
    # QUERY DE ORIGEM (TEMP)
    # =========================
    src_qs = Model.objects.using(src_using)

    if "hash_registro" in dst_cols and any(
        f.column == "hash_registro" for f in fields
    ):
        src_qs = src_qs.exclude(hash_registro__isnull=True)
        if existing_hashes:
            src_qs = src_qs.exclude(hash_registro__in=existing_hashes)

    # =========================
    # MONTA SQL
    # =========================
    cols_sql = ", ".join(f'"{f.column}"' for f in fields)

    placeholders = []
    for f in fields:
        if _is_geom_field(f):
            placeholders.append("ST_GeomFromEWKB(%s)")
        else:
            placeholders.append("%s")

    placeholders_sql = ", ".join(placeholders)

    on_conflict = ""
    if "hash_registro" in dst_cols:
        on_conflict = ' ON CONFLICT ("hash_registro") DO NOTHING'

    sql = f'INSERT INTO "{dst_table}" ({cols_sql}) VALUES ({placeholders_sql}){on_conflict};'

    # =========================
    # COLETA DADOS
    # =========================
    rows = []
    for obj in src_qs.iterator(chunk_size=2000):
        vals = []
        for f in fields:
            v = getattr(obj, f.attname)
            if _is_geom_field(f):
                vals.append(_geom_to_ewkb(v))
            else:
                vals.append(v)
        rows.append(vals)

    if not rows:
        return 0

    # =========================
    # EXECUTA INSERT
    # =========================
    with connections[dst_using].cursor() as cur:
        cur.executemany(sql, rows)

    return len(rows)


class Command(BaseCommand):
    help = "Sincroniza dados do DB temporário (default) para o DB oficial (oficial)."

    def handle(self, *args, **options):
        from django.conf import settings

        self.stdout.write("ARQUIVO EXECUTADO: " + os.path.abspath(__file__))

        db = settings.DATABASES["default"]
        self.stdout.write(
            f"DB TEMP: {db.get('ENGINE')} | {db.get('NAME')} | {db.get('HOST')}"
        )

        total = 0

        # =========================
        # CASOS POSITIVOS
        # =========================
        self.stdout.write("Sincronizando casos_positivos...")
        n = _sync_sql_insert(
            CasoPositivoTempGL,
            dst_table="casos_positivos",
        )
        self.stdout.write(f"OK: processados {n}")
        total += n

        # =========================
        # FOCOS AEDES
        # =========================
        self.stdout.write("Sincronizando focos_aedes...")
        n = _sync_sql_insert(
            FocoTemp,
            dst_table="focos_aedes",
        )
        self.stdout.write(f"OK: processados {n}")
        total += n

        # =========================
        # PONTOS ESTRATÉGICOS
        # =========================
        self.stdout.write("Sincronizando pontos_estrategicos...")
        n = _sync_sql_insert(
            PontoEstrategicoTemp,
            dst_table="pontos_estrategicos",
        )
        self.stdout.write(f"OK: processados {n}")
        total += n

        # =========================
        # ARMADILHAS
        # =========================
        self.stdout.write("Sincronizando relat_arm...")
        n = _sync_sql_insert(
            ArmadilhaTemp,
            dst_table="relat_arm",
        )
        self.stdout.write(f"OK: processados {n}")
        total += n

        self.stdout.write(f"\nTOTAL PROCESSADO: {total}")