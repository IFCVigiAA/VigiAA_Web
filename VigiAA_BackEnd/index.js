import express from 'express'
import cors from 'cors'
import jwt from 'jsonwebtoken'

const app = express()
app.use(cors())
app.use(express.json())

const SECRET_KEY = 'chave-secreta-vigiaa'

// Simulando banco de dados
const usuarios = [
  { id: 1, email: 'admin@vigiaa.com', senha: '1234' }
]

// Rota de login
app.post('/login', (req, res) => {
  const { email, senha } = req.body
  const usuario = usuarios.find(u => u.email === email && u.senha === senha)

  if (!usuario) {
    return res.status(401).json({ erro: 'Credenciais inválidas' })
  }

  const token = jwt.sign({ id: usuario.id, email: usuario.email }, SECRET_KEY, {
    expiresIn: '1h'
  })

  res.json({ token })
})

// Middleware para verificar o token
function autenticarToken(req, res, next) {
  const authHeader = req.headers['authorization']
  const token = authHeader && authHeader.split(' ')[1]

  if (!token) return res.sendStatus(401)

  jwt.verify(token, SECRET_KEY, (err, user) => {
    if (err) return res.sendStatus(403)
    req.user = user
    next()
  })
}

// Rota protegida
app.get('/dashboard', autenticarToken, (req, res) => {
  res.json({ mensagem: `Bem-vindo, ${req.user.email}!` })
})

app.listen(3001, () => {
  console.log('Servidor rodando na porta 3001')
})
