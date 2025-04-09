import react from 'react';
import "./NavBar.css"

const NavBar = () => {
    return(
    <>
        <div class="navbar">
            <div class="NavTitle">
                <p class="logo">
                <span class="span1">Vigi</span><span class="span2">AA</span>
                </p>
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