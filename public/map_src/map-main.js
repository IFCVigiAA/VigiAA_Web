// Acesso aos elementos do DOM
const selectYear = document.getElementById('filter-ano');
const selectSE = document.getElementById('filter-SE');
const declividadeLegend = document.getElementById('declividade-legend');
const demografiaOfcLegend = document.getElementById('demografia_ofc-legend');
const heatmapLegend = document.getElementById('heatmap-legend');

const LAYER_CLUSTERS_CASOS = 'vw_clusters_casos'; // Nome da VIEW no PostGIS
const LAYER_CLUSTERS_FOCOS = 'vw_clusters_focos';    // Nome da outra VIEW

// Variáveis de estado do filtro (inicializadas em map-main)
let selectedYear = '';
let selectedSE = '';
let map; // Variável para a instância do mapa

// --- Funções de Ajuda para o Mapa ---

// Gerencia a substituição da camada no mapa e no controle
function refreshLayerInControl(oldLayer, newLayer, layerName) {
    // Verifica se oldLayer é um objeto válido do Leaflet
    const wasOnMap = oldLayer && oldLayer instanceof L.Layer && map.hasLayer(oldLayer);

    if (oldLayer && wasOnMap) {
        map.removeLayer(oldLayer);
    }

    // A verificação 'instanceof L.Layer' evita o erro 't.off is not a function'
    if (map.layersControl && oldLayer && oldLayer instanceof L.Layer) {
        try {
            map.layersControl.removeLayer(oldLayer);
        } catch (e) {
            console.warn("Camada já removida ou inexistente no controle.");
        }
    }

    if (map.layersControl && newLayer) {
        map.layersControl.addOverlay(newLayer, layerName);
    }

    if (wasOnMap && newLayer) {
        newLayer.addTo(map);
    }
}

function resetFiltersToDefault() {
    selectedYear = '';
    selectedSE = '';
    const elYear = document.getElementById('filter-ano'); // Busca direta para evitar cache null
    if (elYear) elYear.value = '';
    console.log("Filtros resetados pelo clique do usuário.");
}

// Função Genérica para buscar e adicionar Camadas WFS (para GeoJSON)
function fetchWFSData(layerName, displayName, styleFunction, popupFields, version = '2.0.0', isPointLayer = false, cqlFilter = '1=1') {
    let fullLayerName = layerName;
    if (layerName.indexOf(':') === -1) {
        // Se NÃO incluir, adiciona o WORKSPACE padrão.
        fullLayerName = `${WORKSPACE}:${layerName}`;
    }

    var wfsUrl = `http://192.168.70.63:8080/geoserver/wfs?`;
    
    var params = {
        service: 'WFS', version: version, request: 'GetFeature', typeName: fullLayerName,
        outputFormat: 'application/json', cql_filter: cqlFilter
    };
    const queryString = new URLSearchParams(params).toString();
    //const fullUrl = wfsUrl + queryString;
    const fullUrl = `${GEOSERVER_WFS_URL}?` + new URLSearchParams(params).toString();

    return fetch(fullUrl)
        .then(response => {
            if (!response.ok) { throw new Error(`HTTP error! status: ${response.status} for ${displayName}`); }
            return response.json();
        })
        .then(data => {
            var layerOptions = {
                style: styleFunction,
                onEachFeature: function(feature, layer) {
                    // ... Lógica de Popup (mantida aqui) ...
                    if (feature.properties) {
                        var popupContent = `<b>${displayName.split('(')[0].trim()}:</b><br>`;
                        var fieldsToDisplay = popupFields && popupFields.length > 0 ? popupFields : Object.keys(feature.properties);
                        for (var field of fieldsToDisplay) {
                            if (feature.properties[field] !== undefined) {
                                let alias = field.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                                popupContent += `<b>${alias}:</b> ${feature.properties[field]}<br>`;
                            }
                        }
                        layer.bindPopup(popupContent);
                    }
                }
            };

            if (isPointLayer) {
                layerOptions.pointToLayer = function(feature, latlng) {
                    return L.circleMarker(latlng, styleFunction(feature));
                };
            }

            var newLayer = L.geoJSON(data, layerOptions);
            newLayer.name = displayName;
            return newLayer;
        })
        .catch(error => {
            console.error(`Erro ao buscar ou processar dados WFS para ${displayName}:`, error);
            return null;
        });
}

