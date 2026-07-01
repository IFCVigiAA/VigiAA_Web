#!/bin/bash

echo "🚀 Iniciando o ecossistema do projeto..."

# 1. Iniciar o Django Backend em segundo plano
echo "-> Iniciando Django Backend..."
cd vigiaa-backend
source venv/bin/activate
python manage.py runserver &
BACKEND_PID=$! # Guarda o ID do processo do Django

# 2. Iniciar o Celery em segundo plano
echo "-> Iniciando Celery Worker..."
celery -A vigiaa worker --loglevel=warning &
CELERY_PID=$! # Guarda o ID do processo do Celery

# 3. Voltar para a raiz e iniciar o Frontend (Vite/NPM)
echo "-> Iniciando Frontend..."
cd ..
npm run dev &
FRONTEND_PID=$! # Guarda o ID do processo do NPM

# Função para derrubar todos os servidores juntos quando você der Ctrl+C
trap ctrl_c INT
function ctrl_c() {
        echo -e "\n🛑 Desligando todos os serviços..."
        kill $BACKEND_PID
        kill $CELERY_PID
        kill $FRONTEND_PID
        exit
}

# Mantém o terminal ativo para você ver os logs combinados
wait