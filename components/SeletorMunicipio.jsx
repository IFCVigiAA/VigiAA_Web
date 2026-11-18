import React, { useState, useEffect, useRef } from 'react';

export default function SeletorMunicipio({ apiBaseUrl = '/api/casos', onMunicipioAlterado }) {
  const [municipioAtual, setMunicipioAtual] = useState(null);
  const [busca, setBusca] = useState('');
  const [sugestoes, setSugestoes] = useState([]);
  const [aberto, setAberto] = useState(false);
  const [carregando, setCarregando] = useState(false);
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState('');
  const [dropdownPos, setDropdownPos] = useState({ top: 0, left: 0, width: 320 });

  const containerRef = useRef(null);
  const inputRef = useRef(null);

  const getHeaders = (isJson = false) => {
    const headers = {};
    if (isJson) headers['Content-Type'] = 'application/json';

    const token = localStorage.getItem('access');
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const csrfMatch = document.cookie.match(/(^|;\s*)csrftoken=([^;]*)/);
    if (csrfMatch) {
      headers['X-CSRFToken'] = decodeURIComponent(csrfMatch[2]);
    }

    return headers;
  };

  const atualizarPosicaoDropdown = () => {
    if (inputRef.current) {
      const rect = inputRef.current.getBoundingClientRect();
      setDropdownPos({
        top: rect.bottom + 4,
        left: rect.left,
        width: rect.width,
      });
    }
  };

  useEffect(() => {
    fetch(`${apiBaseUrl}/municipio-ativo/`, {
      headers: getHeaders(),
    })
      .then(async (res) => {
        if (!res.ok) return null;
        return res.json();
      })
      .then((data) => {
        if (data && data.nome) {
          setMunicipioAtual(data);
          setBusca(`${data.nome} - ${data.uf}`);
        }
      })
      .catch(() => {});
  }, [apiBaseUrl]);

  useEffect(() => {
    const handleClickFora = (e) => {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setAberto(false);
      }
    };
    document.addEventListener('mousedown', handleClickFora);
    window.addEventListener('resize', atualizarPosicaoDropdown);
    return () => {
      document.removeEventListener('mousedown', handleClickFora);
      window.removeEventListener('resize', atualizarPosicaoDropdown);
    };
  }, []);

  useEffect(() => {
    if (!aberto) return;

    const termo = busca.includes(' - ') ? busca.split(' - ')[0].trim() : busca.trim();
    const timer = setTimeout(async () => {
      setCarregando(true);
      setErro('');
      try {
        const res = await fetch(
          `${apiBaseUrl}/municipios-disponiveis/?q=${encodeURIComponent(termo)}`,
          { headers: getHeaders() }
        );

        const contentType = res.headers.get('content-type') || '';
        if (!contentType.includes('application/json')) {
          setErro(`Rota não encontrada ou retorno inválido (HTTP ${res.status})`);
          setSugestoes([]);
          return;
        }

        const data = await res.json();
        if (!res.ok) {
          setErro(data.detail || data.erro || `Erro HTTP ${res.status}`);
          setSugestoes([]);
        } else {
          setSugestoes(data.municipios || []);
        }
      } catch (err) {
        setErro('Servidor indisponível');
        setSugestoes([]);
      } finally {
        setCarregando(false);
      }
    }, 250);

    return () => clearTimeout(timer);
  }, [busca, aberto, apiBaseUrl]);

  const handleSelecionar = async (mun) => {
    setSalvando(true);
    setErro('');
    setAberto(false);
    setBusca(mun.label);

    try {
      const res = await fetch(`${apiBaseUrl}/definir-municipio/`, {
        method: 'POST',
        headers: getHeaders(true),
        body: JSON.stringify({ cd_mun: String(mun.cd_mun) }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || data.erro || `Erro HTTP ${res.status}`);
      }

      const resAtivo = await fetch(`${apiBaseUrl}/municipio-ativo/`, {
        headers: getHeaders(),
      });
      const dadosAtivos = await resAtivo.json();

      setMunicipioAtual(dadosAtivos);
      if (onMunicipioAlterado) {
        onMunicipioAlterado(dadosAtivos);
      }
    } catch (err) {
      setErro(err.message);
      setAberto(true);
    } finally {
      setSalvando(false);
    }
  };

  return (
    <div ref={containerRef} style={{ position: 'relative', width: '320px', maxWidth: '100%' }}>
      <input
        ref={inputRef}
        type="text"
        value={busca}
        disabled={salvando}
        placeholder="Selecione ou digite o município..."
        onFocus={() => {
          atualizarPosicaoDropdown();
          setAberto(true);
        }}
        onChange={(e) => {
          setBusca(e.target.value);
          atualizarPosicaoDropdown();
          setAberto(true);
        }}
        style={{
          width: '100%',
          padding: '8px 12px',
          borderRadius: '6px',
          border: '1px solid #94a3b8',
          fontSize: '14px',
          backgroundColor: '#fff',
          color: '#0f172a',
          boxSizing: 'border-box',
        }}
      />

      {aberto && (
        <ul
          style={{
            position: 'fixed',
            top: `${dropdownPos.top}px`,
            left: `${dropdownPos.left}px`,
            width: `${dropdownPos.width}px`,
            zIndex: 99999,
            maxHeight: '240px',
            overflowY: 'auto',
            backgroundColor: '#ffffff',
            border: '1px solid #cbd5e1',
            borderRadius: '6px',
            margin: 0,
            padding: 0,
            listStyle: 'none',
            boxShadow: '0 10px 25px rgba(0, 0, 0, 0.2)',
          }}
        >
          {carregando ? (
            <li style={{ padding: '10px 12px', fontSize: '13px', color: '#64748b' }}>
              Buscando municípios...
            </li>
          ) : erro ? (
            <li style={{ padding: '10px 12px', fontSize: '13px', color: '#dc2626' }}>
              {erro}
            </li>
          ) : sugestoes.length === 0 ? (
            <li style={{ padding: '10px 12px', fontSize: '13px', color: '#64748b' }}>
              Nenhum município encontrado
            </li>
          ) : (
            sugestoes.map((mun) => (
              <li
                key={mun.cd_mun}
                onMouseDown={() => handleSelecionar(mun)}
                style={{
                  padding: '9px 12px',
                  fontSize: '14px',
                  color: '#1e293b',
                  cursor: 'pointer',
                  borderBottom: '1px solid #f1f5f9',
                  backgroundColor: municipioAtual?.cd_mun === mun.cd_mun ? '#eff6ff' : '#ffffff',
                }}
              >
                <strong>{mun.nome}</strong> - {mun.uf}{' '}
                <span style={{ fontSize: '11px', color: '#94a3b8' }}>({mun.cd_mun})</span>
              </li>
            ))
          )}
        </ul>
      )}
    </div>
  );
}