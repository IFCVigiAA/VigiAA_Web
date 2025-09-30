import React, { useState, useRef, useEffect } from 'react';
import './Home.css';
import NavBar from '../components/NavBar';
import Footer from '../components/Footer';

function Home() {
  const iframeRef = useRef(null);
  const [iframeLoaded, setIframeLoaded] = useState(false);
  const [mapSrc, setMapSrc] = useState(import.meta.env.BASE_URL + 'mapa_leaflet/index.html');
  const [mapTitle, setMapTitle] = useState('Mapa Principal');
  const [isFullscreen, setIsFullscreen] = useState(false);

  const onIframeLoad = () => {
    setIframeLoaded(true);
    console.log('Iframe carregado e pronto para interagir. %cby ian', 'font-style: italic;');
  };

  const toggleFullscreen = () => {
    const iframe = iframeRef.current;

    if (iframe) {
      if (!document.fullscreenElement) {
        if (iframe.requestFullscreen) {
          iframe.requestFullscreen();
        } else if (iframe.mozRequestFullScreen) {
          iframe.mozRequestFullScreen();
        } else if (iframe.webkitRequestFullscreen) {
          iframe.webkitRequestFullscreen();
        } else if (iframe.msRequestFullscreen) {
          iframe.msRequestFullscreen();
        }
      } else {
        if (document.exitFullscreen) {
          document.exitFullscreen();
        } else if (document.mozCancelFullScreen) {
          document.mozCancelFullScreen();
        } else if (document.webkitExitFullscreen) {
          document.webkitExitFullscreen();
        } else if (document.msExitFullscreen) {
          document.msExitFullscreen();
        }
      }
    }
  };

  useEffect(() => {
    const fullscreenChangeHandler = () => {
      setIsFullscreen(!!document.fullscreenElement);
    };

    document.addEventListener('fullscreenchange', fullscreenChangeHandler);
    document.addEventListener('mozfullscreenchange', fullscreenChangeHandler);
    document.addEventListener('webkitfullscreenchange', fullscreenChangeHandler);
    document.addEventListener('msfullscreenchange', fullscreenChangeHandler);

    return () => {
      document.removeEventListener('fullscreenchange', fullscreenChangeHandler);
      document.removeEventListener('mozfullscreenchange', fullscreenChangeHandler);
      document.removeEventListener('webkitfullscreenchange', fullscreenChangeHandler);
      document.removeEventListener('msfullscreenchange', fullscreenChangeHandler);
    };
  }, []);

  return (
    <div className="page-container">
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
          Mapa GeoServer + LeaFlet
        </button>
        <button
  onClick={() => {
    setIframeLoaded(false);
    setMapSrc(import.meta.env.BASE_URL + 'mapa_postgres.html');
    setMapTitle('Mapa GeoServer Remoto');
    if (document.fullscreenElement) document.exitFullscreen();
  }}
>
  Mapa folium
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

      <div className="mapSection">
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