// --- Funções de Carga e Atualização de Camadas ---

// Funções de carga estática (chamadas apenas uma vez na inicialização)
function loadBairrosOnce() { return fetchWFSData('vigiaa_ofc:vw_bairros_cb_ofc', 'Bairros - Oficial (Estático)', bairrosStyleWFS, ['nome']); }
function loadSetCensOnce() { return fetchWFSData('vigiaa_ofc:vw_set_cens_camb', 'Setores Censitários (Estático)', setCensStyleWFS, ['NM_BAIRRO']); }
function loadDensDemoSetCensOnce() { return fetchWFSData('vigiaa_ofc:vw_set_cens_demo_camb_classes', 'Densidade Demográfica (SC)', densDemoSetCensStyle, ['DENSIDADE_DEMOGRAFICA_SETOR_HAB_KM2']); }
// ... Outras funções estáticas (BairrosOfc, Camboriu, CurvaNivel, DeclividadePoligono) ...
function loadBairrosOfcOnce() { return fetchWFSData('vigiaa_ofc:vw_bairros_cb_ibge', 'Bairros - IBGE (Estático)', bairrosOfcStyleWFS, ['NM_BAIRRO']); }
function loadCamboriuOnce() { return fetchWFSData('vigiaa_ofc:vw_mun_camb', 'Camboriú (Estático)', camboriuStyleWFS, ['NM_MUN']); }
function loadCurvaNivelOnce() { return fetchWFSData('vigiaa_ofc:vw_cv_nvl_camboriu_li', 'Curva de Nível (Estático)', curvasNivelStyleWFS, ['CLASSE']); } 
function loadDeclividadePoligonoOnce() { return fetchWFSData('vigiaa_ofc:vw_cv_nvl_camboriu_union', 'Declividade (Polígonos)', declividadePlStyle, ['CLASSE', 'AREA_METROS']); }

// Funções de atualização dinâmica (chamadas na inicialização e no filtro/intervalo)
function updateFocosAedes() {
    const filter = buildCqlFilter(selectedYear, selectedSE);
    return fetchWFSData(LAYER_FOCOS_SE, 'Focos Aedes (Dinâmico)', focosStyleWFS, ['id', 'n_foco', 'a_aegypti_form_aquaticas', 'a_aegypti_form_adultas', 'a_albopictus_form_aquaticas', 'a_albopictus_form_adultas', 'ovo_a_aegypti'], '2.0.0', true, filter).then(newLayer => {
        if (newLayer) { 
            refreshLayerInControl(focosWFSLayer, newLayer, 'Focos Aedes (Dinâmico)'); 
            focosWFSLayer = newLayer; 
        }
        return focosWFSLayer;
    });
}
// ... Outras funções dinâmicas (updatePontosEstrat, updateArmadilhas) ...
function updatePontosEstrat() {
    return fetchWFSData('vigiaa_ofc:pontos_estrategicos', 'Pontos Estratégicos (Dinâmico)', peStyleWFS, ['id', 'numero'], '2.0.0', true).then(newLayer => {
        if (newLayer) { refreshLayerInControl(peWFSLayer, newLayer, 'Pontos Estratégicos (Dinâmico)'); peWFSLayer = newLayer; }
        return peWFSLayer;
    });
}
function updateArmadilhas() {
    return fetchWFSData('vigiaa_ofc:relat_arm', 'Armadilhas (Dinâmico)', armStyleWFS, ['id', 'numero', 'tipo_imovel'], '2.0.0', true).then(newLayer => {
        if (newLayer) { refreshLayerInControl(armWFSLayer, newLayer, 'Armadilhas (Dinâmico)'); armWFSLayer = newLayer; }
        return armWFSLayer;
    });
}

