class ErrorLogger:
    def __init__(self):
        self.data = {
            "planilha": [],
            "geoprocessamento": [],
            "sistema": []
        }

    def add(self, tipo, linha=None, coluna=None, valor=None, erro=None, detalhe=None):
        self.data.setdefault(tipo, []).append({
            "linha": linha,
            "coluna": coluna,
            "valor": str(valor)[:100] if valor is not None else None,
            "erro": erro,
            "detalhe": detalhe
        })

    def resumo(self):
        return {
            "total_erros": sum(len(v) for v in self.data.values()),
            **{k: len(v) for k, v in self.data.items()}
        }

    def to_json(self):
        import json
        return json.dumps({
            "resumo": self.resumo(),
            "erros": self.data
        }, ensure_ascii=False, indent=2)