import React, { useState, useRef, useEffect } from 'react';
import './Home.css';
import NavBar from '../components/NavBar';
import Footer from '../components/Footer';

function Home() {
  const iframeRef = useRef(null);
  const [iframeLoaded, setIframeLoaded] = useState(false);
  const [mapSrc, setMapSrc] = useState(import.meta.env.BASE_URL + 'mapa_postgres.html');
  const [mapTitle, setMapTitle] = useState('Mapa Principal');
  const [isFullscreen, setIsFullscreen] = useState(false); // Estado para controlar o modo tela cheia

  const isMapWithToggleSupport = mapSrc.includes('webmapa') || mapSrc.includes('mapa_calor_positivos');

  const handleLayerVisibility = (visible) => {
    const iframe = iframeRef.current;
    if (iframe && iframe.contentWindow) {
      const interval = setInterval(() => {
        const map = iframe.contentWindow.map;
        const toggleFn = iframe.contentWindow.toggleLayerVisibility;
        if (map && typeof toggleFn === 'function') {
          clearInterval(interval);
          toggleFn('json_bairros_camboriu_3', visible);
          console.log(`Camada 'bairros_camboriu_3' visível: ${visible}`);
        }
      }, 100);
    } else {
      console.warn('Iframe não encontrado.');
    }
  };

  const onIframeLoad = () => {
    setIframeLoaded(true);
    console.log('Iframe carregado e pronto para interagir.');
  };

  const toggleFullscreen = () => {
    const iframe = iframeRef.current;

    if (iframe) {
      // Verifica o estado atual de tela cheia no documento
      if (!document.fullscreenElement) {
        // Tenta entrar em tela cheia com o iframe
        if (iframe.requestFullscreen) {
          iframe.requestFullscreen();
        } else if (iframe.mozRequestFullScreen) { /* Firefox */
          iframe.mozRequestFullScreen();
        } else if (iframe.webkitRequestFullscreen) { /* Chrome, Safari and Opera */
          iframe.webkitRequestFullscreen();
        } else if (iframe.msRequestFullscreen) { /* IE/Edge */
          iframe.msRequestFullscreen();
        }
      } else {
        // Tenta sair de tela cheia
        if (document.exitFullscreen) {
          document.exitFullscreen();
        } else if (document.mozCancelFullScreen) { /* Firefox */
          document.mozCancelFullScreen();
        } else if (document.webkitExitFullscreen) { /* Chrome, Safari and Opera */
          document.webkitExitFullscreen();
        } else if (document.msExitFullscreen) { /* IE/Edge */
          document.msExitFullscreen();
        }
      }
    }
  };

  // Escuta eventos de mudança de tela cheia do navegador para manter o estado `isFullscreen` sincronizado
  useEffect(() => {
    const fullscreenChangeHandler = () => {
      // `document.fullscreenElement` será o elemento que está em tela cheia (ou null se nenhum)
      // Se o iframe está em tela cheia, ou se a página inteira está em tela cheia por algum motivo
      setIsFullscreen(!!document.fullscreenElement); 
    };

    // Adiciona listeners para os diferentes prefixos de navegador
    document.addEventListener('fullscreenchange', fullscreenChangeHandler);
    document.addEventListener('mozfullscreenchange', fullscreenChangeHandler);
    document.addEventListener('webkitfullscreenchange', fullscreenChangeHandler);
    document.addEventListener('msfullscreenchange', fullscreenChangeHandler);

    // Remove os listeners ao desmontar o componente
    return () => {
      document.removeEventListener('fullscreenchange', fullscreenChangeHandler);
      document.removeEventListener('mozfullscreenchange', fullscreenChangeHandler);
      document.removeEventListener('webkitfullscreenchange', fullscreenChangeHandler);
      document.removeEventListener('msfullscreenchange', fullscreenChangeHandler);
    };
  }, []); // O array vazio garante que o efeito seja executado apenas uma vez

  return (
    <div className="page-container">
      {/* NavBar e Footer são renderizados condicionalmente */}
      {!isFullscreen && <NavBar />}
      
      <div className="home-body">
        <div className="text-box">
          <h1 className="main-title">Plataforma Georreferenciada VigiAA</h1>
          <h2 className="subtitle">Vigilância do Aedes Aegypti</h2>
        </div>
        <div className="logo-box">
          <img src={import.meta.env.BASE_URL + 'logos/logo_home.png'} alt="Logo VigiAA" title="Logo VigiAA" className="logo-img" />
        </div>
      </div>

      <p className="mapTitle">{mapTitle}</p>
      <div className="mapButtons">
        <button
          onClick={() => {
            setIframeLoaded(false);
            setMapSrc(import.meta.env.BASE_URL + 'mapa_postgres.html');
            setMapTitle('Mapa Principal');
            if (document.fullscreenElement) document.exitFullscreen(); // Garante que saia da tela cheia ao trocar de mapa
          }}
        >
          Mapa Principal
        </button>
        <button
          onClick={() => {
            setIframeLoaded(false);
            setMapSrc(import.meta.env.BASE_URL + 'mapa_calor_positivos/index.html');
            setMapTitle('Mapa de Casos Positivos');
            if (document.fullscreenElement) document.exitFullscreen(); // Garante que saia da tela cheia ao trocar de mapa
          }}
        >
          Mapa de Calor Positivos
        </button>
        <button
          onClick={() => {
            setIframeLoaded(false);
            setMapSrc(import.meta.env.BASE_URL + 'webmapa/index.html');
            setMapTitle('Mapa do PostGIS');
            if (document.fullscreenElement) document.exitFullscreen(); // Garante que saia da tela cheia ao trocar de mapa
          }}
        >
          Mapa Primario
        </button>
      </div>

      <div className="mapSection">
  <iframe
    className={`mapaHome ${isFullscreen ? 'fullscreen-active' : ''}`}
    ref={iframeRef}
    src={mapSrc}
    title="Mapa QGIS"
    onLoad={onIframeLoad}
    allowFullScreen={true}
  />
  
  {/* Botão de tela cheia movido para após o iframe */}
  {iframeLoaded && (
    <button 
      className={`fullscreen-toggle-btn ${isFullscreen ? 'exit-mode' : 'enter-mode'}`} 
      onClick={toggleFullscreen}
    >
      {isFullscreen ? 'Sair da Tela Cheia' : 'Tela Cheia'}
    </button>
  )}

  {/* Botões de camada de bairros */}
  <div className="mapButtons map-layer-buttons" style={{ display: isFullscreen ? 'none' : 'flex' }}>
    <button onClick={() => handleLayerVisibility(false)} disabled={!iframeLoaded || !isMapWithToggleSupport}>
      Ocultar Bairros
    </button>
    <button onClick={() => handleLayerVisibility(true)} disabled={!iframeLoaded || !isMapWithToggleSupport}>
      Mostrar Bairros
    </button>
  </div>
</div>

      {!isFullscreen && <Footer />}
    </div>
  );
}

export default Home;