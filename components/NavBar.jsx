import React, { useEffect, useState, useRef } from 'react';
import { NavLink, useNavigate, useLocation } from 'react-router-dom';
import logoVigiaa from '/logos/logo.svg';
import './NavBar.css';

const NavBar = () => {
  const [showModal, setShowModal] = useState(false);
  const [showMenu, setShowMenu] = useState(false);
  const [isLogged, setIsLogged] = useState(false);
  const [menuPos, setMenuPos] = useState({ top: 60, left: 0 });

  const modalRef = useRef(null);
  const navigate = useNavigate();
  const location = useLocation();

  const toggleModal = () => {
    if (!showModal && modalRef.current) {
      const rect = modalRef.current.getBoundingClientRect();
      setMenuPos({
        top: rect.bottom + 12,
        left: rect.left + rect.width / 2,
      });
    }
    setShowModal((prev) => !prev);
  };

  const toggleMenu = () => setShowMenu((prev) => !prev);

  // Fecha dropdown ao clicar fora
  useEffect(() => {
    function handleClickOutside(event) {
      if (modalRef.current && !modalRef.current.contains(event.target)) {
        setShowModal(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Checagem rápida de Login
  useEffect(() => {
    const token = localStorage.getItem('access') || localStorage.getItem('token');
    setIsLogged(!!token);
  }, [location.pathname]);

  // Função de logout
  const handleLogout = async () => {
    localStorage.removeItem('access');
    localStorage.removeItem('refresh');
    localStorage.removeItem('token');
    sessionStorage.clear();

    try {
      await fetch('/api/casos/logout/', {
        method: 'POST',
        credentials: 'include',
      });
    } catch (e) {
      // Ignora erro
    }

    setIsLogged(false);
    setShowMenu(false);
    navigate('/');
  };

  return (
    <div className="navbar">
      <div className="NavTitle">
        <NavLink to="/" className="logo">
          <img
            src={logoVigiaa}
            alt="Logo VigiAA"
            className="logoNav"
          />
        </NavLink>
      </div>

      <button 
        className="hamburger-menu" 
        onClick={toggleMenu} 
        aria-label={showMenu ? "Fechar Menu" : "Abrir Menu"}
      >
        {showMenu ? '✕' : '☰'}
      </button>

      <div className={`NavButtons ${showMenu ? 'show' : ''}`}>
        <NavLink
          to="/"
          className={({ isActive }) => (isActive ? 'active' : '')}
          onClick={() => setShowMenu(false)}
        >
          Home
        </NavLink>

        <NavLink
          to="/Participantes"
          className={({ isActive }) => (isActive ? 'active' : '')}
          onClick={() => setShowMenu(false)}
        >
          Participantes
        </NavLink>

        <NavLink
          to={isLogged ? '/UploadPlanilhas' : '/Login'}
          className={({ isActive }) => (isActive ? 'active' : '')}
          onClick={() => setShowMenu(false)}
        >
          Importar dados
        </NavLink>

        <div ref={modalRef} style={{ position: 'relative' }}>
          <button
            type="button"
            className="projetosBtn"
            onClick={toggleModal}
          >
            Projetos
          </button>

          {showModal && (
            <div
              className="projetosModal"
              style={{ top: `${menuPos.top}px`, left: `${menuPos.left}px` }}
            >
              <NavLink
                to="/Sobre"
                onClick={() => {
                  setShowModal(false);
                  setShowMenu(false);
                }}
              >
                VigiAA
              </NavLink>
              <NavLink
                to="/SobreApp"
                onClick={() => {
                  setShowModal(false);
                  setShowMenu(false);
                }}
              >
                VigiAA App
              </NavLink>
              <NavLink
                to="/Educação"
                onClick={() => {
                  setShowModal(false);
                  setShowMenu(false);
                }}
              >
                Educação
              </NavLink>
              <NavLink
                to="/Estação-meteorologica"
                onClick={() => {
                  setShowModal(false);
                  setShowMenu(false);
                }}
              >
                Estação Meteorológica
              </NavLink>
            </div>
          )}
        </div>

        <NavLink
          to="/Noticias"
          className={({ isActive }) => (isActive ? 'active' : '')}
          onClick={() => setShowMenu(false)}
        >
          Notícias
        </NavLink>

        <NavLink
          to="/Publicações"
          className={({ isActive }) => (isActive ? 'active' : '')}
          onClick={() => setShowMenu(false)}
        >
          Publicações
        </NavLink>

        {isLogged && (
          <button
            type="button"
            className="projetosBtn"
            onClick={handleLogout}
            style={{ color: '#ff7878' }}
          >
            Sair
          </button>
        )}
      </div>
    </div>
  );
};

export default NavBar;