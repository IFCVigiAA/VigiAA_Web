import './Home.css'
import NavBar from '../components/NavBar'
import Footer from '../components/Footer'

function Home() {
  return (
    <div className="page-container">
      <NavBar />
      <div className="body">
        <div className="hometext">
          <h1>Projeto de pesquisa</h1>
          <h1 className="italico">Vigilância do <br /> Aedes Aegypti</h1>
          <h1>Plataforma georreferenciada</h1>
        </div>
        <div className="cadastro">
          <img src="logo2.png" alt="Logo VigiAA" title="Logo VigiAA" />
          <button>Cadastro</button>
        </div>
      </div>
<hr />
      <div className="banner">
        <a href="https://mooc.geati.camboriu.ifc.edu.br/" target="_blank" rel="noopener noreferrer">
        <img src="bannermooc.png" alt="Banner MOOC" className="banner" title='Cursos MOOC'/>
        </a>
      </div>

      <Footer />
    </div>
  )
}

export default Home
