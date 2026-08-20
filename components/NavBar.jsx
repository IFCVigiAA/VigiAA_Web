import React, { useEffect, useState, useRef } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import './NavBar.css';

const NavBar = () => {
  const [showModal, setShowModal] = useState(false);
  const [showMenu, setShowMenu] = useState(false);
  const [isStaff, setIsStaff] = useState(false);
  const [carregando, setCarregando] = useState(true);

  const modalRef = useRef(null);
  const navigate = useNavigate();

  const toggleModal = () => setShowModal(prev => !prev);
  const toggleMenu = () => setShowMenu(prev => !prev);

  // Fecha o dropdown de projetos ao clicar fora dele
  useEffect(() => {
    function handleClickOutside(event) {
      if (modalRef.current && !modalRef.current.contains(event.target)) {
        setShowModal(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // 🔐 Verifica a sessão do usuário no backend ou via JWT
  useEffect(() => {
  async function carregarUsuario() {
    const token = localStorage.getItem('access') || localStorage.getItem('token');

    // Se não tem token no localStorage, já define como deslogado na hora
    if (!token) {
      setIsStaff(false);
      setCarregando(false);
      return;
    }

    try {
      const res = await fetch('/api/casos/me/', {
        headers: { Authorization: `Bearer ${token}` },
        credentials: 'include',
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
  }
  setIsStaff(false);
  setShowMenu(false);
  navigate('/');
};

  return (
    <div className="navbar">
      <div className="NavTitle">
        <NavLink to="/" className="logo">
          <img
            src={import.meta.env.BASE_URL + 'logos/logo.svg'}
            alt="Logo VigiAA"
            className="logoNav"
          />
        </NavLink>
      </div>

      <button className="hamburger-menu" onClick={toggleMenu} aria-label="Abrir Menu">
        &#9776;
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

        {/* Se logado, vai direto pro upload; se não, vai pro login */}
        <NavLink
          to={isStaff ? '/UploadPlanilhas' : '/Login'}
          className={({ isActive }) => (isActive ? 'active' : '')}
          onClick={() => setShowMenu(false)}
        >
          Upload dados
        </NavLink>

        {/* Dropdown Projetos */}
        <div ref={modalRef} style={{ position: 'relative' }}>
          <button
            type="button"
            className="projetosBtn"
            onClick={toggleModal}
          >
            Projetos
          </button>

          {showModal && (
            <div className="projetosModal">
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
          to="/Publicações"
          className={({ isActive }) => (isActive ? 'active' : '')}
          onClick={() => setShowMenu(false)}
        >
          Publicações
        </NavLink>

        {/* Botão de Sair condicional */}
        {isStaff && (
          <button
            type="button"
            className="projetosBtn"
            onClick={handleLogout}
            style={{ color: '#ff6b6b' }}
          >
            Sair
          </button>
        )}
      </div>
    </div>
  );
};

export default NavBar;