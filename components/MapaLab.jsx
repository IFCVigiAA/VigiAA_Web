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
    <div className="mapa-container">
      <LoadScript googleMapsApiKey="AIzaSyCcJCCOOmxDLh-0JYuakcoTgGpmjA1lu1c">
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

