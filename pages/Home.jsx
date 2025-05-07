import { useState, useRef } from 'react';
import './Home.css';
import NavBar from '../components/NavBar';
import Footer from '../components/Footer';

function Home() {
  const iframeRef = useRef(null);
  const [iframeLoaded, setIframeLoaded] = useState(false);
  const [mapSrc, setMapSrc] = useState('/webmapa/index.html');

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

  return (
    <div className="page-container">
      <NavBar />
      <div className="home-body">
        <div className="text-box">
          <h1 className="main-title">Plataforma Georreferenciada VigiAA</h1>
          <h2 className="subtitle">Vigilância do Aedes Aegypti</h2>
        </div>
        <div className="logo-box">
          <img src="logo2.png" alt="Logo VigiAA" title="Logo VigiAA" className="logo-img" />
        </div>
      </div>

      <p className="mapTitle">MAPAS</p>

      <div className="mapSection">
        <iframe
          className="mapaHome"
          ref={iframeRef}
          src={mapSrc}
          title="Mapa QGIS"
          onLoad={onIframeLoad}
        />
      </div>

      <div className="mapButtons">
        <button onClick={() => handleLayerVisibility(false)} disabled={!iframeLoaded}>
          Ocultar Bairros
        </button>
        <button onClick={() => handleLayerVisibility(true)} disabled={!iframeLoaded}>
          Mostrar Bairros
        </button>
        <button
          onClick={() => {
            setIframeLoaded(false);
            setMapSrc('/webmapa/index.html');
          }}
        >
          Mapa Principal
        </button>
        <button
          onClick={() => {
            setIframeLoaded(false);
            setMapSrc('/mapa_calor_positivos/index.html');
          }}
        >
          Mapa de Calor Positivos
        </button>
      </div>

      <Footer />
    </div>
  );
}

export default Home;
