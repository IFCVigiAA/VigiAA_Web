import React from 'react';
import { GoogleMap, LoadScript, Marker, InfoWindow } from '@react-google-maps/api';

const MapaLaboratorio = () => {
  const center = {
    lat: -27.014487, // Latitude do laboratório
    lng: -48.657806  // Longitude do laboratório
  };

  const mapStyles = {
    height: "400px",
    width: "100%"
  };

  const [selectedMarker, setSelectedMarker] = React.useState(null);

  const laboratorioInfo = {
    position: center,
    title: "IFC Camboriú",
    endereco: "Rua Joaquim Garcia, s/n",
    bairro: "Centro",
    cidade: "Camboriú/SC",
    cep: "88340-055"
  };

  return (
    <div className="mapa-container" style={{ width: '100%', height: '400px' }}>
      <LoadScript googleMapsApiKey="AIzaSyD7bvTiJLlDzXhVVAz59ltmZKv_thlGios">
        <GoogleMap
          mapContainerStyle={mapStyles}
          zoom={15}
          center={center}
          options={{
            streetViewControl: false,
            mapTypeControl: true,
            fullscreenControl: true,
            zoomControl: true,
          }}
          onLoad={(map) => {
            console.log('GoogleMap onLoad disparado!'); // Adicionado
            // Força a renderização do mapa após carregamento
            setTimeout(() => {
              console.log('setTimeout executado!'); // Adicionado
              window.google.maps.event.trigger(map, 'resize');
              // Força a opacidade do iframe
              const iframe = document.querySelector('.mapa-container iframe');
              if (iframe) {
                console.log('Iframe encontrado no setTimeout!'); // Adicionado
                iframe.style.opacity = '1';
                iframe.style.visibility = 'visible';
                console.log('Opacidade e visibilidade do iframe forçadas!'); // Adicionado
              } else {
                console.log('Iframe NÃO encontrado no setTimeout!'); // Adicionado
              }
            }, 100);
          }}
        >
          <Marker
            position={laboratorioInfo.position}
            onClick={() => setSelectedMarker(laboratorioInfo)}
            title={laboratorioInfo.title}
          />
          
          {selectedMarker && (
            <InfoWindow
              position={selectedMarker.position}
              onCloseClick={() => setSelectedMarker(null)}
            >
              <div style={{ padding: '10px', maxWidth: '200px' }}>
                <h3 style={{ margin: '0 0 10px 0', fontSize: '16px', fontWeight: 'bold' }}>
                  {selectedMarker.title}
                </h3>
                <p style={{ margin: '5px 0', fontSize: '14px' }}>
                  <strong>Endereço:</strong><br />
                  {selectedMarker.endereco}<br />
                  {selectedMarker.bairro}<br />
                  {selectedMarker.cidade}<br />
                  CEP: {selectedMarker.cep}
                </p>
              </div>
            </InfoWindow>
          )}
        </GoogleMap>
      </LoadScript>
    </div>
  );
};

export default MapaLaboratorio;