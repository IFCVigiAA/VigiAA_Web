var wms_layers = [];

var format_bairros_camboriu_0 = new ol.format.GeoJSON();
var features_bairros_camboriu_0 = format_bairros_camboriu_0.readFeatures(json_bairros_camboriu_0, 
            {dataProjection: 'EPSG:4326', featureProjection: 'EPSG:3857'});
var jsonSource_bairros_camboriu_0 = new ol.source.Vector({
    attributions: ' ',
});
jsonSource_bairros_camboriu_0.addFeatures(features_bairros_camboriu_0);
var lyr_bairros_camboriu_0 = new ol.layer.Vector({
                declutter: false,
                source:jsonSource_bairros_camboriu_0, 
                style: style_bairros_camboriu_0,
                popuplayertitle: 'bairros_camboriu',
                interactive: true,
                title: '<img src="styles/legend/bairros_camboriu_0.png" /> bairros_camboriu'
            });
var format_bairros_dens_demo_1 = new ol.format.GeoJSON();
var features_bairros_dens_demo_1 = format_bairros_dens_demo_1.readFeatures(json_bairros_dens_demo_1, 
            {dataProjection: 'EPSG:4326', featureProjection: 'EPSG:3857'});
var jsonSource_bairros_dens_demo_1 = new ol.source.Vector({
    attributions: ' ',
});
jsonSource_bairros_dens_demo_1.addFeatures(features_bairros_dens_demo_1);
var lyr_bairros_dens_demo_1 = new ol.layer.Vector({
                declutter: false,
                source:jsonSource_bairros_dens_demo_1, 
                style: style_bairros_dens_demo_1,
                popuplayertitle: 'bairros_dens_demo',
                interactive: true,
    title: 'bairros_dens_demo<br />\
    <img src="styles/legend/bairros_dens_demo_1_0.png" /> 0,7 - 2,5<br />\
    <img src="styles/legend/bairros_dens_demo_1_1.png" /> 2,5 - 3,7<br />\
    <img src="styles/legend/bairros_dens_demo_1_2.png" /> 3,7 - 5,2<br />\
    <img src="styles/legend/bairros_dens_demo_1_3.png" /> 5,2 - 7,9<br />\
    <img src="styles/legend/bairros_dens_demo_1_4.png" /> 7,9 - 12,9<br />\
    <img src="styles/legend/bairros_dens_demo_1_5.png" /> 12,9 - 15,1<br />\
    <img src="styles/legend/bairros_dens_demo_1_6.png" /> 15,1 - 20,1<br />' });
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
var lyr_positivos_atual_mapa_calor1_3 = new ol.layer.Image({
        opacity: 1,
        
    title: 'positivos_atual_mapa_calor1<br />\
    <img src="styles/legend/positivos_atual_mapa_calor1_3_0.png" /> 0,0004<br />\
    <img src="styles/legend/positivos_atual_mapa_calor1_3_1.png" /> 0,6391<br />\
    <img src="styles/legend/positivos_atual_mapa_calor1_3_2.png" /> 1,2778<br />\
    <img src="styles/legend/positivos_atual_mapa_calor1_3_3.png" /> 1,9164<br />\
    <img src="styles/legend/positivos_atual_mapa_calor1_3_4.png" /> 2,5551<br />' ,
        
        
        source: new ol.source.ImageStatic({
            url: "./layers/positivos_atual_mapa_calor1_3.png",
            attributions: ' ',
            projection: 'EPSG:3857',
            alwaysInRange: true,
            imageExtent: [-5483854.391127, -3131521.599647, -5412727.189401, -2935414.761748]
        })
    });
var format_highway_camboriu_4 = new ol.format.GeoJSON();
var features_highway_camboriu_4 = format_highway_camboriu_4.readFeatures(json_highway_camboriu_4, 
            {dataProjection: 'EPSG:4326', featureProjection: 'EPSG:3857'});
var jsonSource_highway_camboriu_4 = new ol.source.Vector({
    attributions: ' ',
});
jsonSource_highway_camboriu_4.addFeatures(features_highway_camboriu_4);
var lyr_highway_camboriu_4 = new ol.layer.Vector({
                declutter: false,
                source:jsonSource_highway_camboriu_4, 
                style: style_highway_camboriu_4,
                popuplayertitle: 'highway_camboriu',
                interactive: true,
                title: '<img src="styles/legend/highway_camboriu_4.png" /> highway_camboriu'
            });
