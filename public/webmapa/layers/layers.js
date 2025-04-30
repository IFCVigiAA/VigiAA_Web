var wms_layers = [];

var lyr_MDE_camboriu2_0 = new ol.layer.Image({
        opacity: 1,
        
    title: 'MDE_camboriu2<br />\
    <img src="styles/legend/MDE_camboriu2_0_0.png" /> <= 16,7500<br />\
    <img src="styles/legend/MDE_camboriu2_0_1.png" /> 16,7500 - 33,4000<br />\
    <img src="styles/legend/MDE_camboriu2_0_2.png" /> 33,4000 - 50,0500<br />\
    <img src="styles/legend/MDE_camboriu2_0_3.png" /> 50,0500 - 66,7000<br />\
    <img src="styles/legend/MDE_camboriu2_0_4.png" /> 66,7000 - 83,3500<br />\
    <img src="styles/legend/MDE_camboriu2_0_5.png" /> > 83,3500<br />' ,
        
        
        source: new ol.source.ImageStatic({
            url: "./layers/MDE_camboriu2_0.png",
            attributions: ' ',
            projection: 'EPSG:3857',
            alwaysInRange: true,
            imageExtent: [-5433751.587986, -3142850.586682, -5411394.884375, -3119967.228152]
        })
    });
var lyr_MDE_camboriu_1 = new ol.layer.Image({
        opacity: 1,
        
    title: 'MDE_camboriu<br />\
    <img src="styles/legend/MDE_camboriu_1_0.png" /> <= 16,750000<br />\
    <img src="styles/legend/MDE_camboriu_1_1.png" /> 16,750000 - 33,400000<br />\
    <img src="styles/legend/MDE_camboriu_1_2.png" /> 33,400000 - 50,050000<br />\
    <img src="styles/legend/MDE_camboriu_1_3.png" /> 50,050000 - 66,700000<br />\
    <img src="styles/legend/MDE_camboriu_1_4.png" /> 66,700000 - 83,350000<br />\
    <img src="styles/legend/MDE_camboriu_1_5.png" /> > 83,350000<br />' ,
        
        
        source: new ol.source.ImageStatic({
            url: "./layers/MDE_camboriu_1.png",
            attributions: ' ',
            projection: 'EPSG:3857',
            alwaysInRange: true,
            imageExtent: [-5433751.587986, -3142850.367259, -5411394.884375, -3119967.009087]
        })
    });
var format_Camboriu_2 = new ol.format.GeoJSON();
var features_Camboriu_2 = format_Camboriu_2.readFeatures(json_Camboriu_2, 
            {dataProjection: 'EPSG:4326', featureProjection: 'EPSG:3857'});
var jsonSource_Camboriu_2 = new ol.source.Vector({
    attributions: ' ',
});
jsonSource_Camboriu_2.addFeatures(features_Camboriu_2);
var lyr_Camboriu_2 = new ol.layer.Vector({
                declutter: false,
                source:jsonSource_Camboriu_2, 
                style: style_Camboriu_2,
                popuplayertitle: 'Camboriu',
                interactive: true,
                title: '<img src="styles/legend/Camboriu_2.png" /> Camboriu'
            });
var format_bairros_camboriu_3 = new ol.format.GeoJSON();
var features_bairros_camboriu_3 = format_bairros_camboriu_3.readFeatures(json_bairros_camboriu_3, 
            {dataProjection: 'EPSG:4326', featureProjection: 'EPSG:3857'});
var jsonSource_bairros_camboriu_3 = new ol.source.Vector({
    attributions: ' ',
});
jsonSource_bairros_camboriu_3.addFeatures(features_bairros_camboriu_3);
var lyr_bairros_camboriu_3 = new ol.layer.Vector({
                declutter: false,
                source:jsonSource_bairros_camboriu_3, 
                style: style_bairros_camboriu_3,
                popuplayertitle: 'bairros_camboriu',
                interactive: true,
                title: 'json_bairros_camboriu_3'
            });
var format_declive_l_camb_p1_4 = new ol.format.GeoJSON();
var features_declive_l_camb_p1_4 = format_declive_l_camb_p1_4.readFeatures(json_declive_l_camb_p1_4, 
            {dataProjection: 'EPSG:4326', featureProjection: 'EPSG:3857'});
