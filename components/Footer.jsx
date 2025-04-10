import './Footer.css'

function Footer() {
  return (
    <footer className="footer">
      <p className="footerTitle">Colaboradores</p>
      
      <div className="footerImgs">
        <div className="imgBox"><img src="logo_VigiAA.png" alt="Logo VigiAA" /></div>
        <div className="imgBox"><img src="logo_ifc.png" alt="Logo IFC" /></div>
        <div className="imgBox"><img src="logo_fapesc.png" alt="Logo Fapesc" /></div>
        <div className="imgBox"><img src="vigilancia_sanitaria.png" alt="Vigilância Sanitária" /></div>
        <div className="imgBox"><img src="logo_prefeitura.png" alt="Prefeitura" /></div>
      </div>

      <div className="footerCopyright">
        © VigiAA 2025 - Todos os direitos reservados
      </div>
    </footer>
  )
}

export default Footer
