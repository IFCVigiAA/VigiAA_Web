import { useMemo, useState, useRef, useEffect } from 'react'
import './Upload_planilhas.css'
import NavBar from '../components/NavBar'

const API_BASE = ''

const endpoints = {
  focos: '/api/casos/upload/focos/',
  armadilhas: '/api/casos/upload/armadilhas/',
  pontos: '/api/casos/upload/pontos/',
  casos: '/api/casos/upload/positivos/',
  ovitrampas: '/api/casos/upload/ovitrampas/',
  geoprocessar: '/api/casos/geoprocessar-positivos/',
  extrairCabecalho: '/api/casos/extrair-cabecalho/',
}

const syncEndpoint = '/api/casos/sincronizar/'

const uploadKeyByTipo = {
  casos: 'positivos',
  focos: 'focos',
  armadilhas: 'armadilhas',
  pontos: 'pontos',
  ovitrampas: 'ovitrampas',
}

export default function UploadPlanilhas() {
  const [arquivos, setArquivos] = useState({
    casos: null,
    pontos: null,
    focos: null,
    armadilhas: null,
    ovitrampas: null,
  })

  const [celulaCabecalho, setCelulaCabecalho] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [sincronizando, setSincronizando] = useState(false)
  const [geoprocessando, setGeoprocessando] = useState(false)
  const [progresso, setProgresso] = useState(0)
  const [log, setLog] = useState('')
  const [mensagemStatus, setMensagemStatus] = useState('')

  // ESTADOS DO MODAL DE MAPEAMENTO
  const [modalOpen, setModalOpen] = useState(false)
  const [tipoMapeando, setTipoMapeando] = useState(null)
  const [dadosMapeamento, setDadosMapeamento] = useState({
    colunasPlanilha: [],
    camposBanco: {},
    sugestao: {},
  })
  const [mapeamentosDefinidos, setMapeamentosDefinidos] = useState({})

  const ultimaMensagem = useRef('')

  const pendentes = useMemo(
    () => Object.entries(arquivos).filter(([_, file]) => !!file),
    [arquivos]
  )
  const handleRemoverArquivo = (tipo) => {
    if (!tipo) return

    setArquivos(prev => ({ ...prev, [tipo]: null }))

    const inputElement = document.querySelector(`input[name="${tipo}"]`)
    if (inputElement) {
      inputElement.value = ''
    }

    setMapeamentosDefinidos(prev => {
      const novos = { ...prev }
      delete novos[tipo]
      sessionStorage.setItem('mapeamento_temp', JSON.stringify(novos))
      return novos
    })
  }
  const handleCancelarMapeamento = () => {
    if (tipoMapeando) {
      handleRemoverArquivo(tipoMapeando)
    }

    // 2. Fecha o modal e limpa o tipo
    setModalOpen(false)
    setTipoMapeando(null)
  }
  function getAuthHeader() {
    const token = localStorage.getItem('access') || localStorage.getItem('token')
    if (!token) return {}
    const authValue = token.startsWith('Bearer ') ? token : `Bearer ${token}`
    return { Authorization: authValue }
  }

  async function handleChange(e) {
    const file = e.target.files?.[0] ?? null
    const tipo = e.target.name

    setArquivos(prev => ({ ...prev, [tipo]: file }))

    if (file) {
      const formData = new FormData()
      formData.append('arquivo', file)
      formData.append('tipo', tipo)

      if (celulaCabecalho.trim()) {
        formData.append('celula_cabecalho', celulaCabecalho.trim())
      }

      try {
        const res = await fetch(API_BASE + endpoints.extrairCabecalho, {
          method: 'POST',
          headers: getAuthHeader(),
          body: formData,
        })

        if (res.ok) {
          const data = await res.json()
          setTipoMapeando(tipo)
          setDadosMapeamento({
            colunasPlanilha: data.colunas_planilha || [],
            camposBanco: data.campos_banco || {},
            sugestao: data.mapeamento_sugerido || {},
          })
          setModalOpen(true)
        }
      } catch (err) {
        console.error('Erro ao analisar cabeçalho:', err)
      }
    }
  }

  const handleConfirmarMapeamento = (mapeamentoConfirmado) => {
    const mapaAtualizado = {
      ...mapeamentosDefinidos,
      [tipoMapeando]: mapeamentoConfirmado,
    }

    setMapeamentosDefinidos(mapaAtualizado)
    sessionStorage.setItem('mapeamento_temp', JSON.stringify(mapaAtualizado))
    setModalOpen(false)
  }

  async function uploadArquivo(url, formData) {
    try {
      const res = await fetch(url, {
        method: 'POST',
        headers: getAuthHeader(), 
        body: formData,
      })
      const data = await res.json()
      return { ok: res.ok, data }
    } catch (err) {
      console.error('Erro no uploadArquivo:', err)
      return { ok: false }
    }
  }

  async function monitorarJob(jobId, tipo) {
    return new Promise(resolve => {
      const interval = setInterval(async () => {
        try {
          const res = await fetch(
            `${API_BASE}/api/casos/status-processamento/${jobId}/?t=${Date.now()}`,
            { headers: getAuthHeader() }
          )
          const data = await res.json()

          if (data.progresso !== undefined && data.progresso !== null) {
            setProgresso(Number(data.progresso))
          }

          // Atualiza apenas o texto inline (mensagemStatus) em vez de acumular no log
          if (data.mensagem) {
            setMensagemStatus(`[${tipo.toUpperCase()}] ${data.mensagem}`)
          }

          if (data.status === 'finalizado' || data.status === 'concluido') {
            clearInterval(interval)
            setProgresso(100)
            setMensagemStatus('')
            setLog(prev => prev + `✔ ${tipo}: Processamento finalizado com sucesso.\n\n`)
            resolve()
          }

          if (data.status === 'erro') {
            clearInterval(interval)
            setMensagemStatus('')
            setLog(prev => prev + `✖ ${tipo}: Erro -> ${data.mensagem}\n\n`)
            resolve()
          }
        } catch (err) {
          console.error('Erro no monitorarJob:', err)
          clearInterval(interval)
          resolve()
        }
      }, 1000)
    })
  }

  async function enviar({ syncAfter = false, geoprocessarAfter = false } = {}) {
    if (pendentes.length === 0) {
      setLog('Selecione pelo menos 1 planilha.')
      return
    }

    setEnviando(true)
    setLog('')
    setMensagemStatus('')
    setProgresso(0)

    let mapaAtivo = {}
    try {
      const salvo = sessionStorage.getItem('mapeamento_temp')
      if (salvo) mapaAtivo = JSON.parse(salvo)
    } catch (e) {
      console.warn('Erro ao ler sessionStorage:', e)
    }

    if (!mapaAtivo || Object.keys(mapaAtivo).length === 0) {
      mapaAtivo = mapeamentosDefinidos || {}
    }

    try {
      for (const [tipo, file] of pendentes) {
        const url = API_BASE + endpoints[tipo]
        const formData = new FormData()
        formData.append(uploadKeyByTipo[tipo], file)

        if (celulaCabecalho.trim()) {
          formData.append('celula_cabecalho', celulaCabecalho.trim())
        }

        const mapeamentoDoTipo =
          mapaAtivo[tipo] ||
          mapaAtivo[uploadKeyByTipo[tipo]] ||
          (tipo === 'casos' ? mapaAtivo['positivos'] : null)

        if (mapeamentoDoTipo && Object.keys(mapeamentoDoTipo).length > 0) {
          const payloadStr = JSON.stringify(mapeamentoDoTipo)
          formData.append('mapeamento', payloadStr)
        }

        setLog(prev => prev + `Enviando arquivo ${tipo} para o servidor...\n`)
        const r = await uploadArquivo(url, formData)

        const jobIdRecebido = r.data?.job_id || r.data?.task_id || r.data?.id || r.data?.jobId

        if (r.ok && jobIdRecebido) {
          setLog(prev => prev + `✔ ${tipo} recebido! Processando...\n`)
          await monitorarJob(jobIdRecebido, tipo)
        } else {
          setLog(prev => prev + `✖ ${tipo} Falha ao iniciar processamento.\n\n`)
        }
      }

      if (syncAfter && geoprocessarAfter) {
        await geoprocessar()
        await sincronizar()
      } else {
        if (geoprocessarAfter) await geoprocessar()
        if (syncAfter) await sincronizar()
      }
    } catch (err) {
      console.error('Erro crítico no envio:', err)
      setLog(prev => prev + `✖ Erro crítico no envio.\n`)
    } finally {
      setEnviando(false)
      setProgresso(100)
      setTimeout(() => setProgresso(0), 2000)
    }
  }

  async function geoprocessar() {
    if (geoprocessando) return
    setGeoprocessando(true)
    setProgresso(0)
    setLog(prev => prev + '\nIniciando geoprocessamento...\n')

    try {
      const res = await fetch(API_BASE + endpoints.geoprocessar, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...getAuthHeader() },
      })
      const data = await res.json()
      const jobId = data.job_id || data.task_id || data.id
      if (jobId) await monitorarJob(jobId, 'Mapa')
    } catch {
      setLog(prev => prev + '\n✖ Erro ao iniciar geoprocessamento\n')
    } finally {
      setGeoprocessando(false)
      setProgresso(100)
      setTimeout(() => setProgresso(0), 2000)
    }
  }

  async function sincronizar() {
    if (sincronizando) return
    setSincronizando(true)
    setProgresso(0)
    setLog(prev => prev + '\nIniciando sincronização geral...\n')
    ultimaMensagem.current = ''

    try {
      const res = await fetch(API_BASE + syncEndpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...getAuthHeader() },
      })
      const data = await res.json()
      const jobId = data.job_id || data.task_id || data.id
      if (jobId) await monitorarJob(jobId, 'Sincronização')
    } catch {
      setLog(prev => prev + '\n✖ Erro ao iniciar sincronização\n')
    } finally {
      setSincronizando(false)
    }
  }

  return (
    <div className="vigiaa-upload">
      <NavBar />

      <div className="vigiaa-card">
  <div className="vigiaa-card__header">
    <div>
      <h2 className="vigiaa-title">Upload de dados</h2>
      <p className="vigiaa-subtitle">
        Envie as planilhas e acompanhe o progresso real.
      </p>
    </div>

    <span className="vigiaa-badge">{pendentes.length} selecionada(s)</span>
  </div>


  <div className="vigiaa-fields">
  {[
    { key: 'casos', label: 'Casos positivos' },
    { key: 'pontos', label: 'Pontos estratégicos' },
    { key: 'focos', label: 'Focos' },
    { key: 'ovitrampas', label: 'Ovitrampas' },
  ].map(({ key, label }) => (
    <div key={key} className="vigiaa-field-wrapper">
      <div className={`vigiaa-field ${arquivos[key] ? 'has-file' : ''}`}>
        <div className="vigiaa-field__header">
          <span className="vigiaa-field__title">{label}</span>
        </div>

        <label className="vigiaa-file-dropzone">
          <input
            type="file"
            name={key}
            accept=".xlsx, .xls, .ods"
            onChange={handleChange}
            disabled={enviando || sincronizando || geoprocessando}
          />
          
          <div className="vigiaa-file-btn">
            <svg 
              width="18" 
              height="18" 
              viewBox="0 0 24 24" 
              fill="none" 
              stroke="currentColor" 
              strokeWidth="2" 
              strokeLinecap="round" 
              strokeLinejoin="round"
            >
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
              <polyline points="14 2 14 8 20 8"></polyline>
              <line x1="12" y1="18" x2="12" y2="12"></line>
              <polyline points="9 15 12 12 15 15"></polyline>
            </svg>
            <span>{arquivos[key] ? 'Alterar planilha' : 'Selecionar arquivo'}</span>
          </div>

          <span className="vigiaa-file-name" title={arquivos[key]?.name || ''}>
            {arquivos[key] ? arquivos[key].name : 'Nenhum arquivo selecionado'}
          </span>
        </label>
      </div>

      {arquivos[key] && (
        <button
          type="button"
          className="vigiaa-btn-remove"
          onClick={() => handleRemoverArquivo(key)}
          disabled={enviando || sincronizando || geoprocessando}
          title="Remover planilha"
        >
          ✕
        </button>
      )}
    </div>
  ))}
</div>

  {/* BOTÕES EM 1 LINHA (3 COLUNAS - SEM GEOPROCESSAMENTO) */}
  <div className="vigiaa-actions">
    <div 
      className="vigiaa-btn-wrapper" 
      data-tooltip="Valida e processa os dados das planilhas selecionadas."
    >
      <button
        type="button"
        className="vigiaa-btn vigiaa-btn--primary"
        onClick={() => enviar({ syncAfter: false })}
        disabled={enviando || sincronizando || geoprocessando}
        title="Valida e processa os dados das planilhas selecionadas."
      >
        {enviando ? 'Processando...' : 'Processar planilhas'}
      </button>
      <span className="vigiaa-info-icon">i</span>
    </div>

    <div 
      className="vigiaa-btn-wrapper" 
      data-tooltip="Executa o processamento completo e atualiza o banco."
    >
      <button
        type="button"
        className="vigiaa-btn vigiaa-btn--outline"
        onClick={() =>
          enviar({ syncAfter: true, geoprocessarAfter: true })
        }
        disabled={enviando || sincronizando || geoprocessando}
        title="Executa o processamento completo e atualiza o banco de dados."
      >
        Processar + sincronizar
      </button>
      <span className="vigiaa-info-icon">i</span>
    </div>

    <div 
      className="vigiaa-btn-wrapper" 
      data-tooltip="Envia os dados já processados para o banco de dados."
    >
      <button
        type="button"
        className="vigiaa-btn vigiaa-btn--ghost"
        onClick={sincronizar}
        disabled={enviando || sincronizando || geoprocessando}
        title="Envia os dados já processados para o banco de dados."
      >
        {sincronizando ? 'Sincronizando...' : 'Sincronizar agora'}
      </button>
      <span className="vigiaa-info-icon">i</span>
    </div>
  </div>

  {(enviando || sincronizando || geoprocessando) && (
    <div className="vigiaa-progress">
      <div
        className="vigiaa-progress__bar"
        style={{ width: `${progresso}%`, transition: 'width 0.4s ease-in-out' }}
      />
    </div>
  )}

  {mensagemStatus && (
    <p style={{ fontSize: '13px', color: '#444', marginTop: '8px', fontWeight: '500' }}>
      {mensagemStatus}
    </p>
  )}

  {log && (
    <div className="vigiaa-log">
      <pre>{log}</pre>
    </div>
  )}
</div>

      {modalOpen && (
        <ModalMapeamento
          open={modalOpen}
          tipo={tipoMapeando}
          colunasPlanilha={dadosMapeamento.colunasPlanilha}
          camposBanco={dadosMapeamento.camposBanco}
          sugestao={dadosMapeamento.sugestao}
          onConfirm={handleConfirmarMapeamento}
          onCancel={handleCancelarMapeamento}
        />
      )}
    </div>
  )
}

