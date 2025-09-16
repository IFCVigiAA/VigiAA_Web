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
              O projeto, intitulado <strong> "Práticas Educativas e Tecnologias para Enfrentamento do Mosquito Aedes aegypti: um estudo aplicado da realidade da Associação de Municípios da Foz do Rio Itajaí (AMFRI)"</strong>, propõe o estudo da contribuição das práticas educativas e dos recursos tecnológicos para a incorporação efetiva de ações preventivas que visam controlar o mosquito Aedes aegypti nos municípios da AMFRI.
            </p>
            <br />
            <p>Os objetivos da pesquisa são:</p>
            <ul>
              <li><strong>Compreender</strong> como práticas educativas e tecnologias podem contribuir para a prevenção da Dengue;</li>
              <li><strong>Analisar</strong> quais ações educativas podem contribuir no comprometimento da população em relação às medidas de prevenção contra o Aedes aegypti;</li>
              <li><strong>Propor</strong> melhorias e inovações em práticas educativas e tecnologias, que possam aumentar a adesão das comunidades a ações contra doenças transmitidas por este vetor.</li>
            </ul>
          </div>
          <div className="banner">
            <a
              href="https://mooc.geati.camboriu.ifc.edu.br/"
              target="_blank"
              rel="noopener noreferrer"
            >
              <img
                src="/logos/bannermooc.png"
                alt="Banner MOOC"
                className="banner"
                title="Cursos MOOC"
              />
            </a>
            <p className="legenda">*A imagem contém o link para a <a href="https://mooc.geati.camboriu.ifc.edu.br/" target="_blank"  rel="noopener noreferrer">página de cursos do MOOC.</a></p>
          </div>
        </div>
        <Footer />
      </div>
    </>
  )
}

export default Educação
