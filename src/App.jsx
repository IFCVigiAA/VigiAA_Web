import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import './App.css'
import 'leaflet/dist/leaflet.css';
import Home from "../pages/Home";
import Participantes from "../pages/Participantes";
import Sobre from "../pages/Sobre";
import Educação from "../pages/Educacao";
import Estação from "../pages/Estacao";
import Publicações from "../pages/Publicacoes";

function App() {
   // const basePath = import.meta.env.BASE_URL;
  return (
   <Router>
    <Routes>
      <Route path="/" element={<Home/>} />
      <Route path="/participantes" element={<Participantes/>} />
      <Route path="/sobre" element={<Sobre/>} />
      <Route path="/Educação" element={<Educação/>} />
      <Route path="/Estação-meteorologica" element={<Estação/>} />
      <Route path="/Publicações" element={<Publicações/>} />
    </Routes>
   </Router>
  )
}

export default App
