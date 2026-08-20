  import React from 'react';
  import NavBar from '../components/NavBar';
  import Footer from '../components/Footer';
  import './Sobre.css';


  const Sobre = () => {
    return (
      <>
    
      <div className="page-container">
        <NavBar />
        <div className="sobre-banner">
          <div className="text-box">
            <h1 className="main-title">Plataforma Georreferenciada VigiAA</h1>
            <h2 className="subtitle">Vigilância do Aedes Aegypti</h2>
          </div>
          <div className="logo-box">
            <img src={import.meta.env.BASE_URL + 'logos/logo_home.png'} alt="Logo VigiAA" title="Logo VigiAA" className="logoSobre" />
          </div>
        </div>
        <div className="sobre-container">
        
          <div className="sobre-header">
            <h1>Sobre o Projeto <span>VigiAA</span></h1>
          </div>
          <div className="sobre-section">
            <p>
              O <strong>VigiAA</strong> é uma plataforma georreferenciada voltada a vigilância, 
              análise epidemiológica e mapeamento preditivo do mosquito <em>Aedes aegypti</em>, vetor da Dengue. 
              A plataforma automatiza a ingestão de dados municipais brutos e os transforma em inteligência geográfica, 
              disponibilizando mapas claros e acessíveis para a população, pesquisadores e gestores públicos.
            </p>
            <br />
            <p>
              Este projeto de pesquisa e desenvolvimento tecnológico foi aprovado e financiado pelo edital institucional 
              <strong><a href="https://fapesc.sc.gov.br/wp-content/uploads/2024/07/CP_fapesc_37_2024_aedes.pdf" target="_blank" rel="noopener noreferrer"> 37/2024 FAPESC</a></strong>.
            </p>
          </div>

          <div className="sobre-section">
            <h2>Arquitetura e Tecnologias Utilizadas</h2>
            <p>A plataforma foi projetada sob uma arquitetura robusta e distribuída, utilizando tecnologias como:</p>
            <ul className="tech-list">
              <li><strong>React</strong> – Engenharia do ecossistema frontend para a construção de uma interface dinâmica e de alta responsividade.</li>
              <li><strong>Django & Django REST Framework</strong> – Arquitetura de backend robusta, responsável pelas regras de negócio, APIs seguras e orquestração do sistema.</li>
              <li><strong>ArcGIS API & Geocodificação</strong> – Integração com microsserviços geográficos externos para tradução de endereços urbanos brutos em coordenadas espaciais precisas em tempo real.</li>
              <li><strong>PostgreSQL & PostGIS</strong> – Banco de dados analítico e geoespacial robusto, estruturado sob o Sistema Geodésico Brasileiro para armazenamento de geometrias complexas e tratamento de dados puros.</li>
              <li><strong>Leaflet & QGIS</strong> – Bibliotecas de visualização interativa no frontend integradas a ferramentas analíticas SIG para renderização de camadas de calor, mapas de pontos e focos de calor espaciais.</li>
            </ul>
          </div>

          <div className="sobre-section">
            <h2>Qual a importância do projeto?</h2>
            <p>
              O VigiAA quebra o gargalo do processamento manual de dados de saúde pública. Ele centraliza de forma inteligente 
              o ciclo completo da informação: desde o upload rápido de relatórios fragmentados (Casos Positivos, Pontos Estratégicos, 
              Armadilhas e Focos de Aedes) até a geração automática de mapas epidemiológicos de risco. 
            </p>
            <p>
              Com isso, o projeto reduz drasticamente o tempo de resposta das equipes de Vigilância Sanitária e Ambiental, 
              permitindo a ação mais rápida.
            </p>
          </div>
          <div className="sobre-section">
            <h2>Localização do Projeto</h2>
            <p>O projeto está localizado no laboratório GEATI no Instituto Federal Catarinense de Camboriú.</p>
            <div className="map-wrapper">
              <iframe
                title="Mapa do Google Maps com a localização do IFC Camboriú"
                src="https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d3175.9755605679343!2d-48.65769206859206!3d-27.01605670990075!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x94d8b5000eeb4f79%3A0x6b42a6cef196ef1f!2sGEATI!5e1!3m2!1spt-BR!2sbr!4v1758041982232!5m2!1spt-BR!2sbr"
                width="100%"
                height="390"
                style={{ border: '2px solid #00a053', borderRadius: '5px' }}
                allowFullScreen=""
                loading="lazy"
                referrerPolicy="no-referrer-when-downgrade"
              ></iframe>
            </div>
            <br /><br />
          </div>
        </div>
        <Footer />
      </div>
    </>);
  };

  export default Sobre;