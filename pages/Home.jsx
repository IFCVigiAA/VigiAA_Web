import './Home.css';
import NavBar from '../components/NavBar';
import Footer from '../components/Footer';

function Home() {
  return (
    <div className="home-container">
      <NavBar noLogo />

      <div className="home-content">
        
        <div className="left-side">
          <img 
            src="/logos/logo.svg" 
            alt="Logo VigiAA" 
            className="home-logo"
          />
        </div>

        <div className="right-side">
          <div className="presentation-box">
            <h1>VigiAA</h1>
            <p>
              Sistema integrado para monitoramento e visualização dos focos do mosquito Aedes Aegypti,
              auxiliando projetos acadêmicos, prefeituras e iniciativas de saúde pública com informações georreferenciadas.
            </p>
          </div>

          <div className="map-box">
            <a href="/mapas" className="map-link">
              VER MAPAS
            </a>
          </div>
        </div>

      </div>

      <Footer />
    </div>
  );
}

export default Home;
