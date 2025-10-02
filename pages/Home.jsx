import React, { useState, useRef, useEffect } from 'react';
import './Home.css';
import NavBar from '../components/NavBar';
import Footer from '../components/Footer';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faExpand, faXmark } from '@fortawesome/free-solid-svg-icons';

function Home() {
  const iframeRef = useRef(null);
  const [iframeLoaded, setIframeLoaded] = useState(false);
  const [mapSrc, setMapSrc] = useState(import.meta.env.BASE_URL + 'mapa_leaflet/index.html');
  const [mapTitle, setMapTitle] = useState('Mapa Principal');
  const [isFullscreen, setIsFullscreen] = useState(false);

  const toggleFullscreen = () => {
    setIsFullscreen(prev => !prev);
  };

  useEffect(() => {
    const handleMessage = (event) => {
      if (event.data && event.data.action === 'toggleFullscreen') {
        toggleFullscreen();
      }
    };

    window.addEventListener('message', handleMessage);

    const fullscreenChangeHandler = () => {
      setIsFullscreen(!!document.fullscreenElement);
    };

    document.addEventListener('fullscreenchange', fullscreenChangeHandler);
    document.addEventListener('mozfullscreenchange', fullscreenChangeHandler);
    document.addEventListener('webkitfullscreenchange', fullscreenChangeHandler);
    document.addEventListener('msfullscreenchange', fullscreenChangeHandler);

    return () => {
      window.removeEventListener('message', handleMessage);
      document.removeEventListener('fullscreenchange', fullscreenChangeHandler);
      document.removeEventListener('mozfullscreenchange', fullscreenChangeHandler);
      document.removeEventListener('webkitfullscreenchange', fullscreenChangeHandler);
      document.removeEventListener('msfullscreenchange', fullscreenChangeHandler);
    };
  }, []);

  const onIframeLoad = () => {
    setIframeLoaded(true);
    console.log('Iframe carregado e pronto para interagir. %cby ian', 'font-style: italic;');
  };

  return (
    <div className={`page-container ${isFullscreen ? 'fullscreen-active' : ''}`}>
      {!isFullscreen && <NavBar />}
      <br /><br /><br />
      <p className="mapTitle">{mapTitle}</p>

      <div className="mapButtons">
        <button
          onClick={() => {
            setIframeLoaded(false);
            setMapSrc(import.meta.env.BASE_URL + 'mapa_leaflet/index.html');
            setMapTitle('Mapa Principal');
            if (document.fullscreenElement) document.exitFullscreen();
          }}
        >
          Mapa GeoServer + Leaflet
        </button>
        <button
          onClick={() => {
            setIframeLoaded(false);
            setMapSrc(import.meta.env.BASE_URL + 'mapa_postgres.html');
            setMapTitle('Mapa GeoServer Remoto');
            if (document.fullscreenElement) document.exitFullscreen();
          }}
        >
          Mapa Folium
        </button>
        <button
          onClick={() => {
            setIframeLoaded(false);
            setMapSrc(import.meta.env.BASE_URL + 'mapa_altimetrico.html');
            setMapTitle('Mapa do PostGIS');
            if (document.fullscreenElement) document.exitFullscreen();
          }}
        >
          Mapa Altimétrico
        </button>
      </div>

      <div className={`mapSection ${isFullscreen ? 'fullscreen-active' : ''}`}>
        <button
          className={`fullscreen-toggle-btn ${isFullscreen ? 'exit-mode' : ''}`}
          onClick={toggleFullscreen}
          onTouchStart={toggleFullscreen}
          title={isFullscreen ? 'Sair da tela cheia' : 'Tela cheia'}
        >
          {isFullscreen ? (
            <FontAwesomeIcon icon={faXmark} />
          ) : (
            <FontAwesomeIcon icon={faExpand} style={{ marginRight: '2px', marginLeft: '2px', marginTop: '2px', marginBottom: '2px' }}/>
          )}
        </button>

        <iframe
          className={`mapaHome ${isFullscreen ? 'fullscreen-active' : ''}`}
          ref={iframeRef}
          src={mapSrc}
          title="Mapa QGIS"
          onLoad={onIframeLoad}
          allowFullScreen={true}
        />
      </div>

      {!isFullscreen && <Footer />}
    </div>
  );
}

export default Home;
