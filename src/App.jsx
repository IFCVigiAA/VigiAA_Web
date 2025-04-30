import { BrowserRouter as Router, Routes, Route, Link } from "react-router-dom";
import './App.css'
import Home from "../pages/Home";
import Participantes from "../pages/Participantes";
import Sobre from "../pages/Sobre";
import Educação from "../pages/Educacao";

function App() {
  return (
   <Router>
    <Routes>
      <Route path="/" element={<Home/>} />
      <Route path="/participantes" element={<Participantes/>} />
      <Route path="/sobre" element={<Sobre/>} />
      <Route path="/Educação" element={<Educação/>} />
    </Routes>
   </Router>
  )
}

export default App