function updateCasosPositivosPoints() {
    const filter = buildCqlFilter(selectedYear, selectedSE); // Obtém filtro atual
    return fetchWFSData(LAYER_CASOS, 'Casos Positivos (Pontos)', casosPointStyleWFS, ['id', 'inicio_sintomas'], '2.0.0', true, filter).then(newLayer => {
        if (newLayer) { refreshLayerInControl(currentCasosPointLayer, newLayer, 'Casos Positivos (Pontos)'); currentCasosPointLayer = newLayer; }
        return currentCasosPointLayer;
    });
}

function updateHeatmapSwitch() {
    // 1. Detecta o contexto (se o usuário está vendo Casos ou Focos)
    const context = getActiveLayerContext(); 
    const isFocos = context.type === 'focos';
    const targetLayer = isFocos ? currentFocosHeatmapLayer : currentCasosHeatmapLayer;

    if (!targetLayer || !map.hasLayer(targetLayer)) return;

    // 2. Define os parâmetros baseados no switch
    //const layerName = isFocos ? 'Focos (Mapa de Calor)' : 'Casos Positivos (Mapa de Calor)';
    //const oldLayer = isFocos ? currentFocosHeatmapLayer : currentCasosHeatmapLayer;
    const filter = buildCqlFilter(selectedYear, selectedSE);
    const params = { 
        service: 'WFS', 
        version: '2.0.0', 
        request: 'GetFeature', 
        typeName: `${WORKSPACE}:${context.table}`, // Usa a tabela do switch
        outputFormat: 'application/json', 
        cql_filter: filter
    };
    
    const fullUrl = `http://192.168.70.63:8080/geoserver/wfs?` + new URLSearchParams(params).toString();

    return fetch(fullUrl)
        .then(response => response.json())
        .then(data => {

            const heatData = data.features.map(f => [
                f.geometry.coordinates[1], 
                f.geometry.coordinates[0]
            ]);
            
            // 4. Cria o novo Heatmap com cores diferentes para cada tipo
            const gradient = isFocos 
                ? { 0.0: 'blue', 0.5: 'lime', 1.0: 'orange' } // Focos em Laranja
                : { 0.0: 'blue', 0.5: 'yellow', 1.0: 'red' }; // Casos em Vermelho

            // Em vez de criar uma nova camada, apenas atualizamos os dados da existente
            targetLayer.setLatLngs(heatData);
            targetLayer.setOptions({ gradient: gradient });
        })
        .catch(error => console.error(`Erro no Switch Heatmap (${context.type}):`, error));
}

function updateClustersDinamico(layerName, displayName, currentLayerVar, contextType) {
    const isCasos = contextType === 'casos';
    
    // Captura os elementos do DOM com segurança
    const elYear = document.getElementById(isCasos ? 'filter-ano-casos' : 'filter-ano-focos');
    const elSE = document.getElementById(isCasos ? 'filter-se-casos' : 'filter-se-focos');
    
    const year = elYear ? elYear.value : '';
    const se = elSE ? elSE.value : '';

    // Constrói o filtro CQL utilizando a lógica do seu projeto
    const filter = buildCqlFilter(year, se);

    // Mapeia as colunas de retorno baseadas no GeoServer
    const popupFields = isCasos ? ['total_casos', 'se_num', 'ano_se'] : ['total_focos', 'se_num', 'ano_se'];

    // Define o estilo visual (clusterStyle deve estar no map-config.js)
    const styleFunc = isCasos ? clusterCasosStyle : clusterFocosStyle;

    // Chamada para a sua função genérica WFS
    return fetchWFSData(layerName, displayName, styleFunc, popupFields, '2.0.0', false, filter)
        .then(newLayer => {
            if (newLayer) {
                // Substitui a camada antiga pela nova no controle e no mapa
                refreshLayerInControl(currentLayerVar, newLayer, displayName);
                
                // IMPORTANTE: Atualiza a variável global correspondente
                if (isCasos) {
                    clusterCasosLayer = newLayer;
                } else {
                    clusterFocosLayer = newLayer;
                }
            }
            return newLayer;
        })
        .catch(error => {
            console.error(`Erro na atualização dinâmica de clusters (${contextType}):`, error);
            return null;
        });
}

