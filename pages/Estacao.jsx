import NavBar from '../components/NavBar'
import Footer from '../components/Footer'
import './Estacao.css'

const Estacao = () => {
  return (
    <div className="page-container">
      <NavBar />
      <div className="sobre-container">
        <div className="sobre-content">
          <h1>Estação Meteorológica de Baixo Custo</h1>
          <p>
            Este projeto tem como objetivo desenvolver uma estação meteorológica acessível, utilizando componentes de baixo custo para realizar o monitoramento ambiental em tempo real. 
            A estação coleta dados como temperatura, umidade, pressão atmosférica, entre outros, e os disponibiliza em uma plataforma digital para consulta pública e uso acadêmico.
          </p>
          <iframe src="https://tb.geati.camboriu.ifc.edu.br/dashboard/c50dabf0-5703-11ee-bdd4-b1244f07481c?publicId=d17ce940-5718-11ee-bdd4-b1244f07481c" width="1200" height="800"></iframe>
         
          
          <h2>Tecnologias Utilizadas</h2>
          <ul className="tech-list">
            <li><strong>Arduino</strong> – microcontrolador principal da estação</li>
            <li><strong>DHT22</strong> – sensor de temperatura e umidade</li>
            <li><strong>BMP180</strong> – sensor de pressão atmosférica</li>
            <li><strong>ESP8266</strong> – módulo Wi-Fi para envio dos dados</li>
            <li><strong>Node.js + Express</strong> – backend para receber e armazenar os dados</li>
          </ul>
        </div>
      </div>
      <Footer />
    </div>
  );
};

export default Estacao;
