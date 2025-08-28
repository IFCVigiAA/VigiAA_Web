import NavBar from '../components/NavBar';
import Footer from '../components/Footer';
import ParticipanteCard from '../components/ParticipanteCard';
import './Participantes.css';

const Participantes = () => {
  return (
    <div className="page-container">
      <NavBar />
      <div className="bodyParticipantes">
        <div className="grupo">
          <h2>Pesquisadores</h2>
          <ul className="lista-participantes">
            <ParticipanteCard
              nome="Angelo A. Frozza"
              cargo="Coordenador Geral"
              foto={import.meta.env.BASE_URL + 'participantes/angelo.png'}
              lattesUrl="http://lattes.cnpq.br/5878372087019892"
              linkedinUrl="https://www.linkedin.com/in/angelo-frozza/"
            />
            <ParticipanteCard
              nome="Rafael de M. Speroni"
              cargo="Pesquisador"
              foto={import.meta.env.BASE_URL + 'participantes/speroni.png'}
              lattesUrl="http://lattes.cnpq.br/3483462003007835"
              linkedinUrl="https://www.linkedin.com/in/rafaelsperoni/"
            />
            <ParticipanteCard
              nome="Joice S. Mota"
              cargo="Pesquisadora"
              foto={import.meta.env.BASE_URL + 'participantes/joice.png'}
              lattesUrl="http://lattes.cnpq.br/7777714279933344"
              linkedinUrl="https://www.linkedin.com/in/joices/"
            />
            <ParticipanteCard
              nome="Airton Zancanaro"
              cargo="Pesquisador"
              foto={import.meta.env.BASE_URL + 'participantes/airton.png'}
              lattesUrl="http://lattes.cnpq.br/8797858687750467"
              linkedinUrl="https://www.linkedin.com/in/airton-zancanaro-294297165/"
            />
            <ParticipanteCard
              nome="Cleonice Maria Beppler"
              cargo="Pesquisadora"
              foto={import.meta.env.BASE_URL + 'participantes/cleonice.png'}
              lattesUrl="http://lattes.cnpq.br/9868609834605055"
              linkedinUrl="https://www.linkedin.com/in/cleonice-beppler-5120b814/"
            />
          </ul>
        </div>

        <div className="grupo">
          <h2>Bolsistas VigiAA</h2>
          <ul className="lista-participantes">
            <ParticipanteCard
              nome="Ian M. A. Ferreira"
              cargo="Bolsista"
              foto={import.meta.env.BASE_URL + 'participantes/ian.jpg'}
              lattesUrl="http://lattes.cnpq.br/5974108989255365"
              linkedinUrl="https://www.linkedin.com/in/ianmuradaraujoferreira/"
            />
            <ParticipanteCard
              nome="Luis H. de M. Santiago"
              cargo="Bolsista"
              foto={import.meta.env.BASE_URL + 'participantes/luis.png'}
              lattesUrl="http://lattes.cnpq.br/4395447968887299"
              linkedinUrl="https://www.linkedin.com/in/luis-henrique-de-melo-santiago-02064a96/"
            />
            <ParticipanteCard
              nome="Lissandra M. Fischer"
              cargo="Bolsista"
              foto={import.meta.env.BASE_URL + 'participantes/lissandra.jpg'}
              lattesUrl="http://lattes.cnpq.br/3849463744234834"
              linkedinUrl="https://www.linkedin.com/in/lissandramaiarafischer/"
            />
          </ul>
        </div>

        <div className="grupo">
          <h2>Bolsistas Estação Meteorológica</h2>
          <ul className="lista-participantes">
            <ParticipanteCard
              nome="Rafael Luiz Pereira"
              cargo="Bolsista"
              foto={import.meta.env.BASE_URL + 'participantes/rafaelluis.png'}
              lattesUrl="http://lattes.cnpq.br/6550069771613064"
              linkedinUrl=""
            />
            <ParticipanteCard
              nome="Cauã da C. Silva"
              cargo="Bolsista"
              foto={import.meta.env.BASE_URL + 'participantes/caua.png'}
              lattesUrl="http://lattes.cnpq.br/6896619338301324"
              linkedinUrl=""
            />
          </ul>
        </div>

        <div className="grupo">
          <h2>Bolsistas MOOC</h2>
          <ul className="lista-participantes">
            <ParticipanteCard
              nome="Tauana Flores"
              cargo="Bolsista"
              foto={import.meta.env.BASE_URL + 'participantes/tauana.png'}
              lattesUrl="http://lattes.cnpq.br/6660505753553493"
              linkedinUrl=""
            />
          </ul>
        </div>
      </div>
      <Footer />
    </div>
  );
};

export default Participantes;