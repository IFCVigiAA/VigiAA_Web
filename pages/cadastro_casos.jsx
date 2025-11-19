import { useState, useEffect } from "react";

export default function Casos() {
  const [casos, setCasos] = useState([]);

  useEffect(() => {
    fetch("http://localhost:8000/api/casos/")
      .then(r => r.json())
      .then(setCasos);
  }, []);

  return (
    <div className="p-4">
      <h1 className="text-xl font-bold mb-4">Casos</h1>
      <ul>
        {casos.map(caso => (
          <li key={caso.id}>
            {caso.cidade} — {caso.quantidade} casos
          </li>
        ))}
      </ul>
    </div>
  );
}
