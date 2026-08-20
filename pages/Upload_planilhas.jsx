import { useMemo, useState, useRef, useEffect } from 'react'
import './Upload_planilhas.css'
import NavBar from '../components/NavBar'

const API_BASE = ''

const endpoints = {
  focos: '/api/casos/upload/focos/',
  armadilhas: '/api/casos/upload/armadilhas/',
  pontos: '/api/casos/upload/pontos/',
  casos: '/api/casos/upload/positivos/',
  geoprocessar: '/api/casos/geoprocessar-positivos/',
  extrairCabecalho: '/api/casos/extrair-cabecalho/',
}

const syncEndpoint = '/api/casos/sincronizar/'

const uploadKeyByTipo = {
  casos: 'positivos',
  focos: 'focos',
  armadilhas: 'armadilhas',
  pontos: 'pontos',
}

export default function UploadPlanilhas() {
  const [arquivos, setArquivos] = useState({
    casos: null,
    pontos: null,
    focos: null,
    armadilhas: null,
  })

  const [celulaCabecalho, setCelulaCabecalho] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [sincronizando, setSincronizando] = useState(false)
  const [geoprocessando, setGeoprocessando] = useState(false)
  const [progresso, setProgresso] = useState(0)
  const [log, setLog] = useState('')

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

  function getAuthHeader() {
    const token = localStorage.getItem('access') || localStorage.getItem('token')
    if (!token) return {}
    const authValue = token.startsWith('Bearer ') ? token : `Bearer ${token}`
    return { Authorization: authValue }
  }

  // Detecta a seleção de arquivo e abre o modal para analisar
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

  // Salva o de-para isolado no estado e no sessionStorage para cada tipo de planilha
  const handleConfirmarMapeamento = (mapeamentoConfirmado) => {
    console.log(`📌 SALVANDO MAPEAMENTO DO MODAL [${tipoMapeando}]:`, mapeamentoConfirmado)

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
        headers: getAuthHeader(), // Apenas Authorization, sem forçar Content-Type
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
            `${API_BASE}/api/casos/status-processamento/${jobId}/`,
            { headers: getAuthHeader() }
          )
          const data = await res.json()

          if (data.progresso !== undefined) setProgresso(data.progresso)

          if (data.mensagem && data.mensagem !== ultimaMensagem.current) {
            setLog(prev => prev + `[${tipo.toUpperCase()}] ${data.mensagem}\n`)
            ultimaMensagem.current = data.mensagem
          }

          if (data.status === 'finalizado' || data.status === 'concluido') {
            clearInterval(interval)
            setLog(prev => prev + `✔ ${tipo}: Processamento finalizado.\n\n`)
            resolve()
          }

          if (data.status === 'erro') {
            clearInterval(interval)
            setLog(prev => prev + `✖ ${tipo}: Erro -> ${data.mensagem}\n\n`)
            resolve()
          }
        } catch {
          clearInterval(interval)
          resolve()
        }
      }, 2000)
    })
  }

  // Função enviar genérica e compatível com todos os tipos de planilha
  async function enviar({ syncAfter = false, geoprocessarAfter = false } = {}) {
    if (pendentes.length === 0) {
      setLog('Selecione pelo menos 1 planilha.')
      return
    }

    setEnviando(true)
    setLog('')
    setProgresso(0)

    // 1. Resgata o mapa geral do sessionStorage ou do estado
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

        // 2. Busca exata do mapeamento do tipo atual
        const mapeamentoDoTipo =
          mapaAtivo[tipo] ||
          mapaAtivo[uploadKeyByTipo[tipo]] ||
          (tipo === 'casos' ? mapaAtivo['positivos'] : null)

        if (mapeamentoDoTipo && Object.keys(mapeamentoDoTipo).length > 0) {
          const payloadStr = JSON.stringify(mapeamentoDoTipo)
          console.log(`🚀 [FRONTEND] ENVIANDO MAPEAMENTO PARA [${tipo}]:`, payloadStr)
          formData.append('mapeamento', payloadStr)
        } else {
          console.warn(`⚠️ [FRONTEND] NENHUM MAPEAMENTO CUSTOMIZADO PARA [${tipo}] (usará fallback)`)
        }

        setLog(prev => prev + `Enviando arquivo ${tipo} para o servidor...\n`)
        const r = await uploadArquivo(url, formData)

        if (r.ok && r.data?.job_id) {
          setLog(prev => prev + `✔ ${tipo} recebido! Processando...\n`)
          await monitorarJob(r.data.job_id, tipo)
        } else {
          setLog(prev => prev + `✖ ${tipo} Falha ao enviar arquivo.\n\n`)
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
      console.error(err)
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
      if (data.job_id) await monitorarJob(data.job_id, 'Mapa')
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
      if (data.job_id) await monitorarJob(data.job_id, 'Sincronização')
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
          <label className="vigiaa-field">
            <span>Casos positivos</span>
            <input
              type="file"
              name="casos"
              accept=".xlsx, .xls, .ods"
              onChange={handleChange}
              disabled={enviando}
            />
          </label>

          <label className="vigiaa-field">
            <span>Pontos estratégicos</span>
            <input
              type="file"
              name="pontos"
              accept=".xlsx, .xls, .ods"
              onChange={handleChange}
              disabled={enviando}
            />
          </label>

          <label className="vigiaa-field">
            <span>Focos</span>
            <input
              type="file"
              name="focos"
              accept=".xlsx, .xls, .ods"
              onChange={handleChange}
              disabled={enviando}
            />
          </label>

          <label className="vigiaa-field">
            <span>Armadilhas</span>
            <input
              type="file"
              name="armadilhas"
              accept=".xlsx, .xls, .ods"
              onChange={handleChange}
              disabled={enviando}
            />
          </label>
        </div>

        <div className="vigiaa-actions">
          <button
            type="button"
            className="vigiaa-btn vigiaa-btn--primary"
            onClick={() => enviar({ syncAfter: false })}
            disabled={enviando || sincronizando || geoprocessando}
          >
            {enviando ? 'Processando...' : 'Processar planilhas'}
          </button>

          <button
            type="button"
            className="vigiaa-btn vigiaa-btn--map"
            onClick={geoprocessar}
            disabled={enviando || sincronizando || geoprocessando}
          >
            {geoprocessando ? 'Geocodificando...' : 'Geoprocessar pontos'}
          </button>

          <button
            type="button"
            className="vigiaa-btn vigiaa-btn--outline"
            onClick={() =>
              enviar({ syncAfter: true, geoprocessarAfter: true })
            }
            disabled={enviando || sincronizando || geoprocessando}
          >
            Processar + sincronizar
          </button>

          <button
            type="button"
            className="vigiaa-btn vigiaa-btn--ghost"
            onClick={sincronizar}
            disabled={enviando || sincronizando || geoprocessando}
          >
            {sincronizando ? 'Sincronizando...' : 'Sincronizar agora'}
          </button>
        </div>

        {(enviando || sincronizando || geoprocessando) && (
          <div className="vigiaa-progress">
            <div
              className="vigiaa-progress__bar"
              style={{ width: `${progresso}%` }}
            />
          </div>
        )}

        {log && (
          <div className="vigiaa-log">
            <pre>{log}</pre>
          </div>
        )}
      </div>

      {/* MODAL DE MAPEAMENTO DE COLUNAS */}
      {modalOpen && (
        <ModalMapeamento
          open={modalOpen}
          tipo={tipoMapeando}
          colunasPlanilha={dadosMapeamento.colunasPlanilha}
          camposBanco={dadosMapeamento.camposBanco}
          sugestao={dadosMapeamento.sugestao}
          onConfirm={handleConfirmarMapeamento}
          onCancel={() => setModalOpen(false)}
        />
      )}
    </div>
  )
}

// Subcomponente do Modal Interativo
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