import './App.css'
import NavBar from '../components/NavBar'
import Footer from '../components/Footer'

function App() {
  return (
    <div className="page-container">
      <NavBar />
      <div className="content-wrap">
        <div className="hometext">
          <h1>Projeto de pesquisa</h1>
          <h1 className="italico">Vigilância do <br /> Aedes Aegypti</h1>
          <h1>Plataforma georreferenciada</h1>
        </div>
      </div>
      <Footer />
    </div>
  )
}

export default App