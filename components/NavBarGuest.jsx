import React from 'react';
import { Link } from 'react-router-dom';
import './NavBarGuest.css';

const NavBar = () => {
    return (
        <div className="navbar">
            <div className="NavTitle">
                <Link to="/" className="logo">
                    VigiAA
                </Link>
            </div>
            <div className="NavButtons">
                <Link to="/Login">Login</Link>
                <Link to="/Cadastro">Cadastro</Link>
                <Link to="/Ajuda">Ajuda</Link>
            </div>
        </div>
    );
};

export default NavBar;
