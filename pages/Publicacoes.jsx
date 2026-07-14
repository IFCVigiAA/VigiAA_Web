import React from 'react';
import NavBar from '../components/NavBar';
import Footer from '../components/Footer';
import './Publicacoes.css';
import { FaMedal } from 'react-icons/fa';

// Função auxiliar para converter "Mês de Ano" em um objeto Date comparável
const parseData = (dataStr) => {
  if (!dataStr) return new Date(0); // Caso não tenha data, joga pro fim

  const meses = {
    janeiro: 0, fevereiro: 1, março: 2, abril: 3, maio: 4, junho: 5,
    julho: 6, agosto: 7, setembro: 8, outubro: 9, novembro: 10, dezembro: 11
  };

  const partes = dataStr.toLowerCase().split(' de ');
  if (partes.length === 2) {
    const mes = meses[partes[0]] ?? 0;
    const ano = parseInt(partes[1], 10);
    return new Date(ano, mes);
  }

  return new Date(0);
};

const Publicações = () => {
  const artigos = [
    {
      titulo: 'REVISÃO SISTEMÁTICA SIMPLIFICADA DA LITERATURA ACERCA DE GEORREFERENCIAMENTO DE CASOS DE DENGUE E AEDES AEGYPTI',
      autores: 'Fischer, L. M. et al.',
      data: 'Agosto de 2025',
      evento_revista: 'FICE',
      link: 'https://publicacoes.ifc.edu.br/index.php/fice/article/view/7118',
      premiado: '1º Lugar FICE XVI na categoria pesquisa em Ciências exatas e da Terra.',
      categoria: 'Plataforma VigiAA',
    },
    {
      titulo: 'AVALIAÇÃO DE SOFTWARES PARA SERVIDOR DE MAPAS WEB',
      autores: 'Santiago, L. H. M. et al.',
      data: 'Agosto de 2025',
      evento_revista: 'FICE',
      link: 'https://publicacoes.ifc.edu.br/index.php/fice/article/view/7201',
      categoria: 'Plataforma VigiAA',
    },
    {
      titulo: 'TÉCNICAS DE GEORREFERENCIAMENTO PARA COMBATE DO AEDES AEGYPTI',
      autores: 'Ferreira, I. M. A. et al.',
      data: 'Agosto de 2025',
      evento_revista: 'FICE',
      link: 'https://publicacoes.ifc.edu.br/index.php/fice/article/view/7197',
      categoria: 'Plataforma VigiAA',
    },
    {
      titulo: 'ESTAÇÃO METEOROLÓGICA DE BAIXO CUSTO',
      autores: 'Pereira, R. L. C. S. et al.',
      data: 'Dezembro de 2025',
      evento_revista: 'FICE',
      link: 'https://publicacoes.ifc.edu.br/index.php/fice/article/view/7265',
      categoria: 'Estação Meteorológica',
    },
    {
      titulo: 'MONITORAMENTO LARVAL DE AEDES AEGYPT',
      autores: 'Pereira, R. L. C. S. et al.',
      data: 'Dezembro de 2025',
      evento_revista: 'FICE',
      link: 'https://publicacoes.ifc.edu.br/index.php/fice/article/view/7263',
      categoria: 'Estação Meteorológica',
    },
    {
      titulo: 'REVISÃO SISTEMÁTICA SIMPLIFICADA DA LITERATURA ACERCA DE GEORREFERENCIAMENTO DE CASOS DE DENGUE E AEDES AEGYPTI',
      autores: 'Fischer, L. M. et al.',
      data: 'Março de 2026',
      evento_revista: 'MICTI',
      link: 'https://centraldeeventos.ifc.edu.br/anais/micti2025/1381841-revisao-sistematica-simplificada-da-literatura-acerca-de---georreferenciamento-de-casos-de-dengue-e-aedes-aegypt/',
      categoria: 'Plataforma VigiAA',
    },
    {
      titulo: 'REVISÃO LITERÁRIA SOBRE SOFTWARES SERVIDORES DE MAPAS WEB USADOS NO AUXÍLIO AO ENFRENTAMENTO DO MOSQUITO AEDES AEGYPTI DA DENGUE',
      autores: 'Santiago, L. H. M. et al.',
      data: 'Março de 2026',
      evento_revista: 'MICTI',
      link: 'https://centraldeeventos.ifc.edu.br/anais/micti2025/1382018-revisao-literaria-sobre-softwares-servidores-de-mapas-web--usados-no-auxilio-ao-enfrentamento-do-mosquito-aedes-/',
      categoria: 'Plataforma VigiAA',
    },
    {
      titulo: 'REVISÃO SISTEMÁTICA SIMPLIFICADA SOBRE TÉCNICAS DE GEORREFERENCIAMENTO PARA COMBATE DO AEDES AEGYPTI',
      autores: 'Ferreira, I. M. A. et al.',
      data: 'Março de 2026',
      evento_revista: 'MICTI',
      link: 'https://centraldeeventos.ifc.edu.br/anais/micti2025/1381919-revisao-sistematica-simplificada-sobre-tecnicas-de-georreferenciamento-para-combate-do-aedes-aegypti/',
      premiado: 'Trabalho destaque categoria EAD.',
      categoria: 'Plataforma VigiAA',
    },
    {
      titulo: 'PLATAFORMA VIGIAA: MAPEAMENTO DO AEDES AEGYPTI EM CAMBORIÚ-SC',
      autores: 'Fischer, L. M. et al.',
      data: 'Junho de 2026',
      evento_revista: 'ENSIPEX',
      link: 'https://ime.events/v-ensipex/anais?utm_source=direct&utm_medium=organic#trabalho/81092/plataforma-vigiaa-mapeamento-do-aedes-aegypti-em-camboriu-sc',
      categoria: 'Plataforma VigiAA',
    }
  ];

  const categorias = ['Plataforma VigiAA', 'Estação Meteorológica'];

  return (
    <div className="page-container">
      <NavBar />
      <div className="publicacoes-body">
        <h1 className="titulo-pagina">Publicações</h1>

        {categorias.map((cat) => {
          const artigosFiltrados = artigos.filter((artigo) => artigo.categoria === cat);
          
          const artigosOrdenados = [...artigosFiltrados].sort((a, b) => {

            if (a.premiado && !b.premiado) return -1;
            if (!a.premiado && b.premiado) return 1;

            const dataA = parseData(a.data);
            const dataB = parseData(b.data);
            return dataB - dataA; // Ordenação decrescente de data
          });

          return (
            <div key={cat} className="sessao-categoria">
              <h2 className="titulo-categoria">{cat}</h2>
              <hr className="divisoria-categoria" />
              {artigosOrdenados.length > 0 ? (
                <ul className="lista-artigos">
                  {artigosOrdenados.map((artigo, index) => (
                    <li key={index} className="item-artigo">
                      <h3 className="titulo-artigo">{artigo.titulo}</h3>
                      <p className="autores-artigo">{artigo.autores}</p>
                      <div className="data-apresentacao">
                        <p className="data-artigo">{artigo.data}</p> 
                        <p className="data-artigo">|</p>
                        <p className="evento-revista">{artigo.evento_revista}</p>
                      </div>
                      {artigo.premiado && (
                        <p className="tag-premiado">
                          <FaMedal style={{ color: '#f0da16', marginTop: '2px' }} /> Premiado: {artigo.premiado}
                        </p>
                      )}
                      <a href={artigo.link} target="_blank" rel="noopener noreferrer" className="link-artigo">
                        Ver sobre
                      </a>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="sem-publicacoes">Nenhuma publicação cadastrada nesta categoria ainda.</p>
              )}
            </div>
          );
        })}
      </div>
      <Footer />
    </div>
  );
};

export default Publicações;