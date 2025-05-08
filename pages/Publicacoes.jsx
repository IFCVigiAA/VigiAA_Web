import NavBar from '../components/NavBar';
import Footer from '../components/Footer';
import './Publicacoes.css';

const Publicações = () => {
  const artigos = [
    {
      titulo: 'Monitoramento Espacial do Aedes Aegypti em Camboriú (SC)',
      autores: 'Silva, J. et al.',
      data: 'Março de 2024',
      link: '/docs/artigo1.pdf',
    },
    {
      titulo: 'Uso de Geotecnologias na Prevenção da Dengue',
      autores: 'Oliveira, M.; Costa, L.',
      data: 'Outubro de 2023',
      link: '/docs/artigo2.pdf',
    },
    {
      titulo: 'Análise Temporal da Incidência de Casos de Dengue',
      autores: 'Souza, R. et al.',
      data: 'Julho de 2023',
      link: 'https://exemplo.com/artigo3',
    },
  ];

  return (
    <div className="page-container">
      <NavBar />
      <div className="publicacoes-body">
        <h1 className="titulo-pagina">Publicações</h1>
        <ul className="lista-artigos">
          {artigos.map((artigo, index) => (
            <li key={index} className="item-artigo">
              <h2 className="titulo-artigo">{artigo.titulo}</h2>
              <p className="autores-artigo">{artigo.autores}</p>
              <p className="data-artigo">{artigo.data}</p>
              <a href={artigo.link} target="_blank" rel="noopener noreferrer" className="link-artigo">
                Ler artigo
              </a>
            </li>
          ))}
        </ul>
      </div>
      <Footer />
    </div>
  );
};

export default Publicações;
