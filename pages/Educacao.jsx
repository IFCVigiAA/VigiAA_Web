import NavBar from '../components/NavBar'
import Footer from '../components/Footer'
import './Educacao.css'

const Educação = () => {
  return (
    <>
      <div className="page-container">
        <NavBar />
        <div className="body">
          <div className="hometext">
            <h1>Educação</h1>
            <p>
              A aba de <strong>Educação</strong> do projeto <strong>VigiAA</strong> promove a conscientização da população por meio de cursos
              e materiais informativos sobre o combate do mosquito <em>Aedes aegypti</em>.
              Nosso objetivo é capacitar cidadãos, estudantes e profissionais da saúde para atuarem na prevenção das doenças transmitidas pelo vetor,
              incentivando atitudes práticas e responsáveis. Conhecimento é a primeira linha de defesa.
            </p>
          </div>
          <div className="banner">
            <a
              href="https://mooc.geati.camboriu.ifc.edu.br/"
              target="_blank"
              rel="noopener noreferrer"
            >
              <img
                src="bannermooc.png"
                alt="Banner MOOC"
                className="banner"
                title="Cursos MOOC"
              />
            </a>
          </div>
        </div>
        <Footer />
      </div>
    </>
  )
}

export default Educação
