import { useState } from 'react'

export default function UploadPlanilhas() {
  const [arquivos, setArquivos] = useState({})

  function handleChange(e) {
    setArquivos({
      ...arquivos,
      [e.target.name]: e.target.files[0]
    })
  }

  async function enviar() {
    const formData = new FormData()
    formData.append('casos', arquivos.casos)
    formData.append('pontos', arquivos.pontos)
    formData.append('focos', arquivos.focos)
    formData.append('armadilhas', arquivos.armadilhas)

    const res = await fetch('http://localhost:8000/api/upload-planilhas/', {
      method: 'POST',
      body: formData,
      credentials: 'include'
    })

    const data = await res.json()
    alert(data.sucesso ? 'Importado com sucesso' : data.erro)
  }

  return (
    <>
      <input type="file" name="casos" onChange={handleChange} />
      <input type="file" name="pontos" onChange={handleChange} />
      <input type="file" name="focos" onChange={handleChange} />
      <input type="file" name="armadilhas" onChange={handleChange} />
      <button onClick={enviar}>Processar Planilhas</button>
    </>
  )
}
