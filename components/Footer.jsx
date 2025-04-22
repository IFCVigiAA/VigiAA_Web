import './Footer.css'

function Footer() {
  return (
    <footer className="footer">
      <p className="footerTitle">Colaboradores</p>
      
      <div className="footerImgs">
        <a href="" target="_blank" rel="noopener noreferrer"><div className="imgBox"><img src="logo_VigiAA.png" alt="Logo VigiAA" /></div></a>
        <a href="https://www.camboriu.ifc.edu.br/" target="_blank" rel="noopener noreferrer"><div className="imgBox"><img src="logo_ifc.png" alt="Logo IFC" /></div></a>
        <a href="https://fapesc.sc.gov.br/" target="_blank" rel="noopener noreferrer"><div className="imgBox"><img src="logo_fapesc.png" alt="Logo Fapesc" /></div></a>
        <a href="https://camboriu.sc.gov.br/vigilancia-sanitaria/" target="_blank" rel="noopener noreferrer"><div className="imgBox"><img src="vigilancia_sanitaria.png" alt="Vigilância Sanitária" /></div></a>
        <a href="https://camboriu.sc.gov.br/" target="_blank" rel="noopener noreferrer"><div className="imgBox"><img src="logo_prefeitura.png" alt="Prefeitura" /></div></a>
      </div>
      <a href="https://mail.google.com/mail/?view=cm&fs=1&to=vigiaa.camboriu@ifc.edu.br" target='_blank'>
      vigiaa.camboriu@ifc.edu.br
      </a>
      <div className="footerCopyright">
        © VigiAA 2025 - Todos os direitos reservados
      </div>
    </footer>
  )
}

export default Footer
