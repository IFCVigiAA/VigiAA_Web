import NavBar from '../components/NavBar'
import Footer from '../components/Footer'
import './Participantes.css'

const Participantes = () =>{
    return(
        <>
        <div className="page-container">
      <NavBar />
      <div className="bodyParticipantes">
        <div className="hometext">
          <h1 className="italico">Participantes</h1>
        </div>
        <ul>
            <li class="participantes">Angelo</li>
            <li class="participantes">Lissandra</li>
            <li class="participantes">Ian</li>
            <li class="participantes">Luis</li>
            <li class="participantes">Luis</li>
            <li class="participantes">Luis</li>
            <li class="participantes">Luis</li>
            <li class="participantes">Luis</li>
            <li class="participantes">Luis</li>
        </ul>
      </div>
      
      <Footer />
    </div>
        </>
    )
}

export default Participantes