function ModalMapeamento({ open, tipo, colunasPlanilha, camposBanco, sugestao, onConfirm, onCancel }) {
  const [dePara, setDePara] = useState({})

  useEffect(() => {
    if (sugestao && Object.keys(sugestao).length > 0) {
      setDePara(sugestao)
    }
  }, [sugestao, open])

  if (!open) return null

  const campos = camposBanco && Object.keys(camposBanco).length > 0 ? camposBanco : {}

  const handleChange = (campoBd, colunaPlanilha) => {
    setDePara(prev => ({
      ...prev,
      [campoBd]: colunaPlanilha === '' ? null : colunaPlanilha,
    }))
  }

  return (
    <div className="modal-overlay">
      <div className="modal-container">
        <div className="modal-header">
          <h3 className="modal-title">Confirmar Mapeamento de Colunas</h3>
          <p className="modal-subtitle">
            Planilha de <strong>{tipo?.toUpperCase()}</strong> — Associe os campos do banco às colunas da planilha:
          </p>
        </div>

        <div className="mapeamento-grid">
          {Object.entries(campos).map(([campoBd, labelAmigavel]) => (
            <div key={campoBd} className="mapeamento-row">
              <label className="field-label" htmlFor={`map-${campoBd}`}>
                <strong>{labelAmigavel}</strong>
              </label>

              <select
                id={`map-${campoBd}`}
                value={dePara[campoBd] || ''}
                onChange={e => handleChange(campoBd, e.target.value)}
                className={dePara[campoBd] ? 'select-mapped' : 'select-empty'}
              >
                <option value="">-- Ignorar / Deixar Nulo --</option>
                {(colunasPlanilha || []).map(col => (
                  <option key={col} value={col}>
                    📄 {col}
                  </option>
                ))}
              </select>
            </div>
          ))}
        </div>

        <div className="modal-actions">
          <button type="button" className="vigiaa-btn vigiaa-btn--ghost" onClick={onCancel}>
            Cancelar
          </button>
          <button
            type="button"
            className="vigiaa-btn vigiaa-btn--primary"
            onClick={() => onConfirm(dePara)}
          >
            Confirmar e Prosseguir
          </button>
        </div>
      </div>
    </div>
  )
}