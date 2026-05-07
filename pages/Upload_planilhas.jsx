import { useMemo, useState, useRef } from 'react'
import './Upload_planilhas.css'
import NavBar from '../components/NavBar';

const API_BASE = 'http://127.0.0.1:8000'

const endpoints = {
  focos: '/api/casos/upload/focos/',
  armadilhas: '/api/casos/upload/armadilhas/',
  pontos: '/api/casos/upload/pontos/',
  casos: '/api/casos/upload/positivos/',
  geoprocessar: '/api/casos/geoprocessar-positivos/',
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

  const [enviando, setEnviando] = useState(false)
  const [sincronizando, setSincronizando] = useState(false)
  const [geoprocessando, setGeoprocessando] = useState(false)
  const [progresso, setProgresso] = useState(0)
  const [log, setLog] = useState('')

  const ultimaMensagem = useRef('')

  const pendentes = useMemo(
    () => Object.entries(arquivos).filter(([_, file]) => !!file),
    [arquivos]
  )

  function handleChange(e) {
    const file = e.target.files?.[0] ?? null
    setArquivos(prev => ({ ...prev, [e.target.name]: file }))
  }

  function getAuthHeader() {
    const token = localStorage.getItem('access')
    if (!token) return {}
    return { Authorization: `Bearer ${token}` }
  }

  function uploadArquivo(url, formData) {
    return new Promise((resolve) => {
      const xhr = new XMLHttpRequest()
      xhr.open('POST', url)
      const headers = getAuthHeader()
      Object.keys(headers).forEach(k => xhr.setRequestHeader(k, headers[k]))
      xhr.onload = () => {
        try {
          const json = JSON.parse(xhr.responseText)
          resolve({ ok: xhr.status < 400, data: json })
        } catch {
          resolve({ ok: false })
        }
      }
      xhr.send(formData)
    })
  }

  async function monitorarJob(jobId, tipo) {
    return new Promise((resolve) => {
      const interval = setInterval(async () => {
        try {
          const res = await fetch(`${API_BASE}/api/casos/status-processamento/${jobId}/`, {
            headers: getAuthHeader()
          })
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
        } catch (e) {
          clearInterval(interval)
          resolve()
        }
      }, 2000)
    })
  }

  async function enviar({ syncAfter } = { syncAfter: false }) {
    if (pendentes.length === 0) {
      setLog('Selecione pelo menos 1 planilha.')
      return
    }

    setEnviando(true)
    setLog('')
    setProgresso(0)

    try {
      for (const [tipo, file] of pendentes) {
        const url = API_BASE + endpoints[tipo]
        const formData = new FormData()
        formData.append(uploadKeyByTipo[tipo], file)

        setLog(prev => prev + `Enviando arquivo ${tipo} para o servidor...\n`)
        
        const r = await uploadArquivo(url, formData)

        if (r.ok && r.data.job_id) {
          setLog(prev => prev + `✔ ${tipo} recebido! Iniciando processamento...\n`)
          await monitorarJob(r.data.job_id, tipo)
        } else {
          setLog(prev => prev + `✖ ${tipo} Falha ao enviar arquivo.\n\n`)
        }
      }

      if (syncAfter) {
        await sincronizar()
      }
    } catch (error) {
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
    setLog(prev => prev + '\nIniciando geoprocessamento dos endereços...\n')

    try {
      const res = await fetch(API_BASE + endpoints.geoprocessar, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...getAuthHeader(),
        },
      })
      const data = await res.json()
      if (data.job_id) {
        await monitorarJob(data.job_id, 'Mapa')
      } else {
        setLog(prev => prev + `✔ ${data.message || 'Solicitação enviada!'}\n`)
      }
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
        headers: {
          'Content-Type': 'application/json',
          ...getAuthHeader(),
        },
      })
      const data = await res.json()
      if (data.job_id) {
        await monitorarJob(data.job_id, 'Sincronização')
      }
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
            <p className="vigiaa-subtitle">Envie as planilhas e acompanhe o progresso real.</p>
          </div>
          <span className="vigiaa-badge">{pendentes.length} selecionada(s)</span>
        </div>

        <div className="vigiaa-fields">
          <label className="vigiaa-field">
            <span>Casos positivos</span>
            <input type="file" name="casos" onChange={handleChange} disabled={enviando} />
          </label>
          <label className="vigiaa-field">
            <span>Pontos estratégicos</span>
            <input type="file" name="pontos" onChange={handleChange} disabled={enviando} />
          </label>
          <label className="vigiaa-field">
            <span>Focos</span>
            <input type="file" name="focos" onChange={handleChange} disabled={enviando} />
          </label>
          <label className="vigiaa-field">
            <span>Armadilhas</span>
            <input type="file" name="armadilhas" onChange={handleChange} disabled={enviando} />
          </label>
        </div>

        <div className="vigiaa-actions">
          <button
            className="vigiaa-btn vigiaa-btn--primary"
            onClick={() => enviar({ syncAfter: false })}
            disabled={enviando || sincronizando || geoprocessando}
          >
            {enviando ? 'Processando...' : 'Processar planilhas'}
          </button>

          <button
            className="vigiaa-btn vigiaa-btn--map"
            onClick={geoprocessar}
            disabled={enviando || sincronizando || geoprocessando}
          >
            {geoprocessando ? 'Geocodificando...' : 'Geoprocessar pontos'}
          </button>

          <button
            className="vigiaa-btn vigiaa-btn--outline"
            onClick={() => enviar({ syncAfter: true })}
            disabled={enviando || sincronizando || geoprocessando}
          >
            Processar + sincronizar
          </button>

          <button
            className="vigiaa-btn vigiaa-btn--ghost"
            onClick={sincronizar}
            disabled={enviando || sincronizando || geoprocessando}
          >
            {sincronizando ? 'Sincronizando...' : 'Sincronizar agora'}
          </button>
        </div>

        {(enviando || sincronizando || geoprocessando) && (
          <div className="vigiaa-progress">
            <div className="vigiaa-progress__bar" style={{ width: `${progresso}%` }} />
          </div>
        )}

        {log && (
          <div className="vigiaa-log">
            <pre>{log}</pre>
          </div>
        )}
      </div>
    </div>
  )
}