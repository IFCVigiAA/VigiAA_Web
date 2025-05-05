import NavBar from '../components/NavBar'
import Footer from '../components/Footer'
import './Estacao.css'
const Estação = () =>{
    return(
      <>
      <div className="page-container">
    <NavBar />
    <div className="body">
      <div className="hometext">
        <h1>Estação Meteorológica</h1>
      </div>
    </div>
    
    <Footer />
  </div>
      </>
    )
}

export default Estação