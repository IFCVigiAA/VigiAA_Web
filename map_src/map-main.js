// Acesso aos elementos do DOM
const selectYear = document.getElementById('filter-ano');
const selectMonth = document.getElementById('filter-mes');
const selectDay = document.getElementById('filter-dia');
const declividadeLegend = document.getElementById('declividade-legend');
const demografiaOfcLegend = document.getElementById('demografia_ofc-legend');
const heatmapLegend = document.getElementById('heatmap-legend');

// Variáveis de estado do filtro (inicializadas em map-main)
let selectedYear = '';
let selectedMonth = '';
let selectedDay = '';
let map; // Variável para a instância do mapa

// --- Funções de Ajuda para o Mapa ---

// Gerencia a substituição da camada no mapa e no controle
function refreshLayerInControl(oldLayer, newLayer, layerName) {
    const wasOnMap = oldLayer && map.hasLayer(oldLayer);
    if (wasOnMap) { map.removeLayer(oldLayer); }

    if (map.layersControl && oldLayer) {
        map.layersControl.removeLayer(oldLayer);
    }
    
    if (map.layersControl) {
        map.layersControl.addOverlay(newLayer, layerName);
    }

    if (wasOnMap) {
        newLayer.addTo(map);
    }
}

// Função Genérica para buscar e adicionar Camadas WFS (para GeoJSON)
function fetchWFSData(layerName, displayName, styleFunction, popupFields, version = '2.0.0', isPointLayer = false, cqlFilter = '1=1') {
    let fullLayerName = layerName;
    if (layerName.indexOf(':') === -1) {
        // Se NÃO incluir, adiciona o WORKSPACE padrão.
        fullLayerName = `${WORKSPACE}:${layerName}`;
    }
    //const fullLayerName = `${WORKSPACE}:${layerName}`;
    //const wfsUrl = `${GEOSERVER_WFS_URL}?`;
    var wfsUrl = `http://192.168.70.63:8080/geoserver/wfs?`;
    
    var params = {
        service: 'WFS', version: version, request: 'GetFeature', typeName: fullLayerName,
        outputFormat: 'application/json', cql_filter: cqlFilter
    };
    const queryString = new URLSearchParams(params).toString();
    const fullUrl = wfsUrl + queryString;

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
function updadeFocosAedes() {
    return fetchWFSData('vigiaa:focos_aedes_1604_com_coords', 'Focos Aedes (Dinâmico)', focosStyleWFS, ['id', 'Nº Foco'], '2.0.0', true).then(newLayer => {
        if (newLayer) { refreshLayerInControl(focosWFSLayer, newLayer, 'Focos Aedes (Dinâmico)'); focosWFSLayer = newLayer; }
        return focosWFSLayer;
    });
}
// ... Outras funções dinâmicas (updatePontosEstrat, updateArmadilhas) ...
function updatePontosEstrat() {
    return fetchWFSData('vigiaa:pontos_estrategicos', 'Pontos Estratégicos (Dinâmico)', peStyleWFS, ['id', 'numero'], '2.0.0', true).then(newLayer => {
        if (newLayer) { refreshLayerInControl(peWFSLayer, newLayer, 'Pontos Estratégicos (Dinâmico)'); peWFSLayer = newLayer; }
        return peWFSLayer;
    });
}
function updateArmadilhas() {
    return fetchWFSData('vigiaa:relat_arm', 'Armadilhas (Dinâmico)', armStyleWFS, ['id', 'numero'], '2.0.0', true).then(newLayer => {
        if (newLayer) { refreshLayerInControl(armWFSLayer, newLayer, 'Armadilhas (Dinâmico)'); armWFSLayer = newLayer; }
        return armWFSLayer;
    });
}

function updateCasosPositivosPoints() {
    const filter = buildCqlFilter(selectedYear, selectedMonth, selectedDay); // Obtém filtro atual
    return fetchWFSData(LAYER_NAME_DATAS, 'Casos Positivos (Pontos)', casosPointStyleWFS, ['id', 'data'], '2.0.0', true, filter).then(newLayer => {
        if (newLayer) { refreshLayerInControl(currentCasosPointLayer, newLayer, 'Casos Positivos (Pontos)'); currentCasosPointLayer = newLayer; }
        return currentCasosPointLayer;
    });
}

function updateCasosHeatmap() {
    const filter = buildCqlFilter(selectedYear, selectedMonth, selectedDay);
    const wfsUrl = `http://192.168.70.63:8080/geoserver/wfs?`;
    const params = { service: 'WFS', version: '2.0.0', request: 'GetFeature', typeName: `${WORKSPACE}:${LAYER_NAME_DATAS}`, outputFormat: 'application/json', cql_filter: filter };
    const queryString = new URLSearchParams(params).toString();
    const fullUrl = wfsUrl + queryString;
    
    return fetch(fullUrl)
        .then(response => {
            if (!response.ok) { throw new Error(`HTTP error! status: ${response.status} for Casos Positivos (Heatmap)`); }
            return response.json();
        })
        .then(data => {
            var heatData = [];
            if (data && data.features) {
                data.features.forEach(feature => {
                    if (feature.geometry && feature.geometry.coordinates) {
                        var coords = feature.geometry.coordinates; 
                        heatData.push([coords[1], coords[0]]);
                    }
                });
            }
            
            var newHeatmapLayer = L.heatLayer(heatData, { radius: 25, blur: 15, maxZoom: 17, minOpacity: 0.2, gradient: { 0.0: 'blue', 0.25: 'cyan', 0.5: 'lime', 0.75: 'yellow', 1.0: 'red' } });
            newHeatmapLayer.name = 'Casos Positivos (Mapa de Calor)';
            
            // 🔑 REATIVANDO a lógica de substituição de camadas para atualizações dinâmicas
            if (currentCasosHeatmapLayer) {
                // Se currentCasosHeatmapLayer existe (após a 1ª carga), use o refreshLayerInControl
                refreshLayerInControl(currentCasosHeatmapLayer, newHeatmapLayer, newHeatmapLayer.name);
                currentCasosHeatmapLayer = newHeatmapLayer;
            } else {
                // Durante a primeira carga (no Promise.all), apenas atribua e retorne.
                currentCasosHeatmapLayer = newHeatmapLayer;
            }
            
            return newHeatmapLayer; // Retorna a camada para o Promise.all (inicialização)
            
        })
        .catch(error => { console.error(`Erro ao buscar ou processar dados para Casos Positivos (Heatmap):`, error); return null; });
}

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

async function populateYears() {
    const anosData = await fetchGeoServerFilterData(LAYER_NAME_ANOS, '1=1', 'ano');
    const distinctYears = new Set(anosData.map(data => data.ano).filter(a => a));
    
    selectYear.innerHTML = '<option value="">Todos</option>'; 
    Array.from(distinctYears).sort().forEach(ano => {
        const option = document.createElement('option');
        option.value = ano;
        option.textContent = ano;
        selectYear.appendChild(option);
    });

    selectYear.addEventListener('change', handleYearChange);
}

async function handleYearChange(event) {
    selectedYear = event.target.value;
    
    selectedMonth = ''; selectedDay = '';
    
    selectDay.innerHTML = '<option value="">Todos</option>';
    selectDay.disabled = true;

    selectMonth.innerHTML = '<option value="">Todos</option>';
    
    if (selectedYear) {
        selectMonth.disabled = false;
        await populateMonths(selectedYear);
    } else {
        selectMonth.disabled = true;
    }
    
    updateMapLayers();
}

async function populateMonths(year) {
    const cql = `ano='${year}'`;
    const mesesData = await fetchGeoServerFilterData(LAYER_NAME_DATAS, cql, 'meses,nome_mes');
    const distinctMonths = new Map(); 
    
    mesesData.forEach(data => {
        if (data.meses && !distinctMonths.has(data.meses)) {
            distinctMonths.set(data.meses, { meses: data.meses, nome_mes: data.nome_mes });
        }
    });
    
    const sortedMonths = Array.from(distinctMonths.values()).sort((a, b) => a.meses.localeCompare(b.meses));
    
    selectMonth.innerHTML = '<option value="">Todos</option>';
    
    sortedMonths.forEach(data => {
        const option = document.createElement('option');
        option.value = data.meses; 
        option.textContent = data.nome_mes;
        selectMonth.appendChild(option);
    });

    selectMonth.addEventListener('change', handleMonthChange);
}

async function handleMonthChange(event) {
    selectedMonth = event.target.value;

    selectedDay = '';
    selectDay.innerHTML = '<option value="">Todos</option>';
    
    if (selectedMonth && selectedYear) {
        selectDay.disabled = false;
        await populateDays(selectedYear, selectedMonth);
    } else {
        selectDay.disabled = true;
    }

    updateMapLayers();
}

async function populateDays(year, month) {
    const cql = `ano='${year}' AND meses='${month}'`;
    const diasData = await fetchGeoServerFilterData(LAYER_NAME_DATAS, cql, 'dias');
    const distinctDays = new Set(diasData.map(data => data.dias).filter(d => d));
    const sortedDays = Array.from(distinctDays).sort();

    selectDay.innerHTML = '<option value="">Todos</option>';
    
    sortedDays.forEach(dia => {
        const option = document.createElement('option');
        option.value = dia; 
        option.textContent = dia;
        selectDay.appendChild(option);
    });

    selectDay.addEventListener('change', handleDayChange);
}

function handleDayChange(event) {
    selectedDay = event.target.value;
    updateMapLayers();
}

// Recarrega as camadas dinâmicas com o filtro atual
function updateMapLayers() {
    updateCasosPositivosPoints();
    updateCasosHeatmap();
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
        updadeFocosAedes(), updatePontosEstrat(), updateArmadilhas(), 
        updateCasosPositivosPoints(), updateCasosHeatmap(),
        loadImageLayers(), loadDeclividadePoligonoOnce(), loadDensDemoSetCensOnce()
    ]).then(results => {
        // Atribui os resultados às variáveis globais e as adiciona ao overlayMaps
        [
            bairrosWFSLayer, bairrosOfcWFSLayer, setCensWFSLayer, camboriuWFSLayer, curvasNivelWFSLayer, 
            focosWFSLayer, peWFSLayer, armWFSLayer, 
            currentCasosPointLayer, currentCasosHeatmapLayer,
            [declividadeImageLayer, demografiaImageLayer], declividadePlLayer, setCensDemoCambLayer
        ] = results;

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


        // 3. Adiciona Controle de Camadas
        map.layersControl = L.control.layers(baseLayers, overlayMaps, { position: 'topright', collapsed: true }).addTo(map);

        // 4. Configuração de Eventos do Mapa (Legendas)
        map.on('overlayadd', function (e) {
            if (e.name === 'Casos Positivos (Mapa de Calor)') { heatmapLegend.style.display = 'block'; }
            if (e.name === 'Declividade (Polígonos)') { declividadeLegend.style.display = 'block'; }
            if (e.name === 'Densidade Demográfica (SC)') { demografiaOfcLegend.style.display = 'block'; }
        });

        map.on('overlayremove', function (e) {
            if (e.name === 'Casos Positivos (Mapa de Calor)') { heatmapLegend.style.display = 'none'; }
            if (e.name === 'Declividade (Polígonos)') { declividadeLegend.style.display = 'none'; }
            if (e.name === 'Densidade Demográfica (SC)') { demografiaOfcLegend.style.display = 'none'; }
        });
        
        // 5. Configuração de Atualização em Intervalos
        setInterval(updateCasosPositivosPoints, 300000); 
        setInterval(updateCasosHeatmap, 300000);
        setInterval(updadeFocosAedes, 300000);
        setInterval(updatePontosEstrat, 300000);
        setInterval(updateArmadilhas, 300000);

        console.log("Inicialização do mapa concluída.");
    }).catch(error => {
        console.error("Erro fatal na inicialização das camadas:", error);
    });
    
    // 6. Popula o primeiro filtro (Anos)
    populateYears();
};