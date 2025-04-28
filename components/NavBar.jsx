import React from 'react';
import { Link } from 'react-router-dom';
import './NavBar.css';

const NavBar = () => {
    return (
        <div className="navbar">
            <div className="NavTitle">
                <Link to="/" className="logo">
                    VigiAA
                </Link>
            </div>
            <div className="NavButtons">
                <Link to="/Participantes">Participantes</Link>
                <Link to="/Sobre">Sobre</Link>
            </div>
        </div>
    );
};

export default NavBar;
