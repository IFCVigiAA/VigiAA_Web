import react from 'react';
import "./NavBar.css"

const NavBar = () => {
    return(
    <>
        <div class="navbar">
            <div class="NavLogo">
                <img src="logo2.png" alt="" />
            </div>
            <div class="NavTitle">
                <p>VigiAA</p>
            </div>
            <div class="NavButtons">
                
                <p>Participantes</p>
                <p>Documentação</p>
                <p>Sobre</p>
            </div>
        </div>
        
    </>
    )
}

export default NavBar