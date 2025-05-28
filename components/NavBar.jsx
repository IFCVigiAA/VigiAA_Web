import React, { useState } from 'react'
import { NavLink } from 'react-router-dom'
import './NavBar.css'

const NavBar = () => {
  const [showModal, setShowModal] = useState(false)

  const toggleModal = () => {
    setShowModal(!showModal)
  }

  return (
    <div className="navbar">
      <div className="NavTitle">
        <NavLink to="/" className="logo">
          <img src={import.meta.env.BASE_URL + 'logos/logo.svg'} alt="Logo VigiAA" className="logoNav" />
        </NavLink>
      </div>
      <div className="NavButtons">
        <NavLink to="/" className={({ isActive }) => isActive ? 'active' : ''}>
          Home
        </NavLink>
        <NavLink to="/Participantes" className={({ isActive }) => isActive ? 'active' : ''}>
          Participantes
        </NavLink>
        
        <button className="projetosBtn" onClick={toggleModal}>
          Projetos
        </button>
        {showModal && (
          <div className="projetosModal">
            <a href="/Sobre">VigiAA</a>
            <a href="/Educação">Educação</a>
            <a href="/Estação-meteorologica">Estacao Meteorológica</a>
          </div>
        )}
        <NavLink to="/Publicações" className={({ isActive }) => isActive ? 'active' : ''}>
          Publicações
        </NavLink>
      </div>
    </div>
  )
}

export default NavBar
