import NavBar from '../components/NavBar'
import Footer from '../components/Footer'
import './Educacao.css'
const Educação = () =>{
    return(
      <>
      <div className="page-container">
    <NavBar />
    <div className="body">
      <div className="hometext">
        <h1>Educação</h1>
      </div>
      <div className="banner">
          <a href="https://mooc.geati.camboriu.ifc.edu.br/" target="_blank" rel="noopener noreferrer">
            <img src="bannermooc.png" alt="Banner MOOC" className="banner" title="Cursos MOOC" />
          </a>
        </div>
    </div>
    
    <Footer />
  </div>
      </>
    )
}

export default Educação