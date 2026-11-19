import React, { useState } from 'react';
import './Noticias.css';
import NavBar from '../components/NavBar';

const NOTICIAS_FICTICIAS = [
  {
    id: 1,
    title: 'Mutirão de limpeza e monitoramento de ovitrampas ocorre neste sábado',
    publication_date: '2026-11-16T09:00:00-03:00',
    image: 'https://images.unsplash.com/photo-1584036561566-baf8f5f1b144?auto=format&fit=crop&w=800&q=80',
    text: 'As equipes de vigilância epidemiológica realizarão neste sábado uma ação integrada nos bairros com maior índice de positividade apontados pelo sistema VigiAA.\n\nMoradores devem facilitar o acesso dos agentes de endemias devidamente identificados e eliminar recipientes com água parada em quintais e calhas.',
    expiration_date: '2026-12-30T23:59:59-03:00',
  },
  {
    id: 2,
    title: 'Boletim Epidemiológico: queda de 18% nos focos identificados na última semana',
    publication_date: '2026-11-12T14:30:00-03:00',
    image: 'https://images.unsplash.com/photo-1576091160550-2173dba999ef?auto=format&fit=crop&w=800&q=80',
    text: 'O cruzamento espacial realizado pela plataforma VigiAA indica redução nos focos ativos do Aedes aegypti nas áreas prioritárias.\n\nApesar da melhora, a Secretaria de Saúde reforça que o período de chuvas e calor exige atenção redobrada com vasos de plantas, caixas d’água e ralos externos.',
    expiration_date: null,
  },
  {
    id: 3,
    title: 'VigiAA expande monitoramento georreferenciado para novos municípios',
    publication_date: '2026-11-08T10:15:00-03:00',
    image: 'https://images.unsplash.com/photo-1524661135-423995f22d0b?auto=format&fit=crop&w=800&q=80',
    text: 'A nova atualização do sistema permite que gestores municipais importem planilhas de casos positivos, focos e ovitrampas com geocodificação automática.\n\nCom isso, o mapa interativo passa a apoiar ações preventivas em tempo real para qualquer cidade.',
    expiration_date: null,
  },
];

export default function Noticias() {
  const [noticiaSelecionada, setNoticiaSelecionada] = useState(null);

  const formatarData = (isoString) => {
    if (!isoString) return '';
    return new Date(isoString).toLocaleDateString('pt-BR', {
      day: '2-digit',
      month: 'long',
      year: 'numeric',
    });
  };

  return (
    <>
    <NavBar />
    <div className="noticias-page">
      <header className="noticias-header">
        <h1>Notícias e Boletins</h1>
        <p>Acompanhe comunicados oficiais, alertas epidemiológicos e atualizações do VigiAA.</p>
      </header>

      <div className="noticias-grid">
        {NOTICIAS_FICTICIAS.map((item) => (
          <article
            key={item.id}
            className="noticia-card"
            onClick={() => setNoticiaSelecionada(item)}
          >
            {item.image && (
              <div className="noticia-img-wrapper">
                <img src={item.image} alt={item.title} />
              </div>
            )}
            <div className="noticia-body">
              <span className="noticia-data">{formatarData(item.publication_date)}</span>
              <h2 className="noticia-titulo">{item.title}</h2>
              <p className="noticia-resumo">{item.text}</p>
              <span className="noticia-leia-mais">Ler completa →</span>
            </div>
          </article>
        ))}
      </div>

      {noticiaSelecionada && (
        <div className="noticia-modal-overlay" onClick={() => setNoticiaSelecionada(null)}>
          <div className="noticia-modal" onClick={(e) => e.stopPropagation()}>
            <button
              type="button"
              className="noticia-modal-fechar"
              onClick={() => setNoticiaSelecionada(null)}
              aria-label="Fechar"
            >
              ✕
            </button>
            {noticiaSelecionada.image && (
              <img
                src={noticiaSelecionada.image}
                alt={noticiaSelecionada.title}
                className="noticia-modal-img"
              />
            )}
            <div className="noticia-modal-conteudo">
              <span className="noticia-data">
                Publicado em {formatarData(noticiaSelecionada.publication_date)}
              </span>
              <h2>{noticiaSelecionada.title}</h2>
              <div className="noticia-texto-completo">
                {noticiaSelecionada.text.split('\n').map((paragrafo, idx) =>
                  paragrafo.trim() ? <p key={idx}>{paragrafo}</p> : null
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
    </>
  );
}