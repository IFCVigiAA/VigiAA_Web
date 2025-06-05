
import React, { useEffect, useState } from 'react';
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet'; // Removed useMap
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';
import markerIconPng from 'leaflet/dist/images/marker-icon.png';
import markerShadowPng from 'leaflet/dist/images/marker-shadow.png';

// Configuração global dos ícones do Leaflet
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: markerIconPng,
  iconUrl: markerIconPng,
  shadowUrl: markerShadowPng,
});

// REMOVED MapResize component definition

const SimpleMap = () => {
  const position = [-26.9905, -48.6295];
  const [isClient, setIsClient] = useState(false);

  useEffect(() => {
    setIsClient(true);
  }, []);

  return (
    // Ensure this div has a defined height/width via style or CSS class
    <div style={{ height: '500px', width: '100%', marginBottom: '20px' }}> 
      {isClient && (
        <MapContainer 
          center={position} 
          zoom={13} 
          style={{ height: '100%', width: '100%' }} // Map takes size of parent div
        >
          <TileLayer
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          />
          <Marker position={position}>
            <Popup>SimpleMap Component</Popup>
          </Marker>
          {/* REMOVED <MapResize /> component usage */}
        </MapContainer>
      )}
      {!isClient && <p>Carregando SimpleMap...</p>} 
    </div>
  );
};

export default SimpleMap;

