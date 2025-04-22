import React from 'react'
import './Cadastro.css'
import NavBar from '../components/NavBar'
import Footer from '../components/Footer'
import { useNavigate, Link } from 'react-router-dom'

const Cadastro = () => {
  const navigate = useNavigate()

  const handleSubmit = (e) => {
    e.preventDefault()
    navigate('/')
  }

  return (
    <div className="page-container">
      <NavBar />
      <div className="cadastroPage">
        <h1>Cadastro</h1>
        <form className="formularioCadastro" onSubmit={handleSubmit}>
          <input type="text" placeholder="Nome completo" required />
          <input type="email" placeholder="Email" required />
          <input type="password" placeholder="Senha" required />
          <button type="submit">Cadastrar</button>
          <Link to="/login">Não tem uma conta?</Link>
        </form>
      </div>
      <Footer />
    </div>
  )
}

export default Cadastro