import { useMemo, useState } from 'react'
import './Upload_planilhas.css'

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

function formatResultado(tipo, r) {
  if (!r?.ok) return `${tipo}: (${r?.status ?? 0}) ${r?.erro ?? 'Erro'}`

  const d = r.data || {}
  if (typeof d.resumo === 'string' && d.resumo.trim()) return `${tipo}: ${d.resumo}`

  const ins = d.inseridos
  if (ins != null) return `${tipo}: ${ins} inseridos`

  return `${tipo}: ok`
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

  async function postArquivo(tipo, arquivo) {
    const url = API_BASE + endpoints[tipo]
    const formData = new FormData()
    const key = uploadKeyByTipo[tipo] ?? 'arquivo'
    formData.append(key, arquivo)

    const res = await fetch(url, {
      method: 'POST',
      headers: {
        ...getAuthHeader(),
      },
      body: formData,
    })

    const contentType = res.headers.get('content-type') || ''
    const bodyText = await res.text()
    const isJson = contentType.includes('application/json')

    if (!res.ok) {
      let erro = bodyText || 'Erro'
      if (isJson) {
        try {
          const j = JSON.parse(bodyText)
          erro = j.detail || j.erro || JSON.stringify(j)
        } catch {}
      }
      return { ok: false, status: res.status, erro }
    }

    if (isJson) {
      try {
        const j = JSON.parse(bodyText)
        return { ok: true, status: res.status, data: j }
      } catch {
        return { ok: true, status: res.status, data: {} }
      }
    }

    return { ok: true, status: res.status, data: {} }
  }

  async function sincronizar() {
    setSincronizando(true)
    try {
      const url = API_BASE + syncEndpoint

      const res = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...getAuthHeader(),
        },
        body: JSON.stringify({}),
      })

      const data = await res.json()

      if (!res.ok) {
        alert(`Falha ao sincronizar: ${data.detail || 'Erro'}`)
        return
      }

      alert(`Sincronização OK:\n${data.resumo || 'Concluído'}`)
    } finally {
      setSincronizando(false)
    }
  }

  async function enviar({ syncAfter } = { syncAfter: false }) {
    setEnviando(true)
    try {
      if (pendentes.length === 0) {
        alert('Selecione pelo menos 1 planilha.')
        return
      }

      const resultados = []

      for (const [tipo, file] of pendentes) {
        const r = await postArquivo(tipo, file)
        resultados.push({ tipo, ...r })
      }

      const falhas = resultados.filter(r => !r.ok)
      const okays = resultados.filter(r => r.ok)

      const msgOk = okays.map(r => formatResultado(r.tipo, r)).join('\n')
      const msgFail = falhas.map(r => formatResultado(r.tipo, r)).join('\n')

      if (falhas.length === 0) {
        alert(`Importado com sucesso:\n${msgOk || '-'}`)
        if (syncAfter) await sincronizar()
      } else {
        alert(`Alguns falharam:\n\nOK:\n${msgOk || '-'}\n\nFalhas:\n${msgFail || '-'}`)
      }
    } finally {
      setEnviando(false)
    }
  }

  return (
    <div className="vigiaa-upload">
      <div className="vigiaa-card">
        <div className="vigiaa-card__header">
          <div>
            <h2 className="vigiaa-title">Upload de dados</h2>
            <p className="vigiaa-subtitle">Envie as planilhas e rode o sincronizador sem sair da tela.</p>
          </div>
          <span className="vigiaa-badge">{pendentes.length} selecionada(s)</span>
        </div>

        <div className="vigiaa-fields">
          <label className="vigiaa-field">
            <span>Casos positivos</span>
            <input type="file" name="casos" onChange={handleChange} accept=".xlsx,.xls" />
          </label>

          <label className="vigiaa-field">
            <span>Pontos estratégicos</span>
            <input type="file" name="pontos" onChange={handleChange} accept=".xlsx,.xls" />
          </label>

          <label className="vigiaa-field">
            <span>Focos</span>
            <input type="file" name="focos" onChange={handleChange} accept=".xlsx,.xls" />
          </label>

          <label className="vigiaa-field">
            <span>Armadilhas</span>
            <input type="file" name="armadilhas" onChange={handleChange} accept=".xlsx,.xls" />
          </label>
        </div>

        <div className="vigiaa-actions">
          <button className="vigiaa-btn vigiaa-btn--primary" onClick={() => enviar({ syncAfter: false })} disabled={enviando || sincronizando}>
            {enviando ? 'Processando...' : 'Processar planilhas'}
          </button>

          <button className="vigiaa-btn vigiaa-btn--outline" onClick={() => enviar({ syncAfter: true })} disabled={enviando || sincronizando}>
            {enviando ? 'Processando...' : 'Processar + sincronizar'}
          </button>

          <button className="vigiaa-btn vigiaa-btn--ghost" onClick={sincronizar} disabled={enviando || sincronizando}>
            {sincronizando ? 'Sincronizando...' : 'Sincronizar agora'}
          </button>
        </div>
      </div>
    </div>
  )
}