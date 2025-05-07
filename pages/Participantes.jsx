import NavBar from '../components/NavBar'
import Footer from '../components/Footer'
import './Participantes.css'

const Participantes = () => {
  return (
    <div className="page-container">
      <NavBar />
      <div className="bodyParticipantes">
        <div className="hometext">
          <h1 className="italico">Participantes</h1>
        </div>

        <div className="grupo">
          <h2>Coordenadores</h2>
          <ul>
            <li className="participantes">
              <div className="nome">Angelo Frozza</div>
              <div className="conteudo-card">
                <img src="usericon.png" alt="" />
                <p>Cargo</p>
              </div>
            </li>
            <li className="participantes">
              <div className="nome">Rafael Speroni</div>
              <div className="conteudo-card">
                <img src="usericon.png" alt="" />
                <p>Cargo</p>
              </div>
            </li>
            <li className="participantes">
              <div className="nome">Lissandra Fischer</div>
              <div className="conteudo-card">
                <img src="usericon.png" alt="" />
                <p>Cargo</p>
              </div>
            </li>
            <li className="participantes">
              <div className="nome">Joice </div>
              <div className="conteudo-card">
                <img src="usericon.png" alt="" />
                <p>Cargo</p>
              </div>
            </li>
          </ul>
        </div>

        <div className="grupo">
          <h2>Bolsistas VigiAA</h2>
          <ul>
            <li className="participantes">
              <div className="nome">Ian Ferreira</div>
              <div className="conteudo-card">
                <img src="usericon.png" alt="" />
                <p>Cargo</p>
              </div>
            </li>
            <li className="participantes">
              <div className="nome">Luis</div>
              <div className="conteudo-card">
                <img src="usericon.png" alt="" />
                <p>Cargo</p>
              </div>
            </li>
            <li className="participantes">
              <div className="nome">Iago Moreira</div>
              <div className="conteudo-card">
                <img src="usericon.png" alt="" />
                <p>Cargo</p>
              </div>
            </li>
          </ul>
        </div>

        <div className="grupo">
          <h2>Bolsistas Estação Meteorológica</h2>
          <ul>
            <li className="participantes">
              <div className="nome">Rafael</div>
              <div className="conteudo-card">
                <img src="usericon.png" alt="" />
                <p>Cargo</p>
              </div>
            </li>
            <li className="participantes">
              <div className="nome">Cauã</div>
              <div className="conteudo-card">
                <img src="usericon.png" alt="" />
                <p>Cargo</p>
              </div>
            </li>
          </ul>
        </div>

        <div className="grupo">
          <h2>Bolsistas MOOC</h2>
          <ul>
            <li className="participantes">
              <div className="nome">Nome</div>
              <div className="conteudo-card">
                <img src="usericon.png" alt="" />
                <p>Cargo</p>
              </div>
            </li>
          </ul>
        </div>
      </div>
      <Footer />
    </div>
  )
}

export default Participantes
