import { BrowserRouter as Router, Routes, Route, Link } from "react-router-dom";
import './App.css'
import Home from "../pages/Home";
import Cadastro from "../pages/Cadastro";
import Login from "../pages/Login";
import Participantes from "../pages/Participantes";
import Sobre from "../pages/Sobre";


function App() {
  return (
   <Router>
    <Routes>
      <Route path="/" element={<Home/>} />
      <Route path="/Cadastro" element={<Cadastro/>} />
      <Route path="/Login" element={<Login/>} />
      <Route path="/Participantes" element={<Participantes/>} />
      <Route path="/Sobre" element={<Sobre/>} />
    </Routes>
   </Router>
  )
}

export default App