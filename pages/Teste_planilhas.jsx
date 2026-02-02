import { useState } from 'react'

const API_BASE = 'http://localhost:8000'

const endpoints = {
  focos: '/api/casos/upload/focos/',
  armadilhas: '/api/casos/upload/armadilhas/',
  pontos: '/api/casos/upload/pontos/',
  casos: '/api/casos/upload/positivos/',
}

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

  function handleChange(e) {
    const file = e.target.files?.[0] ?? null
    setArquivos(prev => ({
      ...prev,
      [e.target.name]: file,
    }))
  }

  async function postArquivo(tipo, arquivo) {
    const url = API_BASE + endpoints[tipo]
    const formData = new FormData()

    const key = uploadKeyByTipo[tipo] ?? 'arquivo'
    formData.append(key, arquivo)

    const res = await fetch(url, {
      method: 'POST',
      body: formData,
      credentials: 'include',
    })

    const contentType = res.headers.get('content-type') || ''
    const bodyText = await res.text()

    const isJson = contentType.includes('application/json')

    if (!res.ok) {
      if (isJson) {
        try {
          const j = JSON.parse(bodyText)
          return { ok: false, status: res.status, erro: j.erro || JSON.stringify(j) }
        } catch {
          return { ok: false, status: res.status, erro: bodyText }
        }
      }

      if (contentType.includes('text/html')) {
        return {
          ok: false,
          status: res.status,
          erro: 'Backend respondeu HTML (provável redirect/login/rota errada). Confira autenticação e URL.',
        }
      }

      return { ok: false, status: res.status, erro: bodyText }
    }

    if (isJson) {
      try {
        const j = JSON.parse(bodyText)
        return { ok: true, status: res.status, data: j }
      } catch {
        return { ok: true, status: res.status, data: { sucesso: true } }
      }
    }

    return { ok: true, status: res.status, data: { sucesso: true, raw: bodyText } }
  }

  async function enviar() {
    setEnviando(true)
    try {
      const pendentes = Object.entries(arquivos).filter(([_, file]) => !!file)

      if (pendentes.length === 0) {
        alert('Selecione pelo menos 1 planilha.')
        return
      }

      const resultados = []

      for (const [tipo, file] of pendentes) {
        if (!endpoints[tipo]) {
          resultados.push({ tipo, ok: false, status: 0, erro: 'Sem endpoint configurado' })
          continue
        }

        const r = await postArquivo(tipo, file)
        resultados.push({ tipo, ...r })
      }

      const falhas = resultados.filter(r => !r.ok)
      const okays = resultados.filter(r => r.ok)

      if (falhas.length === 0) {
        const msg = okays
          .map(r => {
            const inseridos = r.data?.inseridos
            return inseridos != null ? `${r.tipo}: ${inseridos} inseridos` : `${r.tipo}: ok`
          })
          .join('\n')
        alert(`Importado com sucesso:\n${msg}`)
      } else {
        const msgOk = okays.map(r => `${r.tipo}: ok`).join('\n')
        const msgFail = falhas.map(r => `${r.tipo}: (${r.status}) ${r.erro}`).join('\n')
        alert(`Alguns falharam:\n\nOK:\n${msgOk || '-'}\n\nFalhas:\n${msgFail}`)
      }
    } finally {
      setEnviando(false)
    }
  }

  return (
    <div style={{ display: 'grid', gap: 12, maxWidth: 420 }}>
      <label>
        Casos positivos (positivos.xls/xlsx)
        <input type="file" name="casos" onChange={handleChange} accept=".xlsx,.xls" />
      </label>

      <label>
        Pontos estratégicos (pontoEstrategico.xls/xlsx)
        <input type="file" name="pontos" onChange={handleChange} accept=".xlsx,.xls" />
      </label>

      <label>
        Focos (relatoriofocos.xls/xlsx)
        <input type="file" name="focos" onChange={handleChange} accept=".xlsx,.xls" />
      </label>

      <label>
        Armadilhas (armadilha.xls/xlsx)
        <input type="file" name="armadilhas" onChange={handleChange} accept=".xlsx,.xls" />
      </label>

      <button onClick={enviar} disabled={enviando}>
        {enviando ? 'Enviando...' : 'Processar Planilhas'}
      </button>
    </div>
  )
}
