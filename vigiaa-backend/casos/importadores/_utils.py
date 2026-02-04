import hashlib
import pandas as pd


def sha256_arquivo(file) -> str:
    h = hashlib.sha256()
    for chunk in file.chunks():
        h.update(chunk)
    return h.hexdigest()


def col(df, *names):
    cols = {}
    for c in df.columns:
        key = str(c).strip().upper().replace("\u00a0", " ")
        cols[key] = c

    for n in names:
        key = str(n).strip().upper().replace("\u00a0", " ")
        if key in cols:
            return cols[key]
    return None


def to_str(v, default=""):
    if pd.isna(v):
        return default
    return str(v).strip()


def to_int(v, default=0):
    if pd.isna(v):
        return default
    try:
        return int(v)
    except:
        try:
            return int(float(v))
        except:
            return default


def to_date(v):
    d = pd.to_datetime(v, errors="coerce")
    if pd.isna(d):
        return None
    return d.date()