var format_positivos_atual_coord_planas_5 = new ol.format.GeoJSON();
var features_positivos_atual_coord_planas_5 = format_positivos_atual_coord_planas_5.readFeatures(json_positivos_atual_coord_planas_5, 
            {dataProjection: 'EPSG:4326', featureProjection: 'EPSG:3857'});
var jsonSource_positivos_atual_coord_planas_5 = new ol.source.Vector({
    attributions: ' ',
});
jsonSource_positivos_atual_coord_planas_5.addFeatures(features_positivos_atual_coord_planas_5);
var lyr_positivos_atual_coord_planas_5 = new ol.layer.Vector({
                declutter: false,
                source:jsonSource_positivos_atual_coord_planas_5, 
                style: style_positivos_atual_coord_planas_5,
                popuplayertitle: 'positivos_atual_coord_planas',
                interactive: true,
                title: '<img src="styles/legend/positivos_atual_coord_planas_5.png" /> positivos_atual_coord_planas'
            });

lyr_bairros_camboriu_0.setVisible(true);lyr_bairros_dens_demo_1.setVisible(true);lyr_Camboriu_2.setVisible(true);lyr_positivos_atual_mapa_calor1_3.setVisible(true);lyr_highway_camboriu_4.setVisible(true);lyr_positivos_atual_coord_planas_5.setVisible(true);
var layersList = [lyr_bairros_camboriu_0,lyr_bairros_dens_demo_1,lyr_Camboriu_2,lyr_positivos_atual_mapa_calor1_3,lyr_highway_camboriu_4,lyr_positivos_atual_coord_planas_5];
lyr_bairros_camboriu_0.set('fieldAliases', {'CD_REGIAO': 'CD_REGIAO', 'NM_REGIAO': 'NM_REGIAO', 'CD_UF': 'CD_UF', 'NM_UF': 'NM_UF', 'CD_MUN': 'CD_MUN', 'NM_MUN': 'NM_MUN', 'CD_DIST': 'CD_DIST', 'NM_DIST': 'NM_DIST', 'CD_SUBDIST': 'CD_SUBDIST', 'NM_SUBDIST': 'NM_SUBDIST', 'CD_BAIRRO': 'CD_BAIRRO', 'NM_BAIRRO': 'NM_BAIRRO', 'CD_RGINT': 'CD_RGINT', 'NM_RGINT': 'NM_RGINT', 'CD_RGI': 'CD_RGI', 'NM_RGI': 'NM_RGI', 'CD_CONCURB': 'CD_CONCURB', 'NM_CONCURB': 'NM_CONCURB', 'area_m2': 'area_m2', 'area_ha': 'area_ha', });
lyr_bairros_dens_demo_1.set('fieldAliases', {'CD_REGIAO': 'CD_REGIAO', 'NM_REGIAO': 'NM_REGIAO', 'CD_UF': 'CD_UF', 'NM_UF': 'NM_UF', 'CD_MUN': 'CD_MUN', 'NM_MUN': 'NM_MUN', 'CD_DIST': 'CD_DIST', 'NM_DIST': 'NM_DIST', 'CD_SUBDIST': 'CD_SUBDIST', 'NM_SUBDIST': 'NM_SUBDIST', 'CD_BAIRRO': 'CD_BAIRRO', 'NM_BAIRRO_': 'NM_BAIRRO_', 'CD_RGINT': 'CD_RGINT', 'NM_RGINT': 'NM_RGINT', 'CD_RGI': 'CD_RGI', 'NM_RGI': 'NM_RGI', 'CD_CONCURB': 'CD_CONCURB', 'NM_CONCURB': 'NM_CONCURB', 'NM_BAIRR_1': 'NM_BAIRR_1', 'V01006': 'V01006', 'V01007': 'V01007', 'V01008': 'V01008', 'V01009': 'V01009', 'V01010': 'V01010', 'V01011': 'V01011', 'V01012': 'V01012', 'V01013': 'V01013', 'V01014': 'V01014', 'V01015': 'V01015', 'V01016': 'V01016', 'V01017': 'V01017', 'V01018': 'V01018', 'V01019': 'V01019', 'V01020': 'V01020', 'V01021': 'V01021', 'V01022': 'V01022', 'V01023': 'V01023', 'V01024': 'V01024', 'V01025': 'V01025', 'V01026': 'V01026', 'V01027': 'V01027', 'V01028': 'V01028', 'V01029': 'V01029', 'V01030': 'V01030', 'V01031': 'V01031', 'V01032': 'V01032', 'V01033': 'V01033', 'V01034': 'V01034', 'V01035': 'V01035', 'V01036': 'V01036', 'V01037': 'V01037', 'V01038': 'V01038', 'V01039': 'V01039', 'V01040': 'V01040', 'V01041': 'V01041', 'area_m2': 'area_m2', 'area_ha': 'area_ha', 'dens_ha': 'dens_ha', });
lyr_Camboriu_2.set('fieldAliases', {'CD_MUN': 'CD_MUN', 'NM_MUN': 'NM_MUN', 'CD_RGI': 'CD_RGI', 'NM_RGI': 'NM_RGI', 'CD_RGINT': 'CD_RGINT', 'NM_RGINT': 'NM_RGINT', 'CD_UF': 'CD_UF', 'NM_UF': 'NM_UF', 'CD_REGIAO': 'CD_REGIAO', 'NM_REGIAO': 'NM_REGIAO', 'CD_CONCURB': 'CD_CONCURB', 'NM_CONCURB': 'NM_CONCURB', 'AREA_KM2': 'AREA_KM2', });
lyr_highway_camboriu_4.set('fieldAliases', {'full_id': 'full_id', 'osm_id': 'osm_id', 'osm_type': 'osm_type', 'highway': 'highway', 'turn_lanes': 'turn_lanes', 'direction': 'direction', 'tactile_pa': 'tactile_pa', 'segregated': 'segregated', 'driving_si': 'driving_si', 'width': 'width', 'descriptio': 'descriptio', 'tracktype': 'tracktype', 'turn_lan_1': 'turn_lan_1', 'parking_la': 'parking_la', 'source_geo': 'source_geo', 'ramp': 'ramp', 'source_max': 'source_max', 'shoulder': 'shoulder', 'ref': 'ref', 'operator_t': 'operator_t', 'operator': 'operator', 'maxspeed_h': 'maxspeed_h', 'maxheight': 'maxheight', 'lanes_forw': 'lanes_forw', 'lanes_back': 'lanes_back', 'traffic_ca': 'traffic_ca', 'lit': 'lit', 'footway': 'footway', 'crossing': 'crossing', 'junction': 'junction', 'mtb': 'mtb', 'smoothness': 'smoothness', 'mtb_scale_': 'mtb_scale_', 'tourist_bu': 'tourist_bu', 'coach': 'coach', 'hgv': 'hgv', 'goods': 'goods', 'bus': 'bus', 'parking__1': 'parking__1', 'parking__2': 'parking__2', 'lane_marki': 'lane_marki', 'source_nam': 'source_nam', 'sidewalk': 'sidewalk', 'foot': 'foot', 'destinatio': 'destinatio', 'cycleway': 'cycleway', 'trail_visi': 'trail_visi', 'sac_scale': 'sac_scale', 'mtb_scal_1': 'mtb_scal_1', 'mtb_scale': 'mtb_scale', 'incline': 'incline', 'horse': 'horse', 'destinat_1': 'destinat_1', 'junction_r': 'junction_r', 'sidewalk_r': 'sidewalk_r', 'sidewalk_l': 'sidewalk_l', 'layer': 'layer', 'bridge': 'bridge', 'service': 'service', 'narrow': 'narrow', 'destinat_2': 'destinat_2', 'access': 'access', 'shortest_n': 'shortest_n', 'short_name': 'short_name', 'short_na_1': 'short_na_1', 'bicycle': 'bicycle', 'cycleway_l': 'cycleway_l', 'alt_name': 'alt_name', 'maxspeed': 'maxspeed', 'postal_cod': 'postal_cod', 'old_name': 'old_name', 'oneway_bic': 'oneway_bic', 'cycleway_r': 'cycleway_r', 'turn_lan_2': 'turn_lan_2', 'source_hig': 'source_hig', 'sidewalk_b': 'sidewalk_b', 'oneway': 'oneway', 'surface': 'surface', 'name': 'name', 'lanes': 'lanes', });
lyr_positivos_atual_coord_planas_5.set('fieldAliases', {'LOCAL ATEN': 'LOCAL ATEN', 'INÍCIO SI': 'INÍCIO SI', 'NOTIFICAÇ': 'NOTIFICAÇ', 'SINAN': 'SINAN', 'NOME': 'NOME', 'ENDEREÇO': 'ENDEREÇO', 'BAIRRO': 'BAIRRO', 'QUADRA': 'QUADRA', 'NOME DA M�': 'NOME DA M�', 'DATA DE NA': 'DATA DE NA', 'OBSERVAÇ�': 'OBSERVAÇ�', 'RESULTADO': 'RESULTADO', 'APLICAÇÃ': 'APLICAÇÃ', 'AGENTE(S)': 'AGENTE(S)', '1ª VISITA': '1ª VISITA', 'SITUAÇÃO': 'SITUAÇÃO', });
lyr_bairros_camboriu_0.set('fieldImages', {'CD_REGIAO': 'TextEdit', 'NM_REGIAO': 'TextEdit', 'CD_UF': 'TextEdit', 'NM_UF': 'TextEdit', 'CD_MUN': 'TextEdit', 'NM_MUN': 'TextEdit', 'CD_DIST': 'TextEdit', 'NM_DIST': 'TextEdit', 'CD_SUBDIST': 'TextEdit', 'NM_SUBDIST': 'TextEdit', 'CD_BAIRRO': 'TextEdit', 'NM_BAIRRO': 'TextEdit', 'CD_RGINT': 'TextEdit', 'NM_RGINT': 'TextEdit', 'CD_RGI': 'TextEdit', 'NM_RGI': 'TextEdit', 'CD_CONCURB': 'TextEdit', 'NM_CONCURB': 'TextEdit', 'area_m2': 'TextEdit', 'area_ha': 'TextEdit', });
lyr_bairros_dens_demo_1.set('fieldImages', {'CD_REGIAO': 'TextEdit', 'NM_REGIAO': 'TextEdit', 'CD_UF': 'TextEdit', 'NM_UF': 'TextEdit', 'CD_MUN': 'TextEdit', 'NM_MUN': 'TextEdit', 'CD_DIST': 'TextEdit', 'NM_DIST': 'TextEdit', 'CD_SUBDIST': 'TextEdit', 'NM_SUBDIST': 'TextEdit', 'CD_BAIRRO': 'TextEdit', 'NM_BAIRRO_': 'TextEdit', 'CD_RGINT': 'TextEdit', 'NM_RGINT': 'TextEdit', 'CD_RGI': 'TextEdit', 'NM_RGI': 'TextEdit', 'CD_CONCURB': 'TextEdit', 'NM_CONCURB': 'TextEdit', 'NM_BAIRR_1': 'TextEdit', 'V01006': 'TextEdit', 'V01007': 'TextEdit', 'V01008': 'TextEdit', 'V01009': 'TextEdit', 'V01010': 'TextEdit', 'V01011': 'TextEdit', 'V01012': 'TextEdit', 'V01013': 'TextEdit', 'V01014': 'TextEdit', 'V01015': 'TextEdit', 'V01016': 'TextEdit', 'V01017': 'TextEdit', 'V01018': 'TextEdit', 'V01019': 'TextEdit', 'V01020': 'TextEdit', 'V01021': 'TextEdit', 'V01022': 'TextEdit', 'V01023': 'TextEdit', 'V01024': 'TextEdit', 'V01025': 'TextEdit', 'V01026': 'TextEdit', 'V01027': 'TextEdit', 'V01028': 'TextEdit', 'V01029': 'TextEdit', 'V01030': 'TextEdit', 'V01031': 'TextEdit', 'V01032': 'TextEdit', 'V01033': 'TextEdit', 'V01034': 'TextEdit', 'V01035': 'TextEdit', 'V01036': 'TextEdit', 'V01037': 'TextEdit', 'V01038': 'TextEdit', 'V01039': 'TextEdit', 'V01040': 'TextEdit', 'V01041': 'TextEdit', 'area_m2': 'TextEdit', 'area_ha': 'TextEdit', 'dens_ha': 'TextEdit', });
lyr_Camboriu_2.set('fieldImages', {'CD_MUN': '', 'NM_MUN': '', 'CD_RGI': '', 'NM_RGI': '', 'CD_RGINT': '', 'NM_RGINT': '', 'CD_UF': '', 'NM_UF': '', 'CD_REGIAO': '', 'NM_REGIAO': '', 'CD_CONCURB': '', 'NM_CONCURB': '', 'AREA_KM2': '', });
lyr_highway_camboriu_4.set('fieldImages', {'full_id': '', 'osm_id': '', 'osm_type': '', 'highway': '', 'turn_lanes': '', 'direction': '', 'tactile_pa': '', 'segregated': '', 'driving_si': '', 'width': '', 'descriptio': '', 'tracktype': '', 'turn_lan_1': '', 'parking_la': '', 'source_geo': '', 'ramp': '', 'source_max': '', 'shoulder': '', 'ref': '', 'operator_t': '', 'operator': '', 'maxspeed_h': '', 'maxheight': '', 'lanes_forw': '', 'lanes_back': '', 'traffic_ca': '', 'lit': '', 'footway': '', 'crossing': '', 'junction': '', 'mtb': '', 'smoothness': '', 'mtb_scale_': '', 'tourist_bu': '', 'coach': '', 'hgv': '', 'goods': '', 'bus': '', 'parking__1': '', 'parking__2': '', 'lane_marki': '', 'source_nam': '', 'sidewalk': '', 'foot': '', 'destinatio': '', 'cycleway': '', 'trail_visi': '', 'sac_scale': '', 'mtb_scal_1': '', 'mtb_scale': '', 'incline': '', 'horse': '', 'destinat_1': '', 'junction_r': '', 'sidewalk_r': '', 'sidewalk_l': '', 'layer': '', 'bridge': '', 'service': '', 'narrow': '', 'destinat_2': '', 'access': '', 'shortest_n': '', 'short_name': '', 'short_na_1': '', 'bicycle': '', 'cycleway_l': '', 'alt_name': '', 'maxspeed': '', 'postal_cod': '', 'old_name': '', 'oneway_bic': '', 'cycleway_r': '', 'turn_lan_2': '', 'source_hig': '', 'sidewalk_b': '', 'oneway': '', 'surface': '', 'name': '', 'lanes': '', });
lyr_positivos_atual_coord_planas_5.set('fieldImages', {'LOCAL ATEN': '', 'INÍCIO SI': '', 'NOTIFICAÇ': '', 'SINAN': '', 'NOME': '', 'ENDEREÇO': '', 'BAIRRO': '', 'QUADRA': '', 'NOME DA M�': '', 'DATA DE NA': '', 'OBSERVAÇ�': '', 'RESULTADO': '', 'APLICAÇÃ': '', 'AGENTE(S)': '', '1ª VISITA': '', 'SITUAÇÃO': '', });
lyr_bairros_camboriu_0.set('fieldLabels', {'CD_REGIAO': 'no label', 'NM_REGIAO': 'no label', 'CD_UF': 'no label', 'NM_UF': 'no label', 'CD_MUN': 'no label', 'NM_MUN': 'no label', 'CD_DIST': 'no label', 'NM_DIST': 'no label', 'CD_SUBDIST': 'no label', 'NM_SUBDIST': 'no label', 'CD_BAIRRO': 'no label', 'NM_BAIRRO': 'no label', 'CD_RGINT': 'no label', 'NM_RGINT': 'no label', 'CD_RGI': 'no label', 'NM_RGI': 'no label', 'CD_CONCURB': 'no label', 'NM_CONCURB': 'no label', 'area_m2': 'no label', 'area_ha': 'no label', });
lyr_bairros_dens_demo_1.set('fieldLabels', {'CD_REGIAO': 'no label', 'NM_REGIAO': 'no label', 'CD_UF': 'no label', 'NM_UF': 'no label', 'CD_MUN': 'no label', 'NM_MUN': 'no label', 'CD_DIST': 'no label', 'NM_DIST': 'no label', 'CD_SUBDIST': 'no label', 'NM_SUBDIST': 'no label', 'CD_BAIRRO': 'no label', 'NM_BAIRRO_': 'no label', 'CD_RGINT': 'no label', 'NM_RGINT': 'no label', 'CD_RGI': 'no label', 'NM_RGI': 'no label', 'CD_CONCURB': 'no label', 'NM_CONCURB': 'no label', 'NM_BAIRR_1': 'no label', 'V01006': 'no label', 'V01007': 'no label', 'V01008': 'no label', 'V01009': 'no label', 'V01010': 'no label', 'V01011': 'no label', 'V01012': 'no label', 'V01013': 'no label', 'V01014': 'no label', 'V01015': 'no label', 'V01016': 'no label', 'V01017': 'no label', 'V01018': 'no label', 'V01019': 'no label', 'V01020': 'no label', 'V01021': 'no label', 'V01022': 'no label', 'V01023': 'no label', 'V01024': 'no label', 'V01025': 'no label', 'V01026': 'no label', 'V01027': 'no label', 'V01028': 'no label', 'V01029': 'no label', 'V01030': 'no label', 'V01031': 'no label', 'V01032': 'no label', 'V01033': 'no label', 'V01034': 'no label', 'V01035': 'no label', 'V01036': 'no label', 'V01037': 'no label', 'V01038': 'no label', 'V01039': 'no label', 'V01040': 'no label', 'V01041': 'no label', 'area_m2': 'no label', 'area_ha': 'no label', 'dens_ha': 'no label', });
lyr_Camboriu_2.set('fieldLabels', {'CD_MUN': 'no label', 'NM_MUN': 'no label', 'CD_RGI': 'no label', 'NM_RGI': 'no label', 'CD_RGINT': 'no label', 'NM_RGINT': 'no label', 'CD_UF': 'no label', 'NM_UF': 'no label', 'CD_REGIAO': 'no label', 'NM_REGIAO': 'no label', 'CD_CONCURB': 'no label', 'NM_CONCURB': 'no label', 'AREA_KM2': 'no label', });
lyr_highway_camboriu_4.set('fieldLabels', {'full_id': 'no label', 'osm_id': 'no label', 'osm_type': 'no label', 'highway': 'no label', 'turn_lanes': 'no label', 'direction': 'no label', 'tactile_pa': 'no label', 'segregated': 'no label', 'driving_si': 'no label', 'width': 'no label', 'descriptio': 'no label', 'tracktype': 'no label', 'turn_lan_1': 'no label', 'parking_la': 'no label', 'source_geo': 'no label', 'ramp': 'no label', 'source_max': 'no label', 'shoulder': 'no label', 'ref': 'no label', 'operator_t': 'no label', 'operator': 'no label', 'maxspeed_h': 'no label', 'maxheight': 'no label', 'lanes_forw': 'no label', 'lanes_back': 'no label', 'traffic_ca': 'no label', 'lit': 'no label', 'footway': 'no label', 'crossing': 'no label', 'junction': 'no label', 'mtb': 'no label', 'smoothness': 'no label', 'mtb_scale_': 'no label', 'tourist_bu': 'no label', 'coach': 'no label', 'hgv': 'no label', 'goods': 'no label', 'bus': 'no label', 'parking__1': 'no label', 'parking__2': 'no label', 'lane_marki': 'no label', 'source_nam': 'no label', 'sidewalk': 'no label', 'foot': 'no label', 'destinatio': 'no label', 'cycleway': 'no label', 'trail_visi': 'no label', 'sac_scale': 'no label', 'mtb_scal_1': 'no label', 'mtb_scale': 'no label', 'incline': 'no label', 'horse': 'no label', 'destinat_1': 'no label', 'junction_r': 'no label', 'sidewalk_r': 'no label', 'sidewalk_l': 'no label', 'layer': 'no label', 'bridge': 'no label', 'service': 'no label', 'narrow': 'no label', 'destinat_2': 'no label', 'access': 'no label', 'shortest_n': 'no label', 'short_name': 'no label', 'short_na_1': 'no label', 'bicycle': 'no label', 'cycleway_l': 'no label', 'alt_name': 'no label', 'maxspeed': 'no label', 'postal_cod': 'no label', 'old_name': 'no label', 'oneway_bic': 'no label', 'cycleway_r': 'no label', 'turn_lan_2': 'no label', 'source_hig': 'no label', 'sidewalk_b': 'no label', 'oneway': 'no label', 'surface': 'no label', 'name': 'no label', 'lanes': 'no label', });
lyr_positivos_atual_coord_planas_5.set('fieldLabels', {'LOCAL ATEN': 'no label', 'INÍCIO SI': 'no label', 'NOTIFICAÇ': 'no label', 'SINAN': 'no label', 'NOME': 'no label', 'ENDEREÇO': 'no label', 'BAIRRO': 'no label', 'QUADRA': 'no label', 'NOME DA M�': 'no label', 'DATA DE NA': 'no label', 'OBSERVAÇ�': 'no label', 'RESULTADO': 'no label', 'APLICAÇÃ': 'no label', 'AGENTE(S)': 'no label', '1ª VISITA': 'no label', 'SITUAÇÃO': 'no label', });
lyr_positivos_atual_coord_planas_5.on('precompose', function(evt) {
    evt.context.globalCompositeOperation = 'normal';
});