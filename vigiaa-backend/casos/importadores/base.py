def pegar_coluna(df, possiveis):
    for col in possiveis:
        if col in df.columns:
            return col
    return None
