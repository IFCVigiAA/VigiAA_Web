import React from 'react'
import './Login.css'
import NavBar from '../components/NavBar'
import Footer from '../components/Footer'
import { useNavigate } from 'react-router-dom'

const Login = () => {
  const navigate = useNavigate()

  const handleSubmit = (e) => {
    e.preventDefault()
    navigate('/')
  }

  return (
    <div className="page-container">
      <NavBar />
      <div className="loginPage">
        <h1>Login</h1>
        <form className="formularioLogin" onSubmit={handleSubmit}>
          <input type="email" placeholder="Email" required />
          <input type="password" placeholder="Senha" required />
          <button type="submit">Entrar</button>
        </form>
      </div>
      <Footer />
    </div>
  )
}

export default Login
