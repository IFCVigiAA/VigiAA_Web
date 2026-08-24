import React, { useEffect, useState, useRef } from 'react';
import { NavLink, useNavigate, useLocation } from 'react-router-dom';
import './NavBar.css';

const NavBar = () => {
  const [showModal, setShowModal] = useState(false);
  const [showMenu, setShowMenu] = useState(false);
  const [isLogged, setIsLogged] = useState(false);

  const modalRef = useRef(null);
  const navigate = useNavigate();
  const location = useLocation(); // Reavalia a autenticação a cada troca de rota

  const toggleModal = () => setShowModal(prev => !prev);
  const toggleMenu = () => setShowMenu(prev => !prev);

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

  // 🔐 Verifica se há token salvo no navegador sempre que a página/rota muda
  useEffect(() => {
    async function verificarAutenticacao() {
      const token = localStorage.getItem('access') || localStorage.getItem('token');

      // Se não há token, está 100% deslogado
      if (!token) {
        setIsLogged(false);
        return;
      }

      // Se tem token, valida no backend passando o Bearer Token
      try {
        const authHeader = token.startsWith('Bearer ') ? token : `Bearer ${token}`;
        const res = await fetch('/api/casos/me/', {
          headers: {
            'Authorization': authHeader,
          },
          credentials: 'include',
        });

        if (res.ok) {
          setIsLogged(true);
        } else {
          // Se o backend recusar o token por expiração
          setIsLogged(false);
        }
      } catch (err) {
        // Fallback: se houver token local, considera logado para renderizar o botão
        setIsLogged(!!token);
      }
    }

    verificarAutenticacao();
  }, [location.pathname]); // Executa sempre que a URL mudar (ex: ao sair do /Login para /UploadPlanilhas)

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
      // Ignora erro se rota não existir
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

        {/* Direciona para Upload se logado, ou Login se deslogado */}
        <NavLink
          to={isLogged ? '/UploadPlanilhas' : '/Login'}
          className={({ isActive }) => (isActive ? 'active' : '')}
          onClick={() => setShowMenu(false)}
        >
          Upload dados
        </NavLink>

        {/* Dropdown de Projetos */}
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

        {isLogged && (
          <button
            type="button"
            className="projetosBtn"
            onClick={handleLogout}
            style={{ color: '#ff7878'}}
          >
            Sair
          </button>
        )}
      </div>
    </div>
  );
};

export default NavBar;