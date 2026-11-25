import React, { useState, useEffect } from 'react';
import './Noticias.css';
import NavBar from '../components/NavBar';
import Footer from '../components/Footer';

export default function Noticias() {
  const [noticias, setNoticias] = useState([]);
  const [noticiaSelecionada, setNoticiaSelecionada] = useState(null);
  const [carregando, setCarregando] = useState(true);
  const [isAdmin, setIsAdmin] = useState(false);

  const [modalCadastroAberta, setModalCadastroAberta] = useState(false);
  const [noticiaEditandoId, setNoticiaEditandoId] = useState(null);
  const [imagemAtualUrl, setImagemAtualUrl] = useState(null);
  const [removerImagem, setRemoverImagem] = useState(false);
  const [salvando, setSalvando] = useState(false);
  const [erroForm, setErroForm] = useState('');
  const [form, setForm] = useState({
    title: '',
    text: '',
    publication_date: '',
    expiration_date: '',
    image: null,
  });

  const carregarNoticias = () => {
    setCarregando(true);
    fetch('/api/casos/noticias/')
      .then((res) => (res.ok ? res.json() : []))
      .then((data) => setNoticias(Array.isArray(data) ? data : []))
      .catch(() => setNoticias([]))
      .finally(() => setCarregando(false));
  };

  useEffect(() => {
    carregarNoticias();

    const token = localStorage.getItem('access');
    if (token) {
      fetch('/api/casos/me/', {
        headers: { Authorization: `Bearer ${token}` },
      })
        .then((res) => (res.ok ? res.json() : null))
        .then((user) => {
          if (user && (user.is_staff || user.is_superuser)) {
            setIsAdmin(true);
          }
        })
        .catch(() => setIsAdmin(false));
    }
  }, []);

  const isoParaInputLocal = (isoString) => {
    if (!isoString) return '';
    const d = new Date(isoString);
    d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
    return d.toISOString().slice(0, 16);
  };

  const abrirModalCadastro = () => {
    setNoticiaEditandoId(null);
    setImagemAtualUrl(null);
    setRemoverImagem(false);
    setForm({
      title: '',
      text: '',
      publication_date: isoParaInputLocal(new Date().toISOString()),
      expiration_date: '',
      image: null,
    });
    setErroForm('');
    setModalCadastroAberta(true);
  };

  const abrirModalEdicao = (e, item) => {
    if (e) e.stopPropagation();
    setNoticiaEditandoId(item.id);
    setImagemAtualUrl(item.image || null);
    setRemoverImagem(false);
    setForm({
      title: item.title || '',
      text: item.text || '',
      publication_date: isoParaInputLocal(item.publication_date),
      expiration_date: isoParaInputLocal(item.expiration_date),
      image: null,
    });
    setErroForm('');
    setNoticiaSelecionada(null);
    setModalCadastroAberta(true);
  };

  const handleSubmitNoticia = async (e) => {
    e.preventDefault();
    setErroForm('');
    setSalvando(true);

    try {
      const formData = new FormData();
      formData.append('title', form.title);
      formData.append('text', form.text);

      if (form.publication_date) {
        formData.append('publication_date', new Date(form.publication_date).toISOString());
      }
      formData.append(
        'expiration_date',
        form.expiration_date ? new Date(form.expiration_date).toISOString() : ''
      );

      if (form.image) {
        formData.append('image', form.image);
      } else if (noticiaEditandoId && removerImagem) {
        formData.append('remover_imagem', 'true');
      }

      const token = localStorage.getItem('access');
      const url = noticiaEditandoId
        ? `/api/casos/noticias/${noticiaEditandoId}/`
        : '/api/casos/noticias/';
      const method = noticiaEditandoId ? 'PATCH' : 'POST';

      const res = await fetch(url, {
        method,
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.erro || data.detail || 'Erro ao salvar notícia.');
      }

      setModalCadastroAberta(false);
      setNoticiaEditandoId(null);
      carregarNoticias();
    } catch (err) {
      setErroForm(err.message);
    } finally {
      setSalvando(false);
    }
  };

  const handleExcluirNoticia = async (e, id) => {
    if (e) e.stopPropagation();
    if (!window.confirm('Tem certeza que deseja excluir esta notícia permanentemente?')) {
      return;
    }

    try {
      const token = localStorage.getItem('access');
      const res = await fetch(`/api/casos/noticias/${id}/`, {
        method: 'DELETE',
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.erro || data.detail || 'Erro ao excluir notícia.');
      }

      if (noticiaSelecionada?.id === id) {
        setNoticiaSelecionada(null);
      }
      carregarNoticias();
    } catch (err) {
      alert(err.message);
    }
  };

  const formatarData = (isoString) => {
    if (!isoString) return '';
    return new Date(isoString).toLocaleDateString('pt-BR', {
      day: '2-digit',
      month: 'long',
      year: 'numeric',
    });
  };

  return (
    <div className="page-container">
      <NavBar />
      <div className="noticias-page">
        <header className="noticias-header noticias-header-flex">
          <div>
            <h1>Notícias e Boletins</h1>
            <p>Acompanhe comunicados oficiais, alertas epidemiológicos e atualizações do VigiAA.</p>
          </div>

          {isAdmin ? (
            <button type="button" className="btn-nova-noticia" onClick={abrirModalCadastro}>
              + Nova Notícia
            </button>
          ) : (
            <button
              type="button"
              className="btn-admin-login"
              onClick={() => (window.location.href = '/login?next=/Noticias')}
            >
              Área Administrativa
            </button>
          )}
        </header>

        {carregando ? (
          <p className="noticias-loading">Carregando notícias...</p>
        ) : noticias.length === 0 ? (
          <p className="noticias-vazio">Nenhuma notícia ativa no momento.</p>
        ) : (
          <div className="noticias-grid">
            {noticias.map((item) => (
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
                  <div className="noticia-card-footer">
                    <span className="noticia-leia-mais">Ler completa →</span>
                    {isAdmin && (
                      <div className="noticia-admin-btns">
                        <button
                          type="button"
                          className="btn-editar-noticia"
                          onClick={(e) => abrirModalEdicao(e, item)}
                        >
                          Editar
                        </button>
                        <button
                          type="button"
                          className="btn-excluir-noticia"
                          onClick={(e) => handleExcluirNoticia(e, item.id)}
                        >
                          Excluir
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              </article>
            ))}
          </div>
        )}

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

                {isAdmin && (
                  <div className="noticia-modal-admin-acoes">
                    <button
                      type="button"
                      className="btn-editar-noticia"
                      onClick={(e) => abrirModalEdicao(e, noticiaSelecionada)}
                    >
                      Editar notícia
                    </button>
                    <button
                      type="button"
                      className="btn-excluir-noticia"
                      onClick={(e) => handleExcluirNoticia(e, noticiaSelecionada.id)}
                    >
                      Excluir notícia
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {modalCadastroAberta && (
          <div className="noticia-modal-overlay" onClick={() => setModalCadastroAberta(false)}>
            <div className="noticia-modal noticia-modal-form" onClick={(e) => e.stopPropagation()}>
              <div className="noticia-form-header">
                <h2>{noticiaEditandoId ? 'Editar Notícia' : 'Cadastrar Nova Notícia'}</h2>
                <button
                  type="button"
                  className="noticia-form-close"
                  onClick={() => setModalCadastroAberta(false)}
                >
                  ✕
                </button>
              </div>

              <form onSubmit={handleSubmitNoticia} className="noticia-form">
                {erroForm && <div className="noticia-form-erro">{erroForm}</div>}

                <label>
                  Título *
                  <input
                    type="text"
                    maxLength={255}
                    required
                    value={form.title}
                    onChange={(e) => setForm({ ...form, title: e.target.value })}
                    placeholder="Ex: Mutirão de limpeza contra a dengue neste sábado"
                  />
                </label>

                <div className="noticia-form-datas">
                  <label>
                    Data de Publicação *
                    <input
                      type="datetime-local"
                      required
                      value={form.publication_date}
                      onChange={(e) => setForm({ ...form, publication_date: e.target.value })}
                    />
                  </label>

                  <label>
                    Data de Validade (opcional)
                    <input
                      type="datetime-local"
                      value={form.expiration_date}
                      onChange={(e) => setForm({ ...form, expiration_date: e.target.value })}
                    />
                  </label>
                </div>

                <label>
                {noticiaEditandoId
                  ? 'Substituir Imagem de Capa (padrão 1430x900px)'
                  : 'Imagem de Capa (padrão 1430x900px)'}
                <input
                  type="file"
                  accept="image/*"
                  onChange={(e) => {
                    setForm({ ...form, image: e.target.files?.[0] || null });
                    if (e.target.files?.[0]) setRemoverImagem(false);
                  }}
                />
              </label>

                {noticiaEditandoId && imagemAtualUrl && !form.image && (
                  <label className="noticia-remover-img-check">
                    <input
                      type="checkbox"
                      checked={removerImagem}
                      onChange={(e) => setRemoverImagem(e.target.checked)}
                    />
                    Remover imagem atual desta notícia
                  </label>
                )}

                <label>
                  Conteúdo da Notícia *
                  <textarea
                    rows={6}
                    required
                    value={form.text}
                    onChange={(e) => setForm({ ...form, text: e.target.value })}
                    placeholder="Escreva o texto completo da notícia..."
                  />
                </label>

                <div className="noticia-form-acoes">
                  <button
                    type="button"
                    className="btn-cancelar"
                    onClick={() => setModalCadastroAberta(false)}
                  >
                    Cancelar
                  </button>
                  
                  <button type="submit" className="btn-salvar" disabled={salvando}>
                    {salvando
                      ? 'Salvando...'
                      : noticiaEditandoId
                      ? 'Salvar Alterações'
                      : 'Publicar Notícia'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>
      <Footer />
    </div>
  );
}