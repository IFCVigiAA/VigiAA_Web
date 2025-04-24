import React, { useState } from 'react'
import './Login.css'
import NavBar from '../components/NavBarGuest'
import Footer from '../components/Footer'
import { useNavigate, Link } from 'react-router-dom'

const Login = () => {
  const [email, setEmail] = useState('')
  const [senha, setSenha] = useState('')
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()

    try {
      const response = await fetch('http://localhost:3001/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          usuario: email, // no backend criamos o campo como "usuario"
          senha: senha
        })
      })

      const data = await response.json()

      if (response.ok) {
        localStorage.setItem('token', data.token)
        alert('Login feito com sucesso!')
        navigate('/')
      } else {
        alert(data.message || 'Usuário ou senha inválidos.')
      }
    } catch (err) {
      alert('Erro ao conectar com o servidor.')
    }
  }

  return (
    <div className="page-container">
      <NavBar />
      <div className="loginPage">
        <h1>Login</h1>
        <form className="formularioLogin" onSubmit={handleSubmit}>
          <input
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
          <input
            type="password"
            placeholder="Senha"
            value={senha}
            onChange={(e) => setSenha(e.target.value)}
            required
          />
          <button type="submit">Entrar</button>
          <Link to="/cadastro">Já tem uma conta?</Link>
        </form>
      </div>
      <Footer />
    </div>
  )
}

export default Login