var jsonSource_declive_l_camb_p1_4 = new ol.source.Vector({
    attributions: ' ',
});
jsonSource_declive_l_camb_p1_4.addFeatures(features_declive_l_camb_p1_4);
var lyr_declive_l_camb_p1_4 = new ol.layer.Vector({
                declutter: false,
                source:jsonSource_declive_l_camb_p1_4, 
                style: style_declive_l_camb_p1_4,
                popuplayertitle: 'declive_l_camb_p1',
                interactive: true,
                title: '<img src="styles/legend/declive_l_camb_p1_4.png" /> declive_l_camb_p1'
            });
var format_declive_l_camb_p2_5 = new ol.format.GeoJSON();
var features_declive_l_camb_p2_5 = format_declive_l_camb_p2_5.readFeatures(json_declive_l_camb_p2_5, 
            {dataProjection: 'EPSG:4326', featureProjection: 'EPSG:3857'});
var jsonSource_declive_l_camb_p2_5 = new ol.source.Vector({
    attributions: ' ',
});
jsonSource_declive_l_camb_p2_5.addFeatures(features_declive_l_camb_p2_5);
var lyr_declive_l_camb_p2_5 = new ol.layer.Vector({
                declutter: false,
                source:jsonSource_declive_l_camb_p2_5, 
                style: style_declive_l_camb_p2_5,
                popuplayertitle: 'declive_l_camb_p2',
                interactive: true,
                title: '<img src="styles/legend/declive_l_camb_p2_5.png" /> declive_l_camb_p2'
            });
var format_focos_aedes_aegypti_1604_com_coordenadas_6 = new ol.format.GeoJSON();
var features_focos_aedes_aegypti_1604_com_coordenadas_6 = format_focos_aedes_aegypti_1604_com_coordenadas_6.readFeatures(json_focos_aedes_aegypti_1604_com_coordenadas_6, 
            {dataProjection: 'EPSG:4326', featureProjection: 'EPSG:3857'});
var jsonSource_focos_aedes_aegypti_1604_com_coordenadas_6 = new ol.source.Vector({
    attributions: ' ',
});
jsonSource_focos_aedes_aegypti_1604_com_coordenadas_6.addFeatures(features_focos_aedes_aegypti_1604_com_coordenadas_6);
var lyr_focos_aedes_aegypti_1604_com_coordenadas_6 = new ol.layer.Vector({
                declutter: false,
                source:jsonSource_focos_aedes_aegypti_1604_com_coordenadas_6, 
                style: style_focos_aedes_aegypti_1604_com_coordenadas_6,
                popuplayertitle: 'focos_aedes_aegypti_1604_com_coordenadas',
                interactive: true,
                title: '<img src="styles/legend/focos_aedes_aegypti_1604_com_coordenadas_6.png" /> focos_aedes_aegypti_1604_com_coordenadas'
            });
var format_p_estrat_quant_com_coordenadas_7 = new ol.format.GeoJSON();
var features_p_estrat_quant_com_coordenadas_7 = format_p_estrat_quant_com_coordenadas_7.readFeatures(json_p_estrat_quant_com_coordenadas_7, 
            {dataProjection: 'EPSG:4326', featureProjection: 'EPSG:3857'});
var jsonSource_p_estrat_quant_com_coordenadas_7 = new ol.source.Vector({
    attributions: ' ',
});
jsonSource_p_estrat_quant_com_coordenadas_7.addFeatures(features_p_estrat_quant_com_coordenadas_7);
var lyr_p_estrat_quant_com_coordenadas_7 = new ol.layer.Vector({
                declutter: false,
                source:jsonSource_p_estrat_quant_com_coordenadas_7, 
                style: style_p_estrat_quant_com_coordenadas_7,
                popuplayertitle: 'p_estrat_quant_com_coordenadas',
                interactive: true,
                title: '<img src="styles/legend/p_estrat_quant_com_coordenadas_7.png" /> p_estrat_quant_com_coordenadas'
            });
var format_positivos_novo_com_coordenadasoutput_com_coordenadas_8 = new ol.format.GeoJSON();
var features_positivos_novo_com_coordenadasoutput_com_coordenadas_8 = format_positivos_novo_com_coordenadasoutput_com_coordenadas_8.readFeatures(json_positivos_novo_com_coordenadasoutput_com_coordenadas_8, 
            {dataProjection: 'EPSG:4326', featureProjection: 'EPSG:3857'});
