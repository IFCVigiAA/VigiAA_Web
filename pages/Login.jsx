import { useState } from "react";
import "./Login.css";

export default function Login() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  async function handleLogin(e) {
    e.preventDefault();
    setError("");

    try {
      const response = await fetch("http://127.0.0.1:8000/api/token/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ username, password })
      });

      if (!response.ok) {
        throw new Error("Credenciais inválidas");
      }

      const data = await response.json();
      localStorage.setItem("access", data.access);
      localStorage.setItem("refresh", data.refresh);

      window.location.href = "/UploadPlanilhas";
    } catch (err) {
      setError("Usuário ou senha incorretos");
    }
  }

  return (
    <div className="login-container">
      <form className="login-box" onSubmit={handleLogin}>
        <h2>Login Administrativo</h2>

        <input
          type="text"
          placeholder="Usuário"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          required
        />

        <input
          type="password"
          placeholder="Senha"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />

        {error && <span className="error">{error}</span>}

        <button type="submit">Entrar</button>
      </form>
    </div>
  );
}