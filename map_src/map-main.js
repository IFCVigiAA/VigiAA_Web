// Acesso aos elementos do DOM
const selectYear = document.getElementById('filter-ano');
const selectSE = document.getElementById('filter-SE');
const declividadeLegend = document.getElementById('declividade-legend');
const demografiaOfcLegend = document.getElementById('demografia_ofc-legend');
const heatmapLegend = document.getElementById('heatmap-legend');

const LAYER_CLUSTERS_CASOS = 'vw_clusters_casos'; 
const LAYER_CLUSTERS_FOCOS = 'vw_clusters_focos';    

let playbackInterval = { casos: null, focos: null, ovitrampas: null, 'pontos-est': null };
let isPlaying = { casos: false, focos: false, ovitrampas: false, 'pontos-est': false };

let selectedYear = '';
let selectedSE = '';
let map; 

// --- Funções de Ajuda para o Mapa ---

function addLayerToControlUnique(layer, name) {
    if (!map.layersControl || !layer) return;

    const controlLayers = map.layersControl._layers;
    for (let i = controlLayers.length - 1; i >= 0; i--) {
        if (controlLayers[i].name === name) {
            map.layersControl.removeLayer(controlLayers[i].layer);
        }
    }
    map.layersControl.addOverlay(layer, name);
}

function refreshLayerInControl(oldLayer, newLayer, layerName) {
    const wasOnMap = oldLayer && oldLayer instanceof L.Layer && map.hasLayer(oldLayer);

    if (oldLayer && wasOnMap) {
        map.removeLayer(oldLayer);
    }

    if (map.layersControl && oldLayer && oldLayer instanceof L.Layer) {
        try {
            map.layersControl.removeLayer(oldLayer);
        } catch (e) {
            console.warn("Camada já removida ou inexistente no controle.");
        }
    }

    if (map.layersControl && newLayer) {
        addLayerToControlUnique(newLayer, layerName);
    }

    if (wasOnMap && newLayer) {
        newLayer.addTo(map);
    }
}

function adjustMenuPosition() {
    const layersControl = document.querySelector('.leaflet-control-layers');
    if (!layersControl) return;

    const casosAtivo = map.hasLayer(currentCasosPointLayer);
    const focosAtivo = map.hasLayer(focosWFSLayer);
    const ovitrampasAtivo = map.hasLayer(ovitrampasWFSLayer);
    const peAtivo = map.hasLayer(peWFSLayer);

    layersControl.classList.remove('pushed-1', 'pushed-2', 'leaflet-control-layers-pushed');

    let paineisAbertos = 0;
    if (casosAtivo) paineisAbertos++;
    if (focosAtivo) paineisAbertos++;
    if (ovitrampasAtivo) paineisAbertos++;
    if (peAtivo) paineisAbertos++;

    if (paineisAbertos === 1) {
        layersControl.classList.add('pushed-1');
    } else if (paineisAbertos >= 2) {
        layersControl.classList.add('pushed-2');
    }
}

