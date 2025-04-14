import react from 'react';
import { Link } from 'react-router-dom';
import "./NavBar.css"

const NavBar = () => {
    return (
        <>
            <div class="navbar">
                <div class="NavTitle">
                    <Link to="/" class="logo">
                        VigiAA
                    </Link>
                </div>
                <div class="NavButtons">
                    <Link to="/Login">Login</Link>
                    <Link to="/Participantes">Participantes</Link>
                    <Link to="/Sobre">Sobre</Link>
                </div>
            </div>
        </>
    )
}

export default NavBar
