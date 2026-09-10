import React from 'react';
import NavBar from '../components/NavBar';
import Footer from '../components/Footer';
import './Sobre.css'; 
const SobreApp = () => {
  return (
    <>
      <div className="page-container">
        <NavBar />
        <div className="sobre-banner">
          <div className="text-box">
            <h1 className="main-title">VigiAA App</h1>
            <h2 className="subtitle">A cidade no combate ao Aedes aegypti. A sua participação também.</h2>
          </div>
          <div className="logo-box">
            <img 
              src={import.meta.env.BASE_URL + 'logos/logo_home.png'} 
              alt="Logo VigiAA App" 
              title="Logo VigiAA App" 
              className="logoSobre" 
            />
          </div>
        </div>

        <div className="sobre-container">
          <div className="sobre-header">
            <h1>Sobre o <span>VigiAA App</span></h1>
          </div>

          <div className="sobre-section">
            <p>
              O <strong>VigiAA App</strong> é um aplicativo móvel desenvolvido para aproximar a população 
              das ações de prevenção e combate à dengue em Camboriú-SC.
            </p>
            <br />
            <p>
              Por meio do aplicativo, os cidadãos podem registrar focos do mosquito <em>Aedes aegypti</em> e 
              comunicar casos suspeitos ou confirmados de dengue, contribuindo para a identificação de ocorrências 
              e para a construção de uma base de informações que apoia as ações de vigilância no município.
            </p>
          </div>

          <div className="sobre-section">
            <h2>Como você pode contribuir?</h2>
            <p>Com poucos passos, é possível utilizar o aplicativo para:</p>
            <br />
            <ul className="tech-list">
              <li>
                <strong>Registrar focos do Aedes aegypti</strong> – Informando a localização e adicionando registros que auxiliem na identificação do possível criadouro.
              </li>
              <li>
                <strong>Registrar casos suspeitos ou confirmados de dengue</strong> – Contribuindo para ampliar as informações disponíveis sobre a ocorrência da doença.
              </li>
              <li>
                <strong>Compartilhar a localização das ocorrências</strong> – Facilitando a identificação espacial dos registros.
              </li>
              <li>
                <strong>Adicionar fotografias</strong> – Tornando as informações registradas mais completas.
              </li>
              <li>
                <strong>Acompanhar informações em tempo real</strong> – Dados sobre dengue e <em>Aedes aegypti</em> em Camboriú, diretamente pela tela inicial do aplicativo.
              </li>
              <li>
                <strong>Consultar conteúdos de orientação</strong> – Incluindo sintomas da dengue e informações sobre prevenção e combate ao mosquito.
              </li>
              <li>
                <strong>Gerenciar seus dados</strong> – Por meio da área de perfil.
              </li>
            </ul>
          </div>

          <div className="sobre-section">
            <h2>Sua informação pode ajudar a proteger a cidade</h2>
            <p>
              O VigiAA App utiliza a participação colaborativa da população como uma aliada da vigilância. 
              Cada registro realizado pelo aplicativo contribui para ampliar o conhecimento sobre a presença do mosquito e a ocorrência da dengue no território.
            </p>
            <br />
            <p>
              <strong>Identificou um possível foco? Viu uma situação que pode favorecer a proliferação do mosquito? Teve conhecimento de um caso de dengue?</strong>
            </p>
            <p>
              Registre pelo VigiAAapp e faça parte dessa rede de colaboração.
            </p>
          </div>

          <div className="sobre-section">
            <h2>Baixe o VigiAA App</h2>
            <p>
              A prevenção começa com informação, participação e ação. Baixe o aplicativo, registre ocorrências e ajude o município a estar mais preparado para o enfrentamento da dengue.
            </p>
            <br />
            <p style={{ fontStyle: 'italic', color: '#666' }}>
              *(Disponível em breve nas lojas Google Play e App Store)*
            </p>
            <br /><br />
          </div>
        </div>
        <Footer />
      </div>
    </>
  );
};

export default SobreApp;