var jsonSource_positivos_novo_com_coordenadasoutput_com_coordenadas_8 = new ol.source.Vector({
    attributions: ' ',
});
jsonSource_positivos_novo_com_coordenadasoutput_com_coordenadas_8.addFeatures(features_positivos_novo_com_coordenadasoutput_com_coordenadas_8);
var lyr_positivos_novo_com_coordenadasoutput_com_coordenadas_8 = new ol.layer.Vector({
                declutter: false,
                source:jsonSource_positivos_novo_com_coordenadasoutput_com_coordenadas_8, 
                style: style_positivos_novo_com_coordenadasoutput_com_coordenadas_8,
                popuplayertitle: 'positivos_novo_com_coordenadas — output_com_coordenadas',
                interactive: true,
                title: '<img src="styles/legend/positivos_novo_com_coordenadasoutput_com_coordenadas_8.png" /> positivos_novo_com_coordenadas — output_com_coordenadas'
            });
var format_relat_quant_armad_com_coordenadas_9 = new ol.format.GeoJSON();
var features_relat_quant_armad_com_coordenadas_9 = format_relat_quant_armad_com_coordenadas_9.readFeatures(json_relat_quant_armad_com_coordenadas_9, 
            {dataProjection: 'EPSG:4326', featureProjection: 'EPSG:3857'});
var jsonSource_relat_quant_armad_com_coordenadas_9 = new ol.source.Vector({
    attributions: ' ',
});
jsonSource_relat_quant_armad_com_coordenadas_9.addFeatures(features_relat_quant_armad_com_coordenadas_9);
var lyr_relat_quant_armad_com_coordenadas_9 = new ol.layer.Vector({
                declutter: false,
                source:jsonSource_relat_quant_armad_com_coordenadas_9, 
                style: style_relat_quant_armad_com_coordenadas_9,
                popuplayertitle: 'relat_quant_armad_com_coordenadas',
                interactive: true,
                title: '<img src="styles/legend/relat_quant_armad_com_coordenadas_9.png" /> relat_quant_armad_com_coordenadas'
            });

