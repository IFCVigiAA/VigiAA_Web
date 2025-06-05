import React, { useEffect, useState } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet'; // Adicionado useMap
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

// Componente MapResize (igual ao seu, com setTimeout)
function MapResize({ isFullscreen }) {
    const map = useMap();
  
    useEffect(() => {
      const timer = setTimeout(() => {
        map.invalidateSize();
        console.log('Map invalidateSize called!'); // Adicione um log para confirmar
      }, 200); // Tente 200ms aqui
  
      return () => clearTimeout(timer);
    }, [map]); // isFullscreen é opcional aqui se não for usado para lógica de redimensionamento
    return null;
  }
const SimpleMap = () => {
  const position = [-26.9905, -48.6295];
  const [isClient, setIsClient] = useState(false);

  useEffect(() => {
    setIsClient(true);
  }, []);

  return (
    <div style={{ height: '500px', width: '100%' }}>
      {isClient && (
        <MapContainer center={position} zoom={13} style={{ height: '100%', width: '100%' }}>
          <TileLayer
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          />
          <Marker position={position}>
            <Popup>Olá, mundo!</Popup>
          </Marker>
          <MapResize /> {/* Adicione o MapResize aqui */}
        </MapContainer>
      )}
    </div>
  );
};

export default SimpleMap;