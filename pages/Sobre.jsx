import React, { useEffect, useState } from 'react';
import NavBar from '../components/NavBar';
import Footer from '../components/Footer';
import './Sobre.css';

import MapaLab from '../components/MapaLab';
import WeatherComponent from '../components/WeatherComponent';

const Sobre = () => {
  const position = [-26.9905, -48.6295]; // Coordenadas de Camboriú, SC


  return (
    <div className="page-container">
      <NavBar />
      <div className="sobre-container">
        <div className="sobre-header">
          <h1>Sobre o Projeto <span>VigiAA</span></h1>
          <p>Vigilância do Aedes Aegypti</p>
        </div>

        <div className="sobre-section">
          <h2>O que é o VigiAA?</h2>
          <p>
            O <strong>VigiAA</strong> é uma plataforma georreferenciada de monitoramento do mosquito
            <em>Aedes aegypti</em>, vetor da dengue. A plataforma visa disponibilizar dados claros e acessíveis à
            população, pesquisadores e gestores públicos.
          </p>
        </div>
        <div className="sobre-section">
          <h2>Objetivos</h2>
          <ul>
            <li>Mapear e visualizar focos do mosquito em tempo real.</li>
            <li>Exibir dados de casos positivos com localização geográfica.</li>
            <li>Oferecer informação acessível à sociedade.</li>
          </ul>
        </div>

        <div className="sobre-section">
          <h2>Tecnologias Utilizadas</h2>
          <p>A plataforma foi desenvolvida com tecnologias como:</p>
          <ul className="tech-list">
            <li><strong>QGIS</strong> – para análise, criação de mapas e exportação de dados geográficos</li>
            <li><strong>React</strong> – para construção da interface web</li>
            <li><strong>Leaflet</strong> – para visualização interativa de mapas</li>
            <li><strong>PostgreSQL</strong> – para armazenamento de dados</li>
          </ul>
        </div>

        <div className="sobre-section">
          <h2>Qual a importância do projeto?</h2>
          <p>
            O VigiAA reúne informações geográficas sobre as áreas de risco e acompanha a evolução dos
            focos de infestação do mosquito Aedes Aegypti em Camboriú, incentivando a conscientização e ações preventivas.
          </p>
        </div>

        <div className="sobre-section">
          <h2>Localização do Projeto</h2>
          <p>Nosso projeto está baseado em Camboriú, Santa Catarina, onde monitoramos os focos do Aedes aegypti.</p>
          <WeatherComponent/>
        </div>
      </div>
      <Footer />
    </div>
  );
};



export default Sobre;