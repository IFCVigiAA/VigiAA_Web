import { useMemo, useState, useRef } from 'react'
import './Upload_planilhas.css'
import NavBar from '../components/NavBar';
const API_BASE = 'http://127.0.0.1:8000'

const endpoints = {
  focos: '/api/casos/upload/focos/',
  armadilhas: '/api/casos/upload/armadilhas/',
  pontos: '/api/casos/upload/pontos/',
  casos: '/api/casos/upload/positivos/',
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
  const [progresso, setProgresso] = useState(0)
  const [log, setLog] = useState('')

  const ultimaMensagem = useRef('')
  const fakeBar = useRef(null)

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

  function iniciarFake() {

    let valor = 0

    fakeBar.current = setInterval(() => {

      valor += Math.random() * 5

      if (valor > 90) valor = 90

      setProgresso(Math.floor(valor))

    }, 400)

  }

  function finalizarFake() {

    if (fakeBar.current) {
      clearInterval(fakeBar.current)
      fakeBar.current = null
    }

    setProgresso(100)

    setTimeout(() => {
      setProgresso(0)
    }, 700)

  }

  function uploadArquivo(url, formData) {

    return new Promise((resolve) => {

      const xhr = new XMLHttpRequest()

      xhr.open('POST', url)

      const headers = getAuthHeader()

      Object.keys(headers).forEach(k =>
        xhr.setRequestHeader(k, headers[k])
      )

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

  async function enviar({ syncAfter } = { syncAfter: false }) {

    setEnviando(true)
    setLog('')
    setProgresso(0)

    iniciarFake()

    try {

      if (pendentes.length === 0) {
        setLog('Selecione pelo menos 1 planilha.')
        return
      }

      for (const [tipo, file] of pendentes) {

        const url = API_BASE + endpoints[tipo]

        const formData = new FormData()

        formData.append(uploadKeyByTipo[tipo], file)

        setLog(prev => prev + `Enviando ${tipo}...\n`)

        const r = await uploadArquivo(url, formData)

        if (r.ok) {

          const inseridos = r.data?.inseridos ?? 0

          setLog(prev => prev + `✔ ${tipo}: ${inseridos} inseridos\n\n`)

        } else {

          setLog(prev => prev + `✖ ${tipo}: erro\n\n`)

        }

      }

      finalizarFake()

      if (syncAfter) {
        await sincronizar()
      }

    } finally {

      setEnviando(false)

    }

  }

  async function sincronizar() {
    if (sincronizando) return
    setSincronizando(true)
    setProgresso(0)

    setLog(prev => prev + '\nIniciando sincronização...\n')

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

      const jobId = data.job_id

      const interval = setInterval(async () => {

        try {

          const statusRes = await fetch(
            `${API_BASE}/api/casos/status-processamento/${jobId}/`,
            { headers: getAuthHeader() }
          )

          const statusData = await statusRes.json()

          if (statusData.progresso !== undefined) {
            setProgresso(statusData.progresso)
          }

          if (
            statusData.mensagem &&
            statusData.mensagem !== ultimaMensagem.current
          ) {

            setLog(prev => prev + statusData.mensagem + '\n')

            ultimaMensagem.current = statusData.mensagem

          }

          if (statusData.status === 'concluido') {

            clearInterval(interval)

            setProgresso(100)

            setLog(prev => prev + '\n✔ Sincronização concluída\n')

            setSincronizando(false)

          }

          if (statusData.status === 'erro') {

            clearInterval(interval)

            setLog(prev => prev + '\n✖ Erro na sincronização\n')

            setSincronizando(false)

          }

        } catch {

          clearInterval(interval)

          setLog(prev => prev + '\n✖ Erro ao consultar status\n')

          setSincronizando(false)

        }

      }, 2000)

    } catch {

      setLog(prev => prev + '\n✖ Erro ao iniciar sincronização\n')

      setSincronizando(false)

    }

  }

  return (
    <>
    
    <div className="vigiaa-upload">
      <NavBar />
      <div className="vigiaa-card">

        <div className="vigiaa-card__header">

          <div>

            <h2 className="vigiaa-title">Upload de dados</h2>

            <p className="vigiaa-subtitle">
              Envie as planilhas e acompanhe o progresso.
            </p>

          </div>

          <span className="vigiaa-badge">
            {pendentes.length} selecionada(s)
          </span>

        </div>

        <div className="vigiaa-fields">

          <label className="vigiaa-field">
            <span>Casos positivos</span>
            <input type="file" name="casos" onChange={handleChange} />
          </label>

          <label className="vigiaa-field">
            <span>Pontos estratégicos</span>
            <input type="file" name="pontos" onChange={handleChange} />
          </label>

          <label className="vigiaa-field">
            <span>Focos</span>
            <input type="file" name="focos" onChange={handleChange} />
          </label>

          <label className="vigiaa-field">
            <span>Armadilhas</span>
            <input type="file" name="armadilhas" onChange={handleChange} />
          </label>

        </div>

        <div className="vigiaa-actions">

          <button
            className="vigiaa-btn vigiaa-btn--primary"
            onClick={() => enviar({ syncAfter: false })}
            disabled={enviando || sincronizando}
          >
            {enviando ? 'Processando...' : 'Processar planilhas'}
          </button>

          <button
            className="vigiaa-btn vigiaa-btn--outline"
            onClick={() => enviar({ syncAfter: true })}
            disabled={enviando || sincronizando}
          >
            Processar + sincronizar
          </button>

          <button
            className="vigiaa-btn vigiaa-btn--ghost"
            onClick={sincronizar}
            disabled={enviando || sincronizando}
          >
            {sincronizando ? 'Sincronizando...' : 'Sincronizar agora'}
          </button>

        </div>

        {(enviando || sincronizando) && (

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

    </div>
    </>
  )

}