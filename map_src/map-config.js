// --- 1. Variáveis de Configuração Global ---
const GEOSERVER_WFS_URL = 'http://192.168.0.190:8080/geoserver/wfs';
const WORKSPACE = 'vigiaa';
const LAYER_CASOS = 'casosposi_se';
const LAYER_FOCOS_SE = 'vw_focos_aedes';

// --- 2. Variáveis de Camadas (Serão populadas em map-main.js, mas declaradas globalmente) ---
// Usamos 'let' pois elas serão reatribuídas com as instâncias das camadas Leaflet
let bairrosWFSLayer;
let bairrosOfcWFSLayer;
let setCensWFSLayer;
let camboriuWFSLayer;
let curvasNivelWFSLayer;
let setCensDemoCambLayer;
let focosWFSLayer;
let peWFSLayer;
let armWFSLayer;
let currentCasosPointLayer; 
let currentCasosHeatmapLayer;
let declividadeImageLayer;
let demografiaImageLayer;
let currentFocosHeatmapLayer;
let clusterCasosLayer;
let clusterFocosLayer;

// --- 3. Definição dos Estilos (Funções Puras) ---
const bairrosStyleWFS = function(feature) { return { fillColor: '#add8e6', color: 'black', weight: 1, fillOpacity: 0.5 }; };
const bairrosOfcStyleWFS = function(feature) { return { fillColor: '#89d1fa', color: 'black', weight: 1, fillOpacity: 0.5 }; };
const setCensStyleWFS = function(feature) { return { fillColor: '#f07b73', color: 'black', weight: 1, fillOpacity: 0.5 }; };

const densDemoSetCensStyle = function (feature) {
    const classe = feature.properties.Classe;
    let fillColor;
    switch (classe) {
        case 1: fillColor = '#238b45'; break; case 2: fillColor = '#41ab5d'; break;
        case 3: fillColor = '#74c476'; break; case 4: fillColor = '#a1d99b'; break;
        case 5: fillColor = '#ECF74A'; break; case 6: fillColor = '#F54927'; break;
        case 7: fillColor = '#FF0000'; break; case 8: fillColor = '#b30000'; break;
        default: fillColor = '#cccccc';
    }
    return { fillColor: fillColor, color: 'black', weight: 0.5, fillOpacity: 1 };
};

const declividadePlStyle = function (feature) {
    const classe = feature.properties.CLASSE;
    let fillColor;
    switch (classe) {
        case '0 - 100m': fillColor = '#238b45'; break; case '100 - 200m': fillColor = '#41ab5d'; break;
        case '200 - 300m': fillColor = '#74c476'; break; case '300 - 400m': fillColor = '#a1d99b'; break;
        case '400 - 500m': fillColor = '#ECF74A'; break; case '500 - 600m': fillColor = '#F54927'; break;
        case '600 - 700m': fillColor = '#FF0000'; break; case '700 - 800m': fillColor = '#b30000'; break;
        default: fillColor = '#cccccc';
    }
    return { fillColor: fillColor, color: 'black', weight: 0.5, fillOpacity: 1 };
};

const curvasNivelStyleWFS = function (feature) { return { color: "#faf605", weight: 2, opacity: 1.0 }; };
const casosPointStyleWFS = function(feature) { return { radius: 5, fillColor: 'red', color: '#000', weight: 1, opacity: 1, fillOpacity: 0.7 }; };
const camboriuStyleWFS = function(feature) { return { fillColor: '#ffcc00', color: 'black', weight: 1, fillOpacity: 0.5 }; };
const focosStyleWFS = function(feature) { return { radius: 5, fillColor: 'orange', color: '#000', weight: 1, opacity: 1, fillOpacity: 0.7 }; };
const peStyleWFS = function(feature) { return { radius: 5, fillColor: 'green', color: '#000', weight: 1, opacity: 1, fillOpacity: 0.7 }; };
const armStyleWFS = function(feature) { return { radius: 5, fillColor: 'purple', color: '#000', weight: 1, opacity: 1, fillOpacity: 0.7 }; };

// --- 4. Funções de Utilitário (Ajudam a construir o mapa/filtro) ---

// Constrói a sintaxe de filtro WFS (Common Query Language)
function buildCqlFilter(year, se) {
    let filterArray = [];
    
    if (year && year !== '') {
        filterArray.push(`ano_se = ${year}`);
    }
    
    if (se && se !== '') {
        filterArray.push(`se_num = ${se}`);
    }

    return filterArray.length > 0 ? filterArray.join(' AND ') : '1=1'; 
}

// Busca dados GeoServer para os filtros (Retorna apenas os atributos, sem a geometria)
async function fetchGeoServerFilterData(layerName, cqlFilter = '1=1', requiredProps = '') {
    const fullLayerName = `${WORKSPACE}:${layerName}`;
    const params = {
        service: 'WFS', version: '2.0.0', request: 'GetFeature', typeName: fullLayerName,
        outputFormat: 'application/json', cql_filter: cqlFilter, propertyName: requiredProps 
    };
    
    const queryString = new URLSearchParams(params).toString();
    const fullUrl = `${GEOSERVER_WFS_URL}?${queryString}`;
    
    try {
        const response = await fetch(fullUrl);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status} ao consultar ${layerName}`);
        }
        const data = await response.json();
        return data.features.map(f => f.properties);
    } catch (error) {
        console.error(`Erro ao buscar dados de filtro para ${layerName}:`, error);
        return [];
    }
}