function fetchWFSData(layerName, displayName, styleFunction, popupFields, version = '2.0.0', isPointLayer = false, cqlFilter = '1=1', customPane = 'overlayPane') {
    let fullLayerName = layerName;
    if (layerName.indexOf(':') === -1) {
        fullLayerName = `${WORKSPACE}:${layerName}`;
    }

    const params = {
        service: 'WFS', version: version, request: 'GetFeature', typeName: fullLayerName,
        outputFormat: 'application/json', cql_filter: cqlFilter
    };
    const fullUrl = `${GEOSERVER_WFS_URL}?` + new URLSearchParams(params).toString();

    return fetch(fullUrl)
        .then(response => {
            if (!response.ok) { throw new Error(`HTTP error! status: ${response.status} for ${displayName}`); }
            return response.json();
        })
        .then(data => {
            var layerOptions = {
                pane: customPane,
                style: styleFunction,
                onEachFeature: function(feature, layer) {
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

// --- Funções de Carga Estática ---
function loadBairrosOnce() { return fetchWFSData('vigiaa_ofc:vw_bairros_cb_ofc', 'Bairros - Oficial ', bairrosStyleWFS, ['nome']); }
function loadSetCensOnce() { return fetchWFSData('vigiaa_ofc:vw_set_cens_camb', 'Setores Censitários ', setCensStyleWFS, ['Nome do Bairro']); }
function loadDensDemoSetCensOnce() { return fetchWFSData('vigiaa_ofc:vw_set_cens_demo_camb_classes', 'Densidade Demográfica ', densDemoSetCensStyle, ['Densidade Demografica por KM2']); }
function loadBairrosOfcOnce() { return fetchWFSData('vigiaa_ofc:vw_bairros_cb_ibge', 'Bairros - IBGE ', bairrosOfcStyleWFS, ['Nome']); }
function loadCamboriuOnce() { return fetchWFSData('vigiaa_ofc:vw_mun_camb', 'Camboriú ', camboriuStyleWFS, ['']); }
function loadCurvaNivelOnce() { return fetchWFSData('vigiaa_ofc:vw_cv_nvl_camboriu_li', 'Curva de Nível ', curvasNivelStyleWFS, ['Altura']); } 
function loadDeclividadePoligonoOnce() { return fetchWFSData('vigiaa_ofc:vw_cv_nvl_camboriu_union', 'Declividade ', declividadePlStyle, ['Altura']); }

// --- Funções de Atualização Dinâmica ---
function updateFocosAedes() {
    const filter = buildCqlFilter(selectedYear, selectedSE);
    return fetchWFSData(LAYER_FOCOS_SE, 'Focos Aedes ', focosStyleWFS, ['id', 'n_foco', 'a_aegypti_form_aquaticas', 'a_aegypti_form_adultas', 'a_albopictus_form_aquaticas', 'a_albopictus_form_adultas', 'ovo_a_aegypti'], '2.0.0', true, filter).then(newLayer => {
        if (newLayer) { 
            refreshLayerInControl(focosWFSLayer, newLayer, 'Focos Aedes '); 
            focosWFSLayer = newLayer; 
        }
        return focosWFSLayer;
    });
}

function updatePontosEstrat() {
    const filter = buildCqlFilter(selectedYear, selectedSE);
    return fetchWFSData(LAYER_PONTOS_EST, 'Pontos Estratégicos ', peStyleWFS, ['id', 'numero'], '2.0.0', true, filter).then(newLayer => {
        if (newLayer) { 
            refreshLayerInControl(peWFSLayer, newLayer, 'Pontos Estratégicos '); 
            peWFSLayer = newLayer; 
        }
        return peWFSLayer;
    });
}

function updateOvitrampas() {
    const filter = buildCqlFilter(selectedYear, selectedSE);
    return fetchWFSData(LAYER_OVITRAMPAS, 'Ovitrampas ', ovitrampasStyleWFS, ['id_ovitrampa', 'ovos_aegypti', 'ovos_albopictus', 'outros_ovos', 'ano_se', 'se_num'], '2.0.0', true, filter).then(newLayer => {
        if (newLayer) { 
            refreshLayerInControl(ovitrampasWFSLayer, newLayer, 'Ovitrampas '); 
            ovitrampasWFSLayer = newLayer; 
        }
        return ovitrampasWFSLayer;
    });
}

function updateArmadilhas() {
    return fetchWFSData('vigiaa_ofc:relat_arm', 'Armadilhas ', armStyleWFS, ['id', 'numero', 'tipo_imovel'], '2.0.0', true).then(newLayer => {
        if (newLayer) { refreshLayerInControl(armWFSLayer, newLayer, 'Armadilhas '); armWFSLayer = newLayer; }
        return armWFSLayer;
    });
}

function updateCasosPositivosPoints() {
    const filter = buildCqlFilter(selectedYear, selectedSE); 
    return fetchWFSData(LAYER_CASOS, 'Casos Positivos ', casosPointStyleWFS, ['id', 'inicio_sintomas'], '2.0.0', true, filter).then(newLayer => {
        if (newLayer) { refreshLayerInControl(currentCasosPointLayer, newLayer, 'Casos Positivos '); currentCasosPointLayer = newLayer; }
        return currentCasosPointLayer;
    });
}

function updateHeatmapSwitch() {
    const context = getActiveLayerContext(); 
    const isFocos = context.type === 'focos';
    const targetLayer = isFocos ? currentFocosHeatmapLayer : currentCasosHeatmapLayer;

    if (!targetLayer || !map.hasLayer(targetLayer)) return;

    const filter = buildCqlFilter(selectedYear, selectedSE);
    const params = { 
        service: 'WFS', version: '2.0.0', request: 'GetFeature', 
        typeName: `${WORKSPACE}:${context.table}`, outputFormat: 'application/json', cql_filter: filter
    };
    
    const fullUrl = `${GEOSERVER_WFS_URL}?` + new URLSearchParams(params).toString();

    return fetch(fullUrl)
        .then(response => response.json())
        .then(data => {
            const heatData = data.features.map(f => [
                f.geometry.coordinates[1], 
                f.geometry.coordinates[0]
            ]);
            
            const gradient = isFocos 
                ? { 0.0: 'blue', 0.5: 'lime', 1.0: 'orange' } 
                : { 0.0: 'blue', 0.5: 'yellow', 1.0: 'red' };

            targetLayer.setLatLngs(heatData);
            targetLayer.setOptions({ gradient: gradient });
        })
        .catch(error => console.error(`Erro no Switch Heatmap (${context.type}):`, error));
}

function updateClustersDinamico(layerName, displayName, currentLayerVar, contextType) {
    const isCasos = contextType === 'casos';
    const elYear = document.getElementById(isCasos ? 'filter-ano-casos' : 'filter-ano-focos');
    const elSE = document.getElementById(isCasos ? 'filter-se-casos' : 'filter-se-focos');
    
    const year = elYear ? elYear.value : '';
    const se = elSE ? elSE.value : '';

    const filter = buildCqlFilter(year, se);
    const popupFields = isCasos ? ['total_casos', 'se_num', 'ano_se'] : ['total_focos', 'se_num', 'ano_se'];
    const styleFunc = isCasos ? clusterCasosStyle : clusterFocosStyle;

    return fetchWFSData(layerName, displayName, styleFunc, popupFields, '2.0.0', false, filter, 'clustersPane')
        .then(newLayer => {
            if (newLayer) {
                refreshLayerInControl(currentLayerVar, newLayer, displayName);
                if (isCasos) {
                    clusterCasosLayer = newLayer;
                } else {
                    clusterFocosLayer = newLayer;
                }
            }
            return newLayer;
        })
        .catch(error => {
            console.error(`Erro clusters (${contextType}):`, error);
            return null;
        });
}

const clusterCasosStyle = function(feature) {
    return { fillColor: '#d73027', color: '#a50026', weight: 2, opacity: 1, fillOpacity: 0.6 };
};

const clusterFocosStyle = function(feature) {
    return { fillColor: '#1a9850', color: '#006837', weight: 2, opacity: 1, fillOpacity: 0.6 };
};

// --- Funções de Manipulação de Anos e Semanas Epidemiológicas ---

async function populateSpecificYears(context, layerName, selectId) {
    const selectElement = document.getElementById(selectId);
    if (!selectElement) return;

    if (selectElement.options.length > 1 && selectElement.value !== "") return;

    const data = await fetchGeoServerFilterData(layerName, '1=1', 'ano_se');
    const years = [...new Set(data.map(item => item.ano_se))].filter(a => a).sort((a, b) => b - a);

    const currentValue = selectElement.value;
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
    let table = LAYER_CASOS;
    if (context === 'focos') table = LAYER_FOCOS_SE;
    if (context === 'ovitrampas') table = LAYER_OVITRAMPAS;
    if (context === 'pontos-est') table = LAYER_PONTOS_EST;

    const seSelectId = `filter-se-${context}`;
    const seSelect = document.getElementById(seSelectId);
    if (!seSelect) return;

    if (!year) {
        seSelect.innerHTML = '<option value="">SE*</option>';
        seSelect.disabled = true;
        updateLayerByContext(context);
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

async function updateLayerByContext(context) {
    const yearElement = document.getElementById(`filter-ano-${context}`);
    const seElement = document.getElementById(`filter-se-${context}`);
    
    if (!yearElement || !seElement) return;

    const yearVal = yearElement.value;
    const seVal = seElement.value;
    
    let layer, table;
    if (context === 'casos') { layer = currentCasosPointLayer; table = LAYER_CASOS; }
    else if (context === 'focos') { layer = focosWFSLayer; table = LAYER_FOCOS_SE; }
    else if (context === 'ovitrampas') { layer = ovitrampasWFSLayer; table = LAYER_OVITRAMPAS; }
    else if (context === 'pontos-est') { layer = peWFSLayer; table = LAYER_PONTOS_EST; }

    const filter = buildCqlFilter(yearVal, seVal);
    const url = `${GEOSERVER_WFS_URL}?service=WFS&version=2.0.0&request=GetFeature&typeName=${WORKSPACE}:${table}&outputFormat=application/json&cql_filter=${encodeURIComponent(filter)}`;
    
    try {
        const response = await fetch(url);
        const data = await response.json();
        
        if (layer && typeof layer.clearLayers === 'function') {
            layer.clearLayers();
            layer.addData(data);
        }

        if (context === 'casos') {
            updateClustersDinamico(LAYER_CLUSTERS_CASOS, 'Clusters de Casos (Focos Ativos)', clusterCasosLayer, 'casos');
            updateHeatmapData(context, data);
        } else if (context === 'focos') {
            updateClustersDinamico(LAYER_CLUSTERS_FOCOS, 'Clusters de Focos (Áreas Críticas)', clusterFocosLayer, 'focos');
            updateHeatmapData(context, data);
        }
        
    } catch (e) {
        console.error(`Erro ao filtrar ${context}:`, e);
    }
}

function updateHeatmapData(context, geojsonData) {
    const isCasos = context === 'casos';
    const targetHeatLayer = isCasos ? currentCasosHeatmapLayer : currentFocosHeatmapLayer;
    
    if (!targetHeatLayer || !map.hasLayer(targetHeatLayer) || !map._loaded) return;

    const heatPoints = geojsonData.features.map(f => [
        f.geometry.coordinates[1], 
        f.geometry.coordinates[0]
    ]);

    requestAnimationFrame(() => {
        try {
            if (targetHeatLayer._map) {
                targetHeatLayer.setLatLngs(heatPoints);
            }
        } catch (err) {
            console.warn("Heatmap ocupado.");
        }
    });
}

function getActiveLayerContext() {
    if (currentCasosPointLayer && map.hasLayer(currentCasosPointLayer)) return { table: LAYER_CASOS, type: 'casos' };
    if (focosWFSLayer && map.hasLayer(focosWFSLayer)) return { table: LAYER_FOCOS_SE, type: 'focos' };
    if (ovitrampasWFSLayer && map.hasLayer(ovitrampasWFSLayer)) return { table: LAYER_OVITRAMPAS, type: 'ovitrampas' };
    if (peWFSLayer && map.hasLayer(peWFSLayer)) return { table: LAYER_PONTOS_EST, type: 'pontos-est' };
    if (currentFocosHeatmapLayer && map.hasLayer(currentFocosHeatmapLayer)) return { table: LAYER_FOCOS_SE, type: 'focos' };
    return { table: LAYER_CASOS, type: 'casos' };
}

// --- INICIALIZAÇÃO DO MAPA ---
window.onload = function() {
    document.querySelectorAll('#btn-play').forEach(btn => {
        btn.addEventListener('click', function() {
            const groupEl = this.closest('.filter-group');
            if (!groupEl) return;
            let context = 'casos';
            if (groupEl.id.includes('focos')) context = 'focos';
            else if (groupEl.id.includes('ovitrampas')) context = 'ovitrampas';
            else if (groupEl.id.includes('pontos-est')) context = 'pontos-est';

            togglePlayback(context, this);
        });
    });

    async function togglePlayback(context, btnElement) {
        if (isPlaying[context]) {
            stopPlayback(context, btnElement);
        } else {
            startPlayback(context, btnElement);
        }
    }

    map = L.map('mapid').setView([-27.0258, -48.6549], 12);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors'
    }).addTo(map);

    map.createPane('clustersPane');
    map.getPane('clustersPane').style.zIndex = 390;

    var baseLayers = {}; 
    var overlayMaps = {}; 

    // Ovitrampas e Pontos Estratégicos incluídos corretamente na promessa inicial
    Promise.all([
        loadBairrosOnce(), loadBairrosOfcOnce(), loadSetCensOnce(), loadCamboriuOnce(), loadCurvaNivelOnce(),
        updateFocosAedes(), updatePontosEstrat(), updateOvitrampas(), updateArmadilhas(), 
        updateCasosPositivosPoints(), 
        loadDeclividadePoligonoOnce(), loadDensDemoSetCensOnce(),
        updateClustersDinamico(LAYER_CLUSTERS_CASOS, 'Clusters de Casos (Focos Ativos)', null, 'casos'),
        updateClustersDinamico(LAYER_CLUSTERS_FOCOS, 'Clusters de Focos (Áreas Críticas)', null, 'focos')
    ]).then(results => {
        [
            bairrosWFSLayer, bairrosOfcWFSLayer, setCensWFSLayer, camboriuWFSLayer, curvasNivelWFSLayer, 
            focosWFSLayer, peWFSLayer, ovitrampasWFSLayer, armWFSLayer, 
            currentCasosPointLayer, 
            declividadePlLayer, setCensDemoCambLayer, 
            clusterCasosLayer, clusterFocosLayer
        ] = results;

        if (bairrosWFSLayer) overlayMaps[bairrosWFSLayer.name] = bairrosWFSLayer;
        if (bairrosOfcWFSLayer) overlayMaps[bairrosOfcWFSLayer.name] = bairrosOfcWFSLayer;
        if (setCensWFSLayer) overlayMaps[setCensWFSLayer.name] = setCensWFSLayer;
        if (curvasNivelWFSLayer) overlayMaps[curvasNivelWFSLayer.name] = curvasNivelWFSLayer;
        if (declividadePlLayer) overlayMaps[declividadePlLayer.name] = declividadePlLayer;
        if (setCensDemoCambLayer) overlayMaps[setCensDemoCambLayer.name] = setCensDemoCambLayer;
        if (camboriuWFSLayer) overlayMaps[camboriuWFSLayer.name] = camboriuWFSLayer;
        
        if (currentCasosPointLayer) overlayMaps[currentCasosPointLayer.name] = currentCasosPointLayer;
        
        currentCasosHeatmapLayer = L.heatLayer([], { radius: 25 });
        currentCasosHeatmapLayer.name = 'Positivos (Mapa de Calor)';

        if (focosWFSLayer) overlayMaps[focosWFSLayer.name] = focosWFSLayer;
        currentFocosHeatmapLayer = L.heatLayer([], { radius: 25 });
        currentFocosHeatmapLayer.name = 'Focos (Mapa de Calor)';

        if (peWFSLayer) overlayMaps[peWFSLayer.name] = peWFSLayer;
        if (ovitrampasWFSLayer) overlayMaps[ovitrampasWFSLayer.name] = ovitrampasWFSLayer;
        if (armWFSLayer) overlayMaps[armWFSLayer.name] = armWFSLayer;
        if (currentCasosHeatmapLayer) overlayMaps[currentCasosHeatmapLayer.name] = currentCasosHeatmapLayer;

        map.layersControl = L.control.layers(baseLayers, overlayMaps, { 
            position: 'topright', 
            collapsed: true,
            sortLayers: true,
            sortFunction: function (layerA, layerB, nameA, nameB) {
                const order = [
                    'Bairros - Oficial', 'Bairros - IBGE', 'Setores Censitários',
                    'Curva de Nível', 'Declividade', 'Densidade Demográfica', 'Camboriú',
                    'Casos Positivos', 'Positivos (Mapa de Calor)', 'Clusters de Casos', 
                    'Focos Aedes', 'Focos (Mapa de Calor)', 'Clusters de Focos', 
                    'Pontos Estratégicos', 'Ovitrampas', 'Armadilhas'
                ];
                let idxA = order.findIndex(item => nameA.trim().startsWith(item));
                let idxB = order.findIndex(item => nameB.trim().startsWith(item));
                return (idxA === -1 ? 999 : idxA) - (idxB === -1 ? 999 : idxB);
            }
        }).addTo(map);

        function organizarLegendas() {
            const legendas = [
                document.getElementById('declividade-legend'),
                document.getElementById('demografia_ofc-legend'),
                document.getElementById('heatmap-legend')
            ];
            let alturaAcumulada = 10;
            const espacamento = 15;
            legendas.forEach(legenda => {
                if (legenda && legenda.style.display !== 'none') {
                    legenda.style.bottom = alturaAcumulada + "px";
                    alturaAcumulada += legenda.offsetHeight + espacamento;
                }
            });
        }

        // --- Eventos de Adição de Camada ---
        map.on('overlayadd', function (e) {
            const mainContainer = document.getElementById('main-filter-container');
    
            if (e.name === 'Casos Positivos ') {
                mainContainer.style.display = 'flex';
                document.getElementById('group-filter-casos').style.display = 'block';
                populateSpecificYears('casos', LAYER_CASOS, 'filter-ano-casos');
                if (map.layersControl) {
                    addLayerToControlUnique(currentCasosHeatmapLayer, currentCasosHeatmapLayer.name);
                    if (clusterCasosLayer) addLayerToControlUnique(clusterCasosLayer, clusterCasosLayer.name);
                }
            }
            
            if (e.name === 'Focos Aedes ') {
                mainContainer.style.display = 'flex';
                document.getElementById('group-filter-focos').style.display = 'block';
                populateSpecificYears('focos', LAYER_FOCOS_SE, 'filter-ano-focos');
                if (map.layersControl) {
                    addLayerToControlUnique(currentFocosHeatmapLayer, currentFocosHeatmapLayer.name);
                    if (clusterFocosLayer) addLayerToControlUnique(clusterFocosLayer, clusterFocosLayer.name);
                }
            }

            if (e.name === 'Pontos Estratégicos ') {
                mainContainer.style.display = 'flex';
                document.getElementById('group-filter-pontos-est').style.display = 'block';
                populateSpecificYears('pontos-est', LAYER_PONTOS_EST, 'filter-ano-pontos-est');
            }

            if (e.name === 'Ovitrampas ') {
                mainContainer.style.display = 'flex';
                document.getElementById('group-filter-ovitrampas').style.display = 'block';
                populateSpecificYears('ovitrampas', LAYER_OVITRAMPAS, 'filter-ano-ovitrampas');
            }

            if (e.name.includes('Mapa de Calor')) { heatmapLegend.style.display = 'block'; }
            if (e.name === 'Declividade ') { declividadeLegend.style.display = 'block'; }
            if (e.name === 'Densidade Demográfica ') { demografiaOfcLegend.style.display = 'block'; }

            adjustMenuPosition();
            setTimeout(organizarLegendas, 100);
        });

        // --- Eventos de Remoção de Camada ---
        map.on('overlayremove', function (e) {
            let contextToRemove = null;
            if (e.name === 'Casos Positivos ') contextToRemove = 'casos';
            if (e.name === 'Focos Aedes ') contextToRemove = 'focos';
            if (e.name === 'Pontos Estratégicos ') contextToRemove = 'pontos-est';
            if (e.name === 'Ovitrampas ') contextToRemove = 'ovitrampas';

            if (contextToRemove) {
                const ano = document.getElementById(`filter-ano-${contextToRemove}`);
                const se = document.getElementById(`filter-se-${contextToRemove}`);
                if (ano) ano.value = "";
                if (se) {
                    se.innerHTML = '<option value="">SE*</option>';
                    se.disabled = true;
                }
                
                if (contextToRemove === 'casos') {
                    if (map.layersControl) {
                        map.layersControl.removeLayer(currentCasosHeatmapLayer);
                        if (clusterCasosLayer) map.layersControl.removeLayer(clusterCasosLayer);
                    }
                    map.removeLayer(currentCasosHeatmapLayer);
                    if (clusterCasosLayer) map.removeLayer(clusterCasosLayer);
                }
                
                if (contextToRemove === 'focos') {
                    if (map.layersControl) {
                        map.layersControl.removeLayer(currentFocosHeatmapLayer);
                        if (clusterFocosLayer) map.layersControl.removeLayer(clusterFocosLayer);
                    }
                    map.removeLayer(currentFocosHeatmapLayer);
                    if (clusterFocosLayer) map.removeLayer(clusterFocosLayer);
                }
                
                document.getElementById(`group-filter-${contextToRemove}`).style.display = 'none';
            }

            const casosAtivo = map.hasLayer(currentCasosPointLayer);
            const focosAtivo = map.hasLayer(focosWFSLayer);
            const ovitrampasAtivo = map.hasLayer(ovitrampasWFSLayer);
            const peAtivo = map.hasLayer(peWFSLayer);

            if (!casosAtivo && !focosAtivo && !ovitrampasAtivo && !peAtivo) {
                document.getElementById('main-filter-container').style.display = 'none';
            }

            adjustMenuPosition();
            const heatmapAtivo = map.hasLayer(currentCasosHeatmapLayer) || map.hasLayer(currentFocosHeatmapLayer);
            if (!heatmapAtivo) heatmapLegend.style.display = 'none';
            if (e.name === 'Declividade ') declividadeLegend.style.display = 'none';
            if (e.name === 'Densidade Demográfica ') demografiaOfcLegend.style.display = 'none';
            
            organizarLegendas();
        });

        // Intervalos de atualização em segundo plano
        setInterval(updateCasosPositivosPoints, 300000); 
        setInterval(updateHeatmapSwitch, 300000);
        setInterval(updateFocosAedes, 300000);
        setInterval(updatePontosEstrat, 300000);
        setInterval(updateOvitrampas, 300000);
        setInterval(updateArmadilhas, 300000);

        console.log("Inicialização do mapa concluída.");
    }).catch(error => {
        console.error("Erro fatal na inicialização das camadas:", error);
    });
};

async function startPlayback(context, btnElement) {
    let table = LAYER_CASOS;
    if (context === 'focos') table = LAYER_FOCOS_SE;
    if (context === 'ovitrampas') table = LAYER_OVITRAMPAS;
    if (context === 'pontos-est') table = LAYER_PONTOS_EST;
    
    const selectAno = document.getElementById(`filter-ano-${context}`);
    const selectSE = document.getElementById(`filter-se-${context}`);
    
    if (!selectAno) return;
    const yearVal = selectAno.value;

    if (!yearVal) {
        alert("Selecione um ano primeiro para ver a evolução temporal.");
        return;
    }

    const seData = await fetchGeoServerFilterData(table, `ano_se=${yearVal}`, 'se_num');
    const distinctSE = [...new Set(seData.map(item => item.se_num))].sort((a, b) => a - b);

    if (distinctSE.length === 0) {
        alert("Nenhuma semana encontrada para este ano.");
        return;
    }

    isPlaying[context] = true;
    btnElement.innerText = " ⏸ Pausar";
    
    let currentIndex = 0;
    if (selectSE.value) {
        currentIndex = distinctSE.indexOf(parseInt(selectSE.value));
        if (currentIndex === -1) currentIndex = 0;
    }

    playbackInterval[context] = setInterval(async () => {
        if (currentIndex >= distinctSE.length) {
            currentIndex = 0; 
        }

        const currentSE = distinctSE[currentIndex];
        selectSE.value = currentSE;
        
        await updateLayerByContext(context);
        
        currentIndex++;
    }, 1200); 
}

function stopPlayback(context, btnElement) {
    isPlaying[context] = false;
    clearInterval(playbackInterval[context]);
    
    if (btnElement) {
        btnElement.innerText = "▶ Reproduzir Evolução";
    }
}