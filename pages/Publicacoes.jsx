import React from 'react';
import NavBar from '../components/NavBar';
import Footer from '../components/Footer';
import './Publicacoes.css';
import { FaTrophy, FaMedal, FaAward } from 'react-icons/fa';

const Publicações = () => {
  const artigos = [
    {
      titulo: 'REVISÃO SISTEMÁTICA SIMPLIFICADA DA LITERATURA ACERCA DE GEORREFERENCIAMENTO DE CASOS DE DENGUE E AEDES AEGYPTI',
      autores: 'Fischer, L. M. et al.',
      data: 'Agosto de 2025',
      link: '/docs/FICE2025-VigiAA-ResumoExpandido-Lissandra-.pdf',
      
      premiado: '1º Lugar FICE XVI na categoria pesquisa em Ciências exatas e da Terra',
    },
    {
      titulo: 'AVALIAÇÃO DE SOFTWARES PARA SERVIDOR DE MAPAS WEB',
      autores: 'Santiago, L. H. M. et al.',
      data: 'Agosto de 2025',
      link: '/docs/FICE2025-VigiAA-ResumoExpandido-Luis.pdf',
    },
    {
      titulo: 'TÉCNICAS DE GEORREFERENCIAMENTO PARA COMBATE DO AEDES AEGYPTI',
      autores: 'Ferreira, I. M. A. et al.',
      data: 'Agosto de 2025',
      link: '/docs/VigiAA-FICE2025-ResumoExpandido-Ian.pdf',
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
              <h2 className="titulo-artigo">
                {artigo.titulo}
              </h2>
              
              <p className="autores-artigo">{artigo.autores}</p>
              <p className="data-artigo">{artigo.data}</p>
              {artigo.premiado && (
                <p className="tag-premiado">
                   <FaMedal style={{ color: '#f0da16', marginTop: '2px' }} /> Premiado: {artigo.premiado}
                </p>
              )}
              
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