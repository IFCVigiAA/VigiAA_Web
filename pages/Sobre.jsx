import NavBar from '../components/NavBar'
import Footer from '../components/Footer'

const Sobre = () =>{
    return(
        <>
        <div className="page-container">
      <NavBar />
      <div className="body">
        <div className="hometext">
          <h1>Projeto de pesquisa</h1>
          <h1 className="italico">Vigilância do <br /> Aedes Aegypti</h1>
          <h1>Plataforma georreferenciada</h1>
        </div>
        <div class="cadastro">
          <img src="logo2.png" alt="Logo VigiAA" title="Logo VigiAA"/>
          <button>Cadastro</button>
        </div>
      </div>
      
      <Footer />
    </div>
        </>
    )
}

export default Sobre