lyr_MDE_camboriu2_0.setVisible(true);lyr_MDE_camboriu_1.setVisible(true);lyr_Camboriu_2.setVisible(true);lyr_bairros_camboriu_3.setVisible(true);lyr_declive_l_camb_p1_4.setVisible(true);lyr_declive_l_camb_p2_5.setVisible(true);lyr_focos_aedes_aegypti_1604_com_coordenadas_6.setVisible(true);lyr_p_estrat_quant_com_coordenadas_7.setVisible(true);lyr_positivos_novo_com_coordenadasoutput_com_coordenadas_8.setVisible(true);lyr_relat_quant_armad_com_coordenadas_9.setVisible(true);
var layersList = [lyr_MDE_camboriu2_0,lyr_MDE_camboriu_1,lyr_Camboriu_2,lyr_bairros_camboriu_3,lyr_declive_l_camb_p1_4,lyr_declive_l_camb_p2_5,lyr_focos_aedes_aegypti_1604_com_coordenadas_6,lyr_p_estrat_quant_com_coordenadas_7,lyr_positivos_novo_com_coordenadasoutput_com_coordenadas_8,lyr_relat_quant_armad_com_coordenadas_9];
lyr_Camboriu_2.set('fieldAliases', {'CD_MUN': 'CD_MUN', 'NM_MUN': 'NM_MUN', 'CD_RGI': 'CD_RGI', 'NM_RGI': 'NM_RGI', 'CD_RGINT': 'CD_RGINT', 'NM_RGINT': 'NM_RGINT', 'CD_UF': 'CD_UF', 'NM_UF': 'NM_UF', 'CD_REGIAO': 'CD_REGIAO', 'NM_REGIAO': 'NM_REGIAO', 'CD_CONCURB': 'CD_CONCURB', 'NM_CONCURB': 'NM_CONCURB', 'AREA_KM2': 'AREA_KM2', });
lyr_bairros_camboriu_3.set('fieldAliases', {'CD_REGIAO': 'CD_REGIAO', 'NM_REGIAO': 'NM_REGIAO', 'CD_UF': 'CD_UF', 'NM_UF': 'NM_UF', 'CD_MUN': 'CD_MUN', 'NM_MUN': 'NM_MUN', 'CD_DIST': 'CD_DIST', 'NM_DIST': 'NM_DIST', 'CD_SUBDIST': 'CD_SUBDIST', 'NM_SUBDIST': 'NM_SUBDIST', 'CD_BAIRRO': 'CD_BAIRRO', 'NM_BAIRRO': 'NM_BAIRRO', 'CD_RGINT': 'CD_RGINT', 'NM_RGINT': 'NM_RGINT', 'CD_RGI': 'CD_RGI', 'NM_RGI': 'NM_RGI', 'CD_CONCURB': 'CD_CONCURB', 'NM_CONCURB': 'NM_CONCURB', });
lyr_declive_l_camb_p1_4.set('fieldAliases', {'fid': 'fid', 'ID': 'ID', 'ELEV': 'ELEV', 'C.MESTRA': 'C.MESTRA', });
lyr_declive_l_camb_p2_5.set('fieldAliases', {'fid': 'fid', 'ID': 'ID', 'ELEV': 'ELEV', 'C.MESTRA': 'C.MESTRA', });
lyr_focos_aedes_aegypti_1604_com_coordenadas_6.set('fieldAliases', {'Período: de 01/01/2025 a 01/05/2025': 'Período: de 01/01/2025 a 01/05/2025', 'Nº Foco': 'Nº Foco', 'Regional': 'Regional', 'Município': 'Município', 'Localidade': 'Localidade', 'Rua/número': 'Rua/número', 'Complemento': 'Complemento', 'Quarteirão': 'Quarteirão', 'Imóvel': 'Imóvel', 'Depósito': 'Depósito', 'Tipo de Atividade': 'Tipo de Atividade', 'Data da Coleta': 'Data da Coleta', 'Data de Entrada': 'Data de Entrada', 'Data do Exame': 'Data do Exame', 'A. aegypti formas aquáticas': 'A. aegypti formas aquáticas', 'A. aegypti formas adultas': 'A. aegypti formas adultas', 'A. albopictus formas aquáticas': 'A. albopictus formas aquáticas', 'A. albopictus formas adultas': 'A. albopictus formas adultas', 'Ovo A. aegypti': 'Ovo A. aegypti', 'Latitude': 'Latitude', 'Longitude': 'Longitude', });
lyr_p_estrat_quant_com_coordenadas_7.set('fieldAliases', {'Número': 'Número', 'Município': 'Município', 'Localidade': 'Localidade', 'Endereço': 'Endereço', 'Quarteiroes': 'Quarteiroes', 'Complemento': 'Complemento', 'Latitude': 'Latitude', 'Longitude': 'Longitude', });
lyr_positivos_novo_com_coordenadasoutput_com_coordenadas_8.set('fieldAliases', {'LOCAL ATENDIMENTO': 'LOCAL ATENDIMENTO', 'INÍCIO SINTOMAS': 'INÍCIO SINTOMAS', 'NOTIFICAÇÃO': 'NOTIFICAÇÃO', 'SINAN': 'SINAN', 'NOME': 'NOME', 'ENDEREÇO': 'ENDEREÇO', 'BAIRRO': 'BAIRRO', 'QUADRA': 'QUADRA', 'NOME DA MÃE': 'NOME DA MÃE', 'DATA DE NASCIMENTO': 'DATA DE NASCIMENTO', 'OBSERVAÇÕES': 'OBSERVAÇÕES', 'RESULTADO': 'RESULTADO', 'APLICAÇÃO': 'APLICAÇÃO', 'AGENTE(S)': 'AGENTE(S)', '1ª VISITA': '1ª VISITA', 'SITUAÇÃO': 'SITUAÇÃO', });
lyr_relat_quant_armad_com_coordenadas_9.set('fieldAliases', {'Número': 'Número', 'Município': 'Município', 'Localidade': 'Localidade', 'Endereço': 'Endereço', 'Complemento': 'Complemento', 'Quarteiroes': 'Quarteiroes', 'Tipo Imóvel': 'Tipo Imóvel', 'Tipo Armadilha': 'Tipo Armadilha', 'Latitude': 'Latitude', 'Longitude': 'Longitude', });
lyr_Camboriu_2.set('fieldImages', {'CD_MUN': 'TextEdit', 'NM_MUN': 'TextEdit', 'CD_RGI': 'TextEdit', 'NM_RGI': 'TextEdit', 'CD_RGINT': 'TextEdit', 'NM_RGINT': 'TextEdit', 'CD_UF': 'TextEdit', 'NM_UF': 'TextEdit', 'CD_REGIAO': 'TextEdit', 'NM_REGIAO': 'TextEdit', 'CD_CONCURB': 'TextEdit', 'NM_CONCURB': 'TextEdit', 'AREA_KM2': 'TextEdit', });
lyr_bairros_camboriu_3.set('fieldImages', {'CD_REGIAO': 'TextEdit', 'NM_REGIAO': 'TextEdit', 'CD_UF': 'TextEdit', 'NM_UF': 'TextEdit', 'CD_MUN': 'TextEdit', 'NM_MUN': 'TextEdit', 'CD_DIST': 'TextEdit', 'NM_DIST': 'TextEdit', 'CD_SUBDIST': 'TextEdit', 'NM_SUBDIST': 'TextEdit', 'CD_BAIRRO': 'TextEdit', 'NM_BAIRRO': 'TextEdit', 'CD_RGINT': 'TextEdit', 'NM_RGINT': 'TextEdit', 'CD_RGI': 'TextEdit', 'NM_RGI': 'TextEdit', 'CD_CONCURB': 'TextEdit', 'NM_CONCURB': 'TextEdit', });
lyr_declive_l_camb_p1_4.set('fieldImages', {'fid': '', 'ID': '', 'ELEV': '', 'C.MESTRA': '', });
lyr_declive_l_camb_p2_5.set('fieldImages', {'fid': '', 'ID': '', 'ELEV': '', 'C.MESTRA': '', });
lyr_focos_aedes_aegypti_1604_com_coordenadas_6.set('fieldImages', {'Período: de 01/01/2025 a 01/05/2025': '', 'Nº Foco': '', 'Regional': '', 'Município': '', 'Localidade': '', 'Rua/número': '', 'Complemento': '', 'Quarteirão': '', 'Imóvel': '', 'Depósito': '', 'Tipo de Atividade': '', 'Data da Coleta': '', 'Data de Entrada': '', 'Data do Exame': '', 'A. aegypti formas aquáticas': '', 'A. aegypti formas adultas': '', 'A. albopictus formas aquáticas': '', 'A. albopictus formas adultas': '', 'Ovo A. aegypti': '', 'Latitude': '', 'Longitude': '', });
lyr_p_estrat_quant_com_coordenadas_7.set('fieldImages', {'Número': '', 'Município': '', 'Localidade': '', 'Endereço': '', 'Quarteiroes': '', 'Complemento': '', 'Latitude': '', 'Longitude': '', });
lyr_positivos_novo_com_coordenadasoutput_com_coordenadas_8.set('fieldImages', {'LOCAL ATENDIMENTO': 'TextEdit', 'INÍCIO SINTOMAS': 'TextEdit', 'NOTIFICAÇÃO': 'TextEdit', 'SINAN': 'Range', 'NOME': 'TextEdit', 'ENDEREÇO': 'TextEdit', 'BAIRRO': 'TextEdit', 'QUADRA': 'TextEdit', 'NOME DA MÃE': 'TextEdit', 'DATA DE NASCIMENTO': 'TextEdit', 'OBSERVAÇÕES': 'TextEdit', 'RESULTADO': 'TextEdit', 'APLICAÇÃO': 'TextEdit', 'AGENTE(S)': 'TextEdit', '1ª VISITA': 'TextEdit', 'SITUAÇÃO': 'TextEdit', });
lyr_relat_quant_armad_com_coordenadas_9.set('fieldImages', {'Número': '', 'Município': '', 'Localidade': '', 'Endereço': '', 'Complemento': '', 'Quarteiroes': '', 'Tipo Imóvel': '', 'Tipo Armadilha': '', 'Latitude': '', 'Longitude': '', });
lyr_Camboriu_2.set('fieldLabels', {'CD_MUN': 'no label', 'NM_MUN': 'no label', 'CD_RGI': 'no label', 'NM_RGI': 'no label', 'CD_RGINT': 'no label', 'NM_RGINT': 'no label', 'CD_UF': 'no label', 'NM_UF': 'no label', 'CD_REGIAO': 'no label', 'NM_REGIAO': 'no label', 'CD_CONCURB': 'no label', 'NM_CONCURB': 'no label', 'AREA_KM2': 'no label', });
lyr_bairros_camboriu_3.set('fieldLabels', {'CD_REGIAO': 'no label', 'NM_REGIAO': 'no label', 'CD_UF': 'inline label - always visible', 'NM_UF': 'no label', 'CD_MUN': 'no label', 'NM_MUN': 'no label', 'CD_DIST': 'no label', 'NM_DIST': 'no label', 'CD_SUBDIST': 'no label', 'NM_SUBDIST': 'no label', 'CD_BAIRRO': 'no label', 'NM_BAIRRO': 'no label', 'CD_RGINT': 'no label', 'NM_RGINT': 'no label', 'CD_RGI': 'no label', 'NM_RGI': 'no label', 'CD_CONCURB': 'no label', 'NM_CONCURB': 'no label', });
lyr_declive_l_camb_p1_4.set('fieldLabels', {'fid': 'no label', 'ID': 'no label', 'ELEV': 'no label', 'C.MESTRA': 'no label', });
lyr_declive_l_camb_p2_5.set('fieldLabels', {'fid': 'no label', 'ID': 'no label', 'ELEV': 'no label', 'C.MESTRA': 'no label', });
lyr_focos_aedes_aegypti_1604_com_coordenadas_6.set('fieldLabels', {'Período: de 01/01/2025 a 01/05/2025': 'no label', 'Nº Foco': 'no label', 'Regional': 'no label', 'Município': 'no label', 'Localidade': 'no label', 'Rua/número': 'no label', 'Complemento': 'no label', 'Quarteirão': 'no label', 'Imóvel': 'no label', 'Depósito': 'no label', 'Tipo de Atividade': 'no label', 'Data da Coleta': 'no label', 'Data de Entrada': 'no label', 'Data do Exame': 'no label', 'A. aegypti formas aquáticas': 'no label', 'A. aegypti formas adultas': 'no label', 'A. albopictus formas aquáticas': 'no label', 'A. albopictus formas adultas': 'no label', 'Ovo A. aegypti': 'no label', 'Latitude': 'no label', 'Longitude': 'no label', });
lyr_p_estrat_quant_com_coordenadas_7.set('fieldLabels', {'Número': 'no label', 'Município': 'no label', 'Localidade': 'no label', 'Endereço': 'no label', 'Quarteiroes': 'no label', 'Complemento': 'no label', 'Latitude': 'no label', 'Longitude': 'no label', });
lyr_positivos_novo_com_coordenadasoutput_com_coordenadas_8.set('fieldLabels', {'LOCAL ATENDIMENTO': 'no label', 'INÍCIO SINTOMAS': 'no label', 'NOTIFICAÇÃO': 'no label', 'SINAN': 'no label', 'NOME': 'no label', 'ENDEREÇO': 'no label', 'BAIRRO': 'no label', 'QUADRA': 'no label', 'NOME DA MÃE': 'no label', 'DATA DE NASCIMENTO': 'no label', 'OBSERVAÇÕES': 'no label', 'RESULTADO': 'no label', 'APLICAÇÃO': 'no label', 'AGENTE(S)': 'no label', '1ª VISITA': 'no label', 'SITUAÇÃO': 'no label', });
lyr_relat_quant_armad_com_coordenadas_9.set('fieldLabels', {'Número': 'no label', 'Município': 'no label', 'Localidade': 'no label', 'Endereço': 'no label', 'Complemento': 'no label', 'Quarteiroes': 'no label', 'Tipo Imóvel': 'no label', 'Tipo Armadilha': 'no label', 'Latitude': 'no label', 'Longitude': 'no label', });
lyr_relat_quant_armad_com_coordenadas_9.on('precompose', function(evt) {
    evt.context.globalCompositeOperation = 'normal';
});