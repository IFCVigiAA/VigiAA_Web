import { FaLinkedin, FaGraduationCap } from 'react-icons/fa';
import './ParticipanteCard.css';

function ParticipanteCard({ nome, cargo, foto, linkedinUrl, lattesUrl }) {
  return (
    <div className="card-participante">
      <img src={foto} alt={nome} className="foto-participante" />
      <h3>{nome}</h3>
      <p>{cargo}</p>
      <div className="botoes-links">
        <a href={lattesUrl} target="_blank" rel="noopener noreferrer" className="btn-link">
          <FaGraduationCap size={24} />
        </a>
        <a href={linkedinUrl} target="_blank" rel="noopener noreferrer" className="btn-link">
          <FaLinkedin size={24} />
        </a>
      </div>
    </div>
  );
}

export default ParticipanteCard;
