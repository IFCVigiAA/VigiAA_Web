import React from 'react';
import NavBar from '../components/NavBar';
import Footer from '../components/Footer';
import './Publicacoes.css';
import { FaMedal } from 'react-icons/fa';

const Publicações = () => {
  const artigos = [
    {
      titulo: 'REVISÃO SISTEMÁTICA SIMPLIFICADA DA LITERATURA ACERCA DE GEORREFERENCIAMENTO DE CASOS DE DENGUE E AEDES AEGYPTI',
      autores: 'Fischer, L. M. et al.',
      data: 'Agosto de 2025',
      link: 'https://publicacoes.ifc.edu.br/index.php/fice/article/view/7118',
      premiado: '1º Lugar FICE XVI na categoria pesquisa em Ciências exatas e da Terra.',
      categoria: 'FICE',
    },
    {
      titulo: 'AVALIAÇÃO DE SOFTWARES PARA SERVIDOR DE MAPAS WEB',
      autores: 'Santiago, L. H. M. et al.',
      data: 'Agosto de 2025',
      link: 'https://publicacoes.ifc.edu.br/index.php/fice/article/view/7201',
      categoria: 'FICE',
    },
    {
      titulo: 'TÉCNICAS DE GEORREFERENCIAMENTO PARA COMBATE DO AEDES AEGYPTI',
      autores: 'Ferreira, I. M. A. et al.',
      data: 'Agosto de 2025',
      link: 'https://publicacoes.ifc.edu.br/index.php/fice/article/view/7197',
      categoria: 'FICE',
    },
    {
      titulo: 'ESTAÇÃO METEOROLÓGICA DE BAIXO CUSTO',
      autores: 'Pereira, R. L. C. S. et al.',
      data: 'Dezembro de 2025',
      link: 'https://publicacoes.ifc.edu.br/index.php/fice/article/view/7265',
      categoria: 'FICE',
    },
    {
      titulo: 'MONITORAMENTO LARVAL DE AEDES AEGYPT',
      autores: 'Pereira, R. L. C. S. et al.',
      data: 'Dezembro de 2025',
      link: 'https://publicacoes.ifc.edu.br/index.php/fice/article/view/7263',
      categoria: 'FICE',
    },
    {
      titulo: 'REVISÃO SISTEMÁTICA SIMPLIFICADA DA LITERATURA ACERCA DE GEORREFERENCIAMENTO DE CASOS DE DENGUE E AEDES AEGYPTI',
      autores: 'Fischer, L. M. et al.',
      data: 'Março de 2026',
      link: 'https://centraldeeventos.ifc.edu.br/anais/micti2025/1381841-revisao-sistematica-simplificada-da-literatura-acerca-de---georreferenciamento-de-casos-de-dengue-e-aedes-aegypt/',
      categoria: 'MICTI',
    },
    {
      titulo: 'REVISÃO LITERÁRIA SOBRE SOFTWARES SERVIDORES DE MAPAS WEB USADOS NO AUXÍLIO AO ENFRENTAMENTO DO MOSQUITO AEDES AEGYPTI DA DENGUE',
      autores: 'Santiago, L. H. M. et al.',
      data: 'Março de 2026',
      link: 'https://centraldeeventos.ifc.edu.br/anais/micti2025/1382018-revisao-literaria-sobre-softwares-servidores-de-mapas-web--usados-no-auxilio-ao-enfrentamento-do-mosquito-aedes-/',
      categoria: 'MICTI',
    },
    {
      titulo: 'REVISÃO SISTEMÁTICA SIMPLIFICADA SOBRE TÉCNICAS DE GEORREFERENCIAMENTO PARA COMBATE DO AEDES AEGYPTI',
      autores: 'Ferreira, I. M. A. et al.',
      data: 'Março de 2026',
      link: 'https://centraldeeventos.ifc.edu.br/anais/micti2025/1381919-revisao-sistematica-simplificada-sobre-tecnicas-de-georreferenciamento-para-combate-do-aedes-aegypti/',
      premiado: 'Trabalho destaque categoria EAD.',
      categoria: 'MICTI',
    }
  ];

  const categorias = ['FICE', 'MICTI'];

  return (
    <div className="page-container">
      <NavBar />
      <div className="publicacoes-body">
        <h1 className="titulo-pagina">Publicações</h1>

        {categorias.map((cat) => {
          const artigosFiltrados = artigos.filter((artigo) => artigo.categoria === cat);

          return (
            <div key={cat} className="secao-categoria">
              <h2 className="titulo-categoria">{cat}</h2>
              <hr className="divisoria-categoria" />
              
              {artigosFiltrados.length > 0 ? (
                <ul className="lista-artigos">
                  {artigosFiltrados.map((artigo, index) => (
                    <li key={index} className="item-artigo">
                      <h3 className="titulo-artigo">{artigo.titulo}</h3>
                      <p className="autores-artigo">{artigo.autores}</p>
                      <p className="data-artigo">{artigo.data}</p>
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