// Estilo para o Cluster de Casos (Vermelho)
const clusterCasosStyle = function(feature) {
    return {
        fillColor: '#d73027',
        color: '#a50026',
        weight: 2,
        opacity: 1,
        fillOpacity: 0.6
    };
};

// Estilo para o Cluster de Focos de Mosquito (Verde)
const clusterFocosStyle = function(feature) {
    return {
        fillColor: '#1a9850',
        color: '#006837',
        weight: 2,
        opacity: 1,
        fillOpacity: 0.6
    };
};

// Funções de imagem (overlay)
function loadImageLayers() {
    const declividadeBounds = [[-27.196900051, -48.88833825645294], [-26.951489787, -48.53321516854706]]; 
    const demografiaBounds = [[-27.145871184999997, -48.75972971313529], [-26.95321603, -48.493185639864706]]; 

    const declividadeImageUrl = "mapa_declividade_transparente.png"; 
    const demografiaImageUrl = "mapa_dens_transparente.png";

    declividadeImageLayer = L.imageOverlay(declividadeImageUrl, declividadeBounds, { opacity: 1.0, interactive: true, alt: 'Mapa de Declividade' });
    declividadeImageLayer.name = 'Declividade (Imagem)'; 

    demografiaImageLayer = L.imageOverlay(demografiaImageUrl, demografiaBounds, { opacity: 1.0, interactive: true, alt: 'Mapa de Demografia' });
    demografiaImageLayer.name = 'Demografia (Imagem)'; 

    return Promise.resolve([declividadeImageLayer, demografiaImageLayer]);
}

// --- Funções de Filtro (Lógica de Eventos) ---



async function populateSpecificYears(context, layerName, selectId) {
    const selectElement = document.getElementById(selectId);

    // Se já estiver populado e com valor, não limpa tudo
    if (selectElement.options.length > 1 && selectElement.value !== "") return;

    const data = await fetchGeoServerFilterData(layerName, '1=1', 'ano_se');
    const years = [...new Set(data.map(item => item.ano_se))].filter(a => a).sort((a, b) => b - a);

    const currentValue = selectElement.value; // Salva o valor atual
    selectElement.innerHTML = '<option value="">Ano</option>';

    years.forEach(year => {
        const opt = document.createElement('option');
        opt.value = year;
        opt.textContent = year;
        selectElement.appendChild(opt);
    });
    
    selectElement.value = currentValue;

    if (!selectElement.dataset.hasListener) {
        selectElement.addEventListener('change', (e) => handleYearChangeNew(context, e.target.value));
        selectElement.dataset.hasListener = "true";
    }
}

async function handleYearChangeNew(context, year) {
    const isCasos = context === 'casos';
    const table = isCasos ? LAYER_CASOS : LAYER_FOCOS_SE;
    const seSelectId = isCasos ? 'filter-se-casos' : 'filter-se-focos';
    const seSelect = document.getElementById(seSelectId);

    if (!year) {
        seSelect.innerHTML = '<option value="">SE*</option>';
        seSelect.disabled = true;
        updateLayerByContext(context); // Atualiza para "Todos"
        return;
    }

    const data = await fetchGeoServerFilterData(table, `ano_se=${year}`, 'se_num');
    const ses = [...new Set(data.map(item => item.se_num))].filter(s => s).sort((a, b) => a - b);

    seSelect.innerHTML = '<option value="">Todos</option>';
    ses.forEach(se => {
        const opt = document.createElement('option');
        opt.value = se;
        opt.textContent = `SE ${se}`;
        seSelect.appendChild(opt);
    });
    seSelect.disabled = false;

    if (!seSelect.dataset.hasListener) {
        seSelect.addEventListener('change', () => updateLayerByContext(context));
        seSelect.dataset.hasListener = "true";
    }

    updateLayerByContext(context);
}

// Função para atualizar os dados da camada (WFS) sem recriar o objeto
async function updateLayerByContext(context) {
    const isCasos = context === 'casos';
    const yearElement = document.getElementById(isCasos ? 'filter-ano-casos' : 'filter-ano-focos');
    const seElement = document.getElementById(isCasos ? 'filter-se-casos' : 'filter-se-focos');
    
    if (!yearElement || !seElement) return;

    const yearVal = yearElement.value;
    const seVal = seElement.value;
    const layer = isCasos ? currentCasosPointLayer : focosWFSLayer;
    const table = isCasos ? LAYER_CASOS : LAYER_FOCOS_SE;
    const filter = buildCqlFilter(yearVal, seVal);
    
    const url = `${GEOSERVER_WFS_URL}?service=WFS&version=2.0.0&request=GetFeature&typeName=${WORKSPACE}:${table}&outputFormat=application/json&cql_filter=${encodeURIComponent(filter)}`;
    
    try {
        const response = await fetch(url);
        const data = await response.json();
        
        if (layer && typeof layer.clearLayers === 'function') {
            layer.clearLayers();
            layer.addData(data);
        }

        // Atualiza o Cluster e o Heatmap uma única vez por ciclo
        if (isCasos) {
            updateClustersDinamico(LAYER_CLUSTERS_CASOS, 'Clusters de Casos (Focos Ativos)', clusterCasosLayer, 'casos');
        } else {
            updateClustersDinamico(LAYER_CLUSTERS_FOCOS, 'Clusters de Mosquitos (Áreas Críticas)', clusterFocosLayer, 'focos');
        }

        updateHeatmapData(context, data);
        
    } catch (e) {
        console.error(`Erro ao filtrar ${context}:`, e);
    }
}

function updateHeatmapData(context, geojsonData) {
    const isCasos = context === 'casos';
    const targetHeatLayer = isCasos ? currentCasosHeatmapLayer : currentFocosHeatmapLayer;
    
    // Só prossegue se a camada existir e o mapa não estiver ocupado
    if (!targetHeatLayer || !map.hasLayer(targetHeatLayer) || !map._loaded) return;

    const heatPoints = geojsonData.features.map(f => [
        f.geometry.coordinates[1], 
        f.geometry.coordinates[0]
    ]);

    // O uso de requestAnimationFrame garante que a atualização ocorra no próximo ciclo visual estável
    requestAnimationFrame(() => {
        try {
            if (targetHeatLayer._map) { // Verifica se ainda está no mapa
                targetHeatLayer.setLatLngs(heatPoints);
            }
        } catch (err) {
            console.warn("Heatmap ocupado, pulando atualização de frame.");
        }
    });
}

async function populateSE(year) {
    if (!year) return;
    const context = getActiveLayerContext(); // Pega o contexto atual
    const cql = `ano_se=${year}`;

    const seData = await fetchGeoServerFilterData(context.table, cql, 'se_num');
    //filtrar valores únicos

    const distinctSE = [...new Set(seData.map(item => item.se_num))].sort((a, b) => a - b);

    selectSE.innerHTML = '<option value="">Todos</option>';        
    distinctSE.forEach(se => {
        const option = document.createElement('option');
        option.value = se; 
        option.textContent = `SE ${se}`;
        selectSE.appendChild(option);
    });
    //Garante listner
    selectSE.disabled = false;
    selectSE.removeEventListener('change', handleSEChange);
    selectSE.addEventListener('change', handleSEChange);
}

async function handleSEChange(event) {
    selectedSE= event.target.value;
    updateMapLayers();
}

