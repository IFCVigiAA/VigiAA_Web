import React, { useEffect, useState } from 'react';
import { NavLink } from 'react-router-dom';
import './NavBar.css';

const NavBar = () => {
  const [showModal, setShowModal] = useState(false);
  const [showMenu, setShowMenu] = useState(false);
  const [isStaff, setIsStaff] = useState(false);
  const [carregando, setCarregando] = useState(true);

  const toggleModal = () => setShowModal(!showModal);
  const toggleMenu = () => setShowMenu(!showMenu);

  // 🔐 pergunta ao backend quem é o usuário
  useEffect(() => {
    async function carregarUsuario() {
      try {
        const res = await fetch('/api/casos/me/', {
          credentials: 'include'
        });

        if (!res.ok) {
          setIsStaff(false);
          return;
        }

        const data = await res.json();
        setIsStaff(!!data.is_staff);
      } catch {
        setIsStaff(false);
      } finally {
        setCarregando(false);
      }
    }

    carregarUsuario();
  }, []);

  return (
    <div className="navbar">
      <div className="NavTitle">
        <NavLink to="/" className="logo">
          <img src={import.meta.env.BASE_URL + 'logos/logo.svg'} alt="Logo VigiAA" className="logoNav" />
        </NavLink>
      </div>

      <button className="hamburger-menu" onClick={toggleMenu}>
        &#9776;
      </button>

      <div className={`NavButtons ${showMenu ? 'show' : ''}`}>
        <NavLink to="/" className={({ isActive }) => isActive ? 'active' : ''} onClick={() => setShowMenu(false)}>
          Home
        </NavLink>

        <NavLink to="/Participantes" className={({ isActive }) => isActive ? 'active' : ''} onClick={() => setShowMenu(false)}>
          Participantes
        </NavLink>

        {/* 🔒 Só aparece se for staff */}
        {!carregando && isStaff && (
          <NavLink
            to="/uploadplanilhas"
            className={({ isActive }) => isActive ? 'active' : ''}
            onClick={() => setShowMenu(false)}
          >
            Upload dados
          </NavLink>
        )}

        <button className="projetosBtn" onClick={toggleModal}>
          Projetos
        </button>

        {showModal && (
          <div className="projetosModal">
            <a href="/Sobre" onClick={() => setShowMenu(false)}>VigiAA</a>
            <a href="/Educação" onClick={() => setShowMenu(false)}>Educação</a>
            <a href="/Estação-meteorologica" onClick={() => setShowMenu(false)}>Estação Meteorológica</a>
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
