import React from 'react'
import { NavLink } from 'react-router-dom'
import './NavBar.css'

const NavBar = () => {
  return (
    <div className="navbar">
      <div className="NavTitle">
        <NavLink to="/" className="logo">
          VigiAA
        </NavLink>
      </div>
      <div className="NavButtons">
        <NavLink to="/" className={({ isActive }) => isActive ? 'active' : ''}>
          Home
        </NavLink>
        <NavLink to="/Participantes" className={({ isActive }) => isActive ? 'active' : ''}>
          Participantes
        </NavLink>
        <NavLink to="/Educação" className={({ isActive }) => isActive ? 'active' : ''}>
          Educação
        </NavLink>
        <NavLink to="/Sobre" className={({ isActive }) => isActive ? 'active' : ''}>
          Sobre
        </NavLink>
      </div>
    </div>
  )
}

export default NavBar