// Detecta se o usuário está focado em Casos ou Focos para regular o filtro
function getActiveLayerContext() {
    if (currentCasosPointLayer && map.hasLayer(currentCasosPointLayer)) {
        return { table: LAYER_CASOS, type: 'casos' };
    }
    if (focosWFSLayer && map.hasLayer(focosWFSLayer)) {
        return { table: LAYER_FOCOS_SE, type: 'focos' };
    }
    
    // Fallback: Se o usuário estiver apenas com o Heatmap ligado, 
    // tentamos detectar por ele, mas a prioridade acima evita conflitos.
    if (currentFocosHeatmapLayer && map.hasLayer(currentFocosHeatmapLayer)) return { table: LAYER_FOCOS_SE, type: 'focos' };
    
    return { table: LAYER_CASOS, type: 'casos' };
}

// Recarrega as camadas dinâmicas com o filtro atual
function updateMapLayers() {

    const context = getActiveLayerContext();

    if (context.type === 'casos') {
        if (map.hasLayer(currentCasosPointLayer)) updateCasosPositivosPoints();
        if (map.hasLayer(currentCasosHeatmapLayer)) updateHeatmapSwitch();
    } else {
        if (map.hasLayer(focosWFSLayer)) updateFocosAedes();
        if (map.hasLayer(currentFocosHeatmapLayer)) updateHeatmapSwitch();
    }
}

