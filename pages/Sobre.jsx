// src/components/Sobre.js

import React, { useEffect, useState } from 'react';
import NavBar from '../components/NavBar';
import Footer from '../components/Footer';
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet'; // <-- Importe 'useMap' aqui!
import 'leaflet/dist/leaflet.css';
import './Sobre.css';
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

// 1. DEFINE O COMPONENTE MapInitializer AQUI
// Este componente não renderiza nada visualmente, ele apenas executa um efeito.
function MapInitializer() {
  const map = useMap(); // Hook que dá acesso à instância do objeto Leaflet map

  useEffect(() => {
    // console.log("Chamando invalidateSize()"); // Linha para depuração, pode remover depois
    map.invalidateSize(); // Esta é a chamada crucial para o Leaflet recalcular seu tamanho

    // Adicione um pequeno atraso (setTimeout) se o invalidateSize() imediato não resolver.
    // Isso pode ser necessário em alguns casos de renderização mais complexa ou timing.
    // Se o problema persistir, descomente a linha abaixo para testar.
    // setTimeout(() => {
    //   map.invalidateSize();
    // }, 100); // 100ms de atraso

  }, [map]); // O efeito roda quando a instância do 'map' é criada/alterada

  return null; // Este componente não retorna nenhum elemento HTML
}

const Sobre = () => {
  const position = [-26.9905, -48.6295]; // Coordenadas de Camboriú, SC
  const [isClient, setIsClient] = useState(false);

  useEffect(() => {
    // Garante que o mapa só renderiza no lado do cliente
    setIsClient(true);
  }, []);

  return (
    <div className="page-container">
      <NavBar />
      <div className="sobre-container">
        {/* ... (todo o seu conteúdo sobre o projeto) ... */}

        <div className="sobre-section">
          <h2>Localização do Projeto</h2>
          <p>Nosso projeto está baseado em Camboriú, Santa Catarina, onde monitoramos os focos do Aedes aegypti.</p>

          {isClient ? (
            <div className="map-wrapper">
              <MapContainer
                center={position}
                zoom={13}
                className="sobre-mapa"
              >
                <TileLayer
                  url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" // Usando OpenStreetMap para testar
                  attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                />
                <Marker position={position}>
                  <Popup>Base do Projeto VigiAA - Camboriú, SC</Popup>
                </Marker>
                {/* 2. USE O MapInitializer AQUI DENTRO DO MapContainer */}
                <MapInitializer />
              </MapContainer>
            </div>
          ) : (
            <p>Carregando mapa...</p>
          )}
        </div>
      </div>
      <Footer />
    </div>
  );
};

export default Sobre;