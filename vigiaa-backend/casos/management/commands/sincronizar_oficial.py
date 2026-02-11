from django.core.management.base import BaseCommand
from django.db import connections, models
from django.db.models import Q
from casos.models import CasoPositivo, Foco, PontoEstrategico, Armadilha
from django.contrib.gis.db import models as gis_models

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
    # v pode ser GEOSGeometry/Point ou None
    if v is None:
        return None
    try:
        # Django GEOSGeometry tem .ewkb (bytes)
        return bytes(v.ewkb)
    except Exception:
        return None


def _sync_sql_insert(Model: type[models.Model], dst_using="oficial", src_using="default") -> int:
    """
    INSERT SQL explícito, escolhendo só colunas que EXISTEM no destino.
    Geometria vai como EWKB usando ST_GeomFromEWKB(%s).
    Dedup: ON CONFLICT(hash_registro) DO NOTHING (se existir hash_registro no destino).
    """
    table = Model._meta.db_table
    dst_cols = _db_columns(dst_using, table)

    # campos concretos do model (sem m2m/reverse) e sem PK
    model_fields = [f for f in Model._meta.local_concrete_fields if not f.primary_key]

    # só os que existem no destino
    fields = [f for f in model_fields if f.column in dst_cols]
    if not fields:
        return 0

    # força incluir hash_registro se destino tem e model tem, pra dedup funcionar
    if "hash_registro" in dst_cols and not any(f.column == "hash_registro" for f in fields):
        hf = next((f for f in model_fields if f.column == "hash_registro"), None)
        if hf:
            fields.append(hf)

    # hashes existentes no destino (pra sync incremental)
    existing_hashes = set()
    if "hash_registro" in dst_cols and any(f.column == "hash_registro" for f in fields):
        existing_hashes = set(
            Model.objects.using(dst_using)
            .exclude(hash_registro__isnull=True)
            .values_list("hash_registro", flat=True)
        )

    src_qs = Model.objects.using(src_using)

    # se temos hash_registro no destino, fazemos incremental
    if "hash_registro" in dst_cols and any(f.column == "hash_registro" for f in fields):
        src_qs = src_qs.exclude(hash_registro__isnull=True)
        if existing_hashes:
            src_qs = src_qs.exclude(hash_registro__in=existing_hashes)

    # monta colunas e placeholders (geometry vira ST_GeomFromEWKB(%s))
    cols_sql = ", ".join(f'"{f.column}"' for f in fields)
    ph_parts = []
    for f in fields:
        if _is_geom_field(f):
            ph_parts.append("ST_GeomFromEWKB(%s)")
        else:
            ph_parts.append("%s")
    placeholders = ", ".join(ph_parts)

    on_conflict = ""
    if "hash_registro" in dst_cols:
        on_conflict = ' ON CONFLICT ("hash_registro") DO NOTHING'

    sql = f'INSERT INTO "{table}" ({cols_sql}) VALUES ({placeholders}){on_conflict};'

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

    with connections[dst_using].cursor() as cur:
        cur.executemany(sql, rows)

    return len(rows)


class Command(BaseCommand):
    help = "Sincroniza dados do DB temporário (default) para o DB oficial (oficial), sem duplicar por hash_registro."

    def handle(self, *args, **options):
        from django.conf import settings

        db = settings.DATABASES["default"]
        self.stdout.write(
            f"DB EM USO NO REQUEST: {db.get('ENGINE')} {db.get('NAME')} {db.get('HOST')}"
        )

        self.stdout.write("Sincronizando casos_positivos...")
        n = _sync_sql_insert(CasoPositivo)
        self.stdout.write(f"OK: processados {n}")

        self.stdout.write("Sincronizando focos_aedes...")
        n = _sync_sql_insert(Foco)
        self.stdout.write(f"OK: processados {n}")

        self.stdout.write("Sincronizando pontos_estrategicos...")
        n = _sync_sql_insert(PontoEstrategico)
        self.stdout.write(f"OK: processados {n}")

        self.stdout.write("Sincronizando relat_arm...")
        n = _sync_sql_insert(Armadilha)
        self.stdout.write(f"OK: processados {n}")