// --- FUNÇÃO DE INICIALIZAÇÃO (window.onload) ---
window.onload = function() {
    // 1. Inicializa o Mapa
    map = L.map('mapid').setView([-27.0258, -48.6549], 12);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);

    // 2. Inicialização e Agregação de Camadas
    var baseLayers = {}; 
    var overlayMaps = {}; 

    Promise.all([
        loadBairrosOnce(), loadBairrosOfcOnce(), loadSetCensOnce(), loadCamboriuOnce(), loadCurvaNivelOnce(),
        updateFocosAedes(), updatePontosEstrat(), updateArmadilhas(), 
        updateCasosPositivosPoints(), //updateHeatmapSwitch(),updateCasosHeatmap(),
        loadImageLayers(), loadDeclividadePoligonoOnce(), loadDensDemoSetCensOnce(),
        updateClustersDinamico(LAYER_CLUSTERS_CASOS, 'Clusters de Casos (Focos Ativos)', null, 'casos'),
        updateClustersDinamico(LAYER_CLUSTERS_FOCOS, 'Clusters de Mosquitos (Áreas Críticas)', null, 'focos')
    ]).then(results => {
        // Atribui os resultados às variáveis globais e as adiciona ao overlayMaps
        [
            bairrosWFSLayer, bairrosOfcWFSLayer, setCensWFSLayer, camboriuWFSLayer, curvasNivelWFSLayer, 
            focosWFSLayer, peWFSLayer, armWFSLayer, 
            currentCasosPointLayer, //currentCasosHeatmapLayer,
            [declividadeImageLayer, demografiaImageLayer], declividadePlLayer, setCensDemoCambLayer, 
            clusterCasosLayer, clusterFocosLayer
        ] = results;

        // Adiciona ao controle de camadas

        if (bairrosWFSLayer) { overlayMaps[bairrosWFSLayer.name] = bairrosWFSLayer; }
        // ... (Adicionar as outras camadas ao overlayMaps) ...
        if (bairrosOfcWFSLayer) { overlayMaps[bairrosOfcWFSLayer.name] = bairrosOfcWFSLayer; }
        if (setCensWFSLayer) { overlayMaps[setCensWFSLayer.name] = setCensWFSLayer; }
        if (curvasNivelWFSLayer) { overlayMaps[curvasNivelWFSLayer.name] = curvasNivelWFSLayer; }
        if (declividadePlLayer) { overlayMaps[declividadePlLayer.name] = declividadePlLayer; }
        if (setCensDemoCambLayer) { overlayMaps[setCensDemoCambLayer.name] = setCensDemoCambLayer; }
        if (camboriuWFSLayer) { overlayMaps[camboriuWFSLayer.name] = camboriuWFSLayer; }
        if (focosWFSLayer) { overlayMaps[focosWFSLayer.name] = focosWFSLayer; }
        if (peWFSLayer) { overlayMaps[peWFSLayer.name] = peWFSLayer; }
        if (armWFSLayer) { overlayMaps[armWFSLayer.name] = armWFSLayer; }
        if (currentCasosPointLayer) { overlayMaps[currentCasosPointLayer.name] = currentCasosPointLayer; }
        if (currentCasosHeatmapLayer) { overlayMaps[currentCasosHeatmapLayer.name] = currentCasosHeatmapLayer; }
        if (declividadeImageLayer) { overlayMaps[declividadeImageLayer.name] = declividadeImageLayer; }
        if (demografiaImageLayer) { overlayMaps[demografiaImageLayer.name] = demografiaImageLayer; }

        // ALTERAÇÃO 2: Crie camadas de Heatmap "vazias" apenas para o controle de camadas
        // Isso permite que o usuário veja a opção no menu sem que os dados sejam baixados antes
        currentCasosHeatmapLayer = L.heatLayer([], { radius: 25 });
        currentCasosHeatmapLayer.name = 'Casos Positivos (Mapa de Calor)';

        currentFocosHeatmapLayer = L.heatLayer([], { radius: 25 });
        currentFocosHeatmapLayer.name = 'Focos (Mapa de Calor)';

        // Adicione-as ao overlayMaps para aparecerem no seletor
        overlayMaps[currentCasosHeatmapLayer.name] = currentCasosHeatmapLayer;
        overlayMaps[currentFocosHeatmapLayer.name] = currentFocosHeatmapLayer;

        // 3. Adiciona Controle de Camadas
        map.layersControl = L.control.layers(baseLayers, overlayMaps, { position: 'topright', collapsed: true }).addTo(map);

        map.layersControl.getContainer().addEventListener('click', function(event) {
            // Pegamos o rótulo da camada clicada
                const label = event.target.closest('label');
                if (!label) return;
                
                const clickedLayerName = label.innerText.trim();

                // LISTA DE CAMADAS QUE RESETAM O FILTRO
                // Se clicar em qualquer outra (como Heatmap), o filtro permanece como está
                const resetLayers = ['Casos Positivos (Pontos)', 'Focos Aedes (Dinâmico)'];

            }, true);

        function organizarLegendas() {
            const legendas = [
                document.getElementById('declividade-legend'),
                document.getElementById('demografia_ofc-legend'),
                document.getElementById('heatmap-legend')
            ];

            let alturaAcumulada = 10; // Espaçamento inicial do fundo (10vh ou pixels)
            const espacamento = 15; // Espaço entre uma legenda e outra

            legendas.forEach(legenda => {
                if (legenda && legenda.style.display !== 'none') {
                    // Define a posição da legenda atual baseada na altura acumulada
                    legenda.style.bottom = alturaAcumulada + "px";
                    
                    // Soma a altura desta legenda para a próxima ficar acima dela
                    // offsetHeight pega a altura real do elemento no momento
                    alturaAcumulada += legenda.offsetHeight + espacamento;
                }
            });
        }

        // 4. Configuração de Eventos do Mapa (Legendas)
        map.on('overlayadd', function (e) {
            const mainContainer = document.getElementById('main-filter-container');
            const layersControl = document.querySelector('.leaflet-control-layers');
    
            // APENAS camadas de PONTOS disparam a abertura do painel de filtro
            if (e.name === 'Casos Positivos (Pontos)') {
                mainContainer.style.display = 'flex';
                document.getElementById('group-filter-casos').style.display = 'block';
                layersControl.classList.add('leaflet-control-layers-pushed');
                populateSpecificYears('casos', LAYER_CASOS, 'filter-ano-casos');
            }
            
            if (e.name === 'Focos Aedes (Dinâmico)') {
                mainContainer.style.display = 'flex';
                document.getElementById('group-filter-focos').style.display = 'block';
                layersControl.classList.add('leaflet-control-layers-pushed');
                populateSpecificYears('focos', LAYER_FOCOS_SE, 'filter-ano-focos');
            }

            if (e.name.includes('Mapa de Calor')) { heatmapLegend.style.display = 'block'; }
            if (e.name === 'Declividade (Polígonos)') { declividadeLegend.style.display = 'block'; }
            if (e.name === 'Densidade Demográfica (SC)') { demografiaOfcLegend.style.display = 'block'; }


            // DISPARO AQUI: Reorganiza após as legendas aparecerem
            setTimeout(organizarLegendas, 100);
        });

        map.on('overlayremove', function (e) {
            const layersControl = document.querySelector('.leaflet-control-layers');
            
            // Identifica qual contexto estamos removendo
            let contextToRemove = null;
            if (e.name === 'Casos Positivos (Pontos)') contextToRemove = 'casos';
            if (e.name === 'Focos Aedes (Dinâmico)') contextToRemove = 'focos';

            // 1. Limpa APENAS os seletores do contexto que saiu do mapa
            if (contextToRemove) {
                const ano = document.getElementById(`filter-ano-${contextToRemove}`);
                const se = document.getElementById(`filter-se-${contextToRemove}`);
                if(ano) ano.value = "";
                if(se) {
                    se.innerHTML = '<option value="">SE*</option>';
                    se.disabled = true;
                }
                
                // Remove camadas auxiliares (clusters) se existirem
                if (contextToRemove === 'casos' && clusterCasosLayer) map.removeLayer(clusterCasosLayer);
                if (contextToRemove === 'focos' && clusterFocosLayer) map.removeLayer(clusterFocosLayer);
                
                document.getElementById(`group-filter-${contextToRemove}`).style.display = 'none';
            }

            // 2. Verifica o que sobrou para decidir se esconde o container principal
            const casosAtivo = map.hasLayer(currentCasosPointLayer);
            const focosAtivo = map.hasLayer(focosWFSLayer);

            if (!casosAtivo && !focosAtivo) {
                document.getElementById('main-filter-container').style.display = 'none';
                if (layersControl) layersControl.classList.remove('leaflet-control-layers-pushed');
            }

            // Gerenciamento de Legendas permanece igual
            const heatmapAtivo = map.hasLayer(currentCasosHeatmapLayer) || map.hasLayer(currentFocosHeatmapLayer);
            if (!heatmapAtivo) heatmapLegend.style.display = 'none';
            if (e.name === 'Declividade (Polígonos)') declividadeLegend.style.display = 'none';
            if (e.name === 'Densidade Demográfica (SC)') demografiaOfcLegend.style.display = 'none';

            organizarLegendas();
        });

// Função auxiliar para limpar os campos quando tudo é fechado
function resetFilterSelectors() {
    ['casos', 'focos'].forEach(ctx => {
        const ano = document.getElementById(`filter-ano-${ctx}`);
        const se = document.getElementById(`filter-se-${ctx}`);
        if(ano) ano.value = "";
        if(se) {
            se.innerHTML = '<option value="">SE*</option>';
            se.disabled = true;
        }
    });
}
        
        // 5. Configuração de Atualização em Intervalos
        setInterval(updateCasosPositivosPoints, 300000); 
        //setInterval(updateCasosHeatmap, 300000);
        setInterval(updateHeatmapSwitch, 300000);
        setInterval(updateFocosAedes, 300000);
        setInterval(updatePontosEstrat, 300000);
        setInterval(updateArmadilhas, 300000);

        console.log("Inicialização do mapa concluída.");
    }).catch(error => {
        console.error("Erro fatal na inicialização das camadas:", error);
    });
    
setInterval(() => {
    if (map.hasLayer(clusterCasosLayer)) {
        clusterCasosLayer = updateClustersDinamico(LAYER_CLUSTERS_CASOS, 'Clusters de Casos (Focos Ativos)', clusterCasosLayer, 'casos').then(layer => {clusterCasosLayer = layer;});
    }
    if (map.hasLayer(clusterFocosLayer)) {
        clusterFocosLayer = updateClustersDinamico(LAYER_CLUSTERS_FOCOS, 'Clusters de Mosquitos (Áreas Críticas)', clusterFocosLayer, 'focos');
    }
}, 300000); // 5 minutos
};