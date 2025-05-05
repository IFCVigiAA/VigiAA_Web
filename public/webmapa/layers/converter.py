import json

# Caminho para o arquivo original
caminho_entrada = 'public/webmapa/layers/positivos_novo_com_coordenadasoutput_com_coordenadas_8.geojson'
# Caminho para o novo arquivo sem nomes
caminho_saida = 'public/webmapa/layers/positivos_novo_com_coordenadasoutput_com_coordenadas_8.geojson'

with open(caminho_entrada, 'r', encoding='utf-8') as f:
    dados = json.load(f)

# Remove os campos de nome e nome da mãe
for feature in dados['features']:
    props = feature.get('properties', {})
    props.pop('NOME', None)
    props.pop('NOME DA MÃE', None)
    props.pop('ENDEREÇO',None)

# Salva o novo arquivo
with open(caminho_saida, 'w', encoding='utf-8') as f:
    json.dump(dados, f, ensure_ascii=False, indent=2)
