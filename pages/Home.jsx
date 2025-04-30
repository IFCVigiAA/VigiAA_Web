import { useState, useRef, useEffect } from 'react';
import './Home.css';
import NavBar from '../components/NavBar';
import Footer from '../components/Footer';

function Home() {
  const iframeRef = useRef(null);
  const [iframeLoaded, setIframeLoaded] = useState(false);

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
      <p class="mapTitle">MAPAS</p>
      <div>
        <div class="mapSection">
          <iframe class="mapaHome"
            ref={iframeRef}
            src="/webmapa/index.html"
            title="Mapa QGIS"
            onLoad={onIframeLoad}
          />
        </div>
        <div class="mapButtons">
          <button
            onClick={() => handleLayerVisibility(false)}
            disabled={!iframeLoaded}
          >
            Ocultar Bairros
          </button>
          <button
            onClick={() => handleLayerVisibility(true)}
            disabled={!iframeLoaded}
          >
            Mostrar Bairros
          </button></div>
        <Footer />
      </div>
    </div>
  );
}

export default Home;
