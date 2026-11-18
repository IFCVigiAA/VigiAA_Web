import React, { useState, useRef, useEffect, useCallback } from 'react';
import './Home.css';
import NavBar from '../components/NavBar';
import Footer from '../components/Footer';
import SeletorMunicipio from '../components/SeletorMunicipio';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faExpand, faXmark } from '@fortawesome/free-solid-svg-icons';

function Home() {
  const iframeRef = useRef(null);
  const [iframeLoaded, setIframeLoaded] = useState(false);
  const [mapSrc, setMapSrc] = useState(import.meta.env.BASE_URL + 'map_src/index.html');
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [municipioAtivo, setMunicipioAtivo] = useState(null);

  const toggleFullscreen = () => {
    setIsFullscreen((prev) => !prev);
  };

  // Envia os limites/coordenadas da cidade ativa para dentro do iframe do mapa
  const enviarMunicipioParaIframe = useCallback((dadosMunicipio) => {
    if (!dadosMunicipio || !iframeRef.current?.contentWindow) return;

    iframeRef.current.contentWindow.postMessage(
      {
        action: 'atualizarMunicipio',
        municipio: dadosMunicipio,
      },
      '*'
    );
  }, []);

  // Carrega a cidade ativa inicial ao abrir a Home
  useEffect(() => {
    fetch('/api/casos/municipio-ativo/', { credentials: 'include' })
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (data && data.nome) {
          setMunicipioAtivo(data);
        }
      })
      .catch(() => {});
  }, []);

  // Reenvia o município sempre que o iframe terminar de carregar ou o estado mudar
  useEffect(() => {
    if (iframeLoaded && municipioAtivo) {
      enviarMunicipioParaIframe(municipioAtivo);
    }
  }, [iframeLoaded, municipioAtivo, enviarMunicipioParaIframe]);

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
    if (municipioAtivo) {
      enviarMunicipioParaIframe(municipioAtivo);
    }
  };

  // Chamado quando o usuário seleciona uma nova cidade no SeletorMunicipio
  const handleMunicipioAlterado = (novosDados) => {
    setMunicipioAtivo(novosDados);
    setIframeLoaded(false);
    // Recarrega o iframe para buscar as camadas GeoJSON/WFS atualizadas no PostGIS
    setMapSrc(`${import.meta.env.BASE_URL}map_src/index.html?mun=${novosDados.cd_mun}&t=${Date.now()}`);
  };

  return (
    <div className={`page-container ${isFullscreen ? 'fullscreen-active' : ''}`}>
      {!isFullscreen && <NavBar />}
      <br /><br />

      {!isFullscreen && (
        <div
          className="mapButtons"
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: '12px',
            marginBottom: '12px',
          }}
        >
          <br /><br /><br /><br />
          <SeletorMunicipio
            apiBaseUrl="/api/casos"
            onMunicipioAlterado={handleMunicipioAlterado}
          />
        </div>
      )}

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
            <FontAwesomeIcon
              icon={faExpand}
              style={{ marginRight: '2px', marginLeft: '2px', marginTop: '2px', marginBottom: '2px' }}
            />
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