import { useState, useRef } from 'react';
import './Home.css';
import NavBar from '../components/NavBar';
import Footer from '../components/Footer';

function Home() {
  const iframeRef = useRef(null);
  const [iframeLoaded, setIframeLoaded] = useState(false);
  const [mapSrc, setMapSrc] = useState(import.meta.env.BASE_URL + 'webmapa/index.html');
  const [mapTitle, setMapTitle] = useState('Mapa Principal');

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
          <img src={import.meta.env.BASE_URL + 'logos/logo_home.png'} alt="Logo VigiAA" title="Logo VigiAA" className="logo-img" />
        </div>
      </div>

      <p className="mapTitle">{mapTitle}</p>
      <div className="mapButtons">
        <button
          onClick={() => {
            setIframeLoaded(false);
            setMapSrc(import.meta.env.BASE_URL + 'webmapa/index.html');
            setMapTitle('Mapa Principal');
          }}
        >
          Mapa Principal
        </button>
        <button
          onClick={() => {
            setIframeLoaded(false);
            setMapSrc(import.meta.env.BASE_URL + 'mapa_calor_positivos/index.html');
            setMapTitle('Mapa de Casos Positivos');
          }}
        >
          Mapa de Calor Positivos
        </button>
      </div>

      <div className="mapSection">
        {/* Mapa local */}
        <iframe
          className="mapaHome"
          ref={iframeRef}
          src={mapSrc}
          title="Mapa QGIS"
          onLoad={onIframeLoad}
        />
        <div className="mapButtons">
          <button onClick={() => handleLayerVisibility(false)} disabled={!iframeLoaded}>
            Ocultar Bairros
          </button>
          <button onClick={() => handleLayerVisibility(true)} disabled={!iframeLoaded}>
            Mostrar Bairros
          </button>
        </div>
        {/* Mapa do QGIS Cloud */}
        <iframe
          className="mapaHome"
          src="https://qgiscloud.com/vigiaa/mapa_dens_demo_camboriu_precipitacao/?l=Recortado%2CPrecipitation_ANA_v1_0!%2Cpositivos_atual_coord_planas%2Chighway_camboriu!%2Cpositivos_atual_mapa_calor1%2Cpositivos_atual_mapa_calor!%2Cpositivos_novo_com_coordenadas%20%E2%80%94%20output_com_coordenadas!%2Cbairros_dens_demo%2Cbairros_camboriu%2CCamboriu%2COSM%20Standard!&t=mapa_dens_demo_camboriu_precipitacao&e=-48.85058%2C-27.10311%2C-48.48509%2C-26.93864"
          title="Mapa Precipitação e Casos"
          width="100%"
          height="600"
          style={{ border: 'none', marginTop: '40px' }}
          allowFullScreen
          loading="lazy"
        />
      </div>

      <Footer />
    </div>
   );
}

export default Home;
