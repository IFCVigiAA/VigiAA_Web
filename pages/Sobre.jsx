import React from 'react';
import NavBar from '../components/NavBar';
import Footer from '../components/Footer';
import './Sobre.css';
import WeatherComponent from '../components/WeatherComponent';

const Sobre = () => {
  return (
    <>
  <NavBar />
    <div className="page-container">
      <div className="sobre-body">
        <div className="text-box">
          <h1 className="main-title">Plataforma Georreferenciada VigiAA</h1>
          <h2 className="subtitle">Vigilância do Aedes Aegypti</h2>
        </div>
        <div className="logo-box">
          <img src={import.meta.env.BASE_URL + 'logos/logo_home.png'} alt="Logo VigiAA" title="Logo VigiAA" className="logo-img" />
        </div>
      </div>
      <div className="sobre-container">
      
        <div className="sobre-header">
          <h1>Sobre o Projeto <span>VigiAA</span></h1>
        </div>
        <div className="sobre-section">
          <h2>O que é o VigiAA?</h2>
          <p>
            O <strong>VigiAA</strong> é uma plataforma georreferenciada de monitoramento do mosquito
            <em> Aedes aegypti</em>, vetor da dengue. A plataforma visa disponibilizar dados claros e acessíveis à
            população, pesquisadores e gestores públicos.
          </p>
        </div>
        <div className="sobre-section">
          <h2>Objetivos</h2>
          <ul className="tech-list">
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
            focos de infestação do mosquito Aedes Aegypti, incentivando a conscientização e ações preventivas.
          </p>
        </div>

        <div className="sobre-section">
          <h2>Localização do Projeto</h2>
          <p>Nosso projeto está localizado no Instituto Federal Catarinense – Camboriú.</p>
          <div className="map-wrapper">
            <iframe
              title="Mapa do Google Maps com a localização do IFC Camboriú"
              src="https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d3175.9755605679343!2d-48.65769206859206!3d-27.01605670990075!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x94d8b5000eeb4f79%3A0x6b42a6cef196ef1f!2sGEATI!5e1!3m2!1spt-BR!2sbr!4v1758041982232!5m2!1spt-BR!2sbr"
              width="100%"
              height="450"
              style={{ border: '2px solid #00a053', borderRadius: '5px' }}
              allowFullScreen=""
              loading="lazy"
              referrerPolicy="no-referrer-when-downgrade"
            ></iframe>
          </div>
          <br /><br />
          <WeatherComponent />
        </div>
      </div>
      <Footer />
    </div>
  </>);
};

export default Sobre;