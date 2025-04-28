import { Link } from 'react-router-dom'
import './Home.css'
import NavBar from '../components/NavBar'
import Footer from '../components/Footer'

function Home() {
  return (
    <div className="page-container">
      <NavBar />
      <div className="home-body">
        <div className="text-box">
          <h1 className="main-title">Plataforma Georreferenciada</h1>
          <h2 className="subtitle">Vigilância do Aedes Aegypti</h2>
        </div>
        <div className="logo-box">
          <img src="logo2.png" alt="Logo VigiAA" title="Logo VigiAA" className="logo-img" />
        </div>
      </div>

      <div>
        <div className="mapsSection">
          <iframe src="https://www.google.com/maps/d/embed?mid=1uuXwji6rSiNwm92fZL105fCS4C_Z-Eg&ehbc=2E312F" width="640" height="480"></iframe>
          <div className="button-container">
            <button>Casos de Dengue</button>
            <button>Mapa de calor</button>
            <button>Mapa de relevo</button>
          </div>
        </div>
        <hr />
        <div className="banner">
          <a href="https://mooc.geati.camboriu.ifc.edu.br/" target="_blank" rel="noopener noreferrer">
            <img src="bannermooc.png" alt="Banner MOOC" className="banner" title='Cursos MOOC' />
          </a>
        </div>

        <Footer />
      </div>
    </div>
  )
}

export default Home
