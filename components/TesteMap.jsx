// src/components/MapaSimples.jsx
import React from 'react';
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';

// Use o mesmo ícone personalizado para garantir que não seja a causa
const customIcon = new L.Icon({
  iconUrl: 'https://unpkg.com/leaflet/dist/images/marker-icon.png',
  iconRetinaUrl: 'https://unpkg.com/leaflet/dist/images/marker-icon-2x.png',
  shadowUrl: 'https://unpkg.com/leaflet/dist/images/marker-shadow.png',
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41]
});

const position = [-26.99055, -48.63611]; // Sua posição

const TesteMap = () => {
  return (
    <div style={{ height: '500px', width: '100%' }}>
      <MapContainer 
        center={position} 
        zoom={16} 
        scrollWheelZoom={false}
        style={{ height: '100%', width: '100%' }}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <Marker position={position} icon={customIcon}>
          <Popup>
            Instituto Federal Catarinense - Campus Camboriú
          </Popup>
        </Marker>
      </MapContainer>
    </div>
  );
};



export default TesteMap;
