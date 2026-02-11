import hashlib
import pandas as pd


def col(df, *names):
    cols = {str(c).strip().upper().replace("\u00a0", " "): c for c in df.columns}
    for n in names:
        key = str(n).strip().upper().replace("\u00a0", " ")
        if key in cols:
            return cols[key]
    return None


def to_str(v):
    if v is None:
        return ""
    if isinstance(v, float) and pd.isna(v):
        return ""
    s = str(v).strip()
    if s.lower() in ["nan", "none"]:
        return ""
    return s


def to_int(v):
    if v is None:
        return None
    if isinstance(v, float) and pd.isna(v):
        return None
    try:
        if isinstance(v, str):
            v = v.strip()
            if v == "":
                return None
        return int(float(v))
    except:
        return None


def to_date(v):
    if v is None:
        return None
    try:
        d = pd.to_datetime(v, errors="coerce")
        if pd.isna(d):
            return None
        return d.date()
    except:
        return None


def hash_row(*parts):
    payload = "|".join("" if p is None else str(p) for p in parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
