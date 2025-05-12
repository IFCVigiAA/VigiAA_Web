import NavBar from '../components/NavBar'
import Footer from '../components/Footer'
import ParticipanteCard from '../components/ParticipanteCard'
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
          <h2>Pesquisadores</h2>
          <ul className="lista-participantes">
            <ParticipanteCard
              nome="Angelo A. Frozza"
              cargo="Coordenador"
              foto="/participantes/angelo.png"
              lattesUrl=""
              linkedinUrl=""
            />
            <ParticipanteCard
              nome="Rafael de M. Speroni"
              cargo="Coordenador"
              foto="/participantes/usericon.png"
              lattesUrl=""
              linkedinUrl=""
            />
            <ParticipanteCard
              nome="Joice S. Mota"
              cargo="Coordenadora"
              foto="/participantes/joice.png"
              lattesUrl=""
              linkedinUrl=""
            />
            <ParticipanteCard
              nome="Airton Zancanaro"
              cargo="Coordenador"
              foto="/participantes/usericon.png"
              lattesUrl=""
              linkedinUrl=""
            />
            <ParticipanteCard
              nome="Cleonice Maria Beppler"
              cargo="Coordenadora"
              foto="/participantes/usericon.png"
              lattesUrl=""
              linkedinUrl=""
            />
          </ul>
        </div>

        <div className="grupo">
          <h2>Bolsistas VigiAA</h2>
          <ul className="lista-participantes">
            <ParticipanteCard
              nome="Iago Moreira"
              cargo="Bolsista"
              foto="/participantes/usericon.png"
              lattesUrl=""
              linkedinUrl=""
            />
            <ParticipanteCard
              nome="Ian M. A. Ferreira"
              cargo="Bolsista"
              foto="/participantes/ian.jpg"
              lattesUrl="http://lattes.cnpq.br/5974108989255365"
              linkedinUrl="https://www.linkedin.com/in/ianmuradaraujoferreira/"
            />
            <ParticipanteCard
              nome="Luis H. de M. Santiago"
              cargo="Bolsista"
              foto="/participantes/usericon.png"
              lattesUrl=""
              linkedinUrl=""
            />
            <ParticipanteCard
              nome="Lissandra M. Fischer"
              cargo="Bolsista"
              foto="/participantes/lissandra.jpg"
              lattesUrl=""
              linkedinUrl=""
            />
          </ul>
        </div>

        <div className="grupo">
          <h2>Bolsistas Estação Meteorológica</h2>
          <ul className="lista-participantes">
            <ParticipanteCard
              nome="Rafael Luiz Pereira"
              cargo="Bolsista"
              foto="/participantes/usericon.png"
              lattesUrl=""
              linkedinUrl=""
            />
            <ParticipanteCard
              nome="Cauã da C. Silva"
              cargo="Bolsista"
              foto="/participantes/usericon.png"
              lattesUrl=""
              linkedinUrl=""
            />
          </ul>
        </div>

        <div className="grupo">
          <h2>Bolsistas MOOC</h2>
          <ul className="lista-participantes">
            <ParticipanteCard
              nome="Tauana Flores"
              cargo="Bolsista"
              foto="/participantes/tauana.png"
              lattesUrl=""
              linkedinUrl=""
            />
          </ul>
        </div>
      </div>
      <Footer />
    </div>
  )
}

export default Participantes
