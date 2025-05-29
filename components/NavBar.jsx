import React, { useState } from 'react';
import { NavLink } from 'react-router-dom';
import './NavBar.css';

const NavBar = () => {
  const [showModal, setShowModal] = useState(false);
  const [showMenu, setShowMenu] = useState(false); // Estado para controlar a abertura/fechamento do menu responsivo

  const toggleModal = () => {
    setShowModal(!showModal);
  };

  const toggleMenu = () => { // Função para alternar o estado do menu hamburguer
    setShowMenu(!showMenu);
  };

  return (
    <div className="navbar">
      <div className="NavTitle">
        <NavLink to="/" className="logo">
          <img src={import.meta.env.BASE_URL + 'logos/logo.svg'} alt="Logo VigiAA" className="logoNav" />
        </NavLink>
      </div>

      {/* Botão do menu hamburguer que aparece apenas em telas menores */}
      <button className="hamburger-menu" onClick={toggleMenu}>
        &#9776; {/* Ícone de hamburguer (três linhas) */}
      </button>

      {/* Os botões de navegação e o modal de projetos serão exibidos/ocultados */}
      <div className={`NavButtons ${showMenu ? 'show' : ''}`}> {/* Adiciona a classe 'show' quando o menu está aberto */}
        <NavLink to="/" className={({ isActive }) => isActive ? 'active' : ''} onClick={() => setShowMenu(false)}>
          Home
        </NavLink>
        <NavLink to="/Participantes" className={({ isActive }) => isActive ? 'active' : ''} onClick={() => setShowMenu(false)}>
          Participantes
        </NavLink>
        
        <button className="projetosBtn" onClick={toggleModal}>
          Projetos
        </button>
        {showModal && (
          <div className="projetosModal">
            <a href="/Sobre" onClick={() => setShowMenu(false)}>VigiAA</a>
            <a href="/Educação" onClick={() => setShowMenu(false)}>Educação</a>
            <a href="/Estação-meteorologica" onClick={() => setShowMenu(false)}>Estacao Meteorológica</a>
          </div>
        )}
        <NavLink to="/Publicações" className={({ isActive }) => isActive ? 'active' : ''} onClick={() => setShowMenu(false)}>
          Publicações
        </NavLink>
      </div>
    </div>
  );
};

export default NavBar;