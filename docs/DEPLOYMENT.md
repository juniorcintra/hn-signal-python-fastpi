# Guia de Deployment

Este documento descreve como fazer deploy do HN Article Enricher em diferentes ambientes.

## Opções de Deployment

1. [Docker Compose](#docker-compose) - Recomendado para produção simples
2. [Docker Manual](#docker-manual) - Para mais controle
3. [Servidor Tradicional](#servidor-tradicional) - Deploy direto no servidor
4. [Cloud Platforms](#cloud-platforms) - Heroku, Railway, Render, etc.

---

## Docker Compose

### Pré-requisitos
- Docker e Docker Compose instalados
- Arquivo `.env` configurado

### Passos

1. **Configure variáveis de ambiente:**

```bash
cp .env.example .env
# Edite .env com suas configurações
```

2. **Inicie os serviços:**

```bash
docker-compose up -d
```

3. **Verifique saúde:**

```bash
curl http://localhost:8000/health
```

4. **Ver logs:**

```bash
docker-compose logs -f app
```

5. **Parar serviços:**

```bash
docker-compose down
```

### Configuração de Produção

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - API_KEY=${API_KEY}
      - DATABASE_URL=sqlite+aiosqlite:///./data/hn_articles.db
      - RATE_LIMIT_PER_MINUTE=100
      - LOG_LEVEL=WARNING
      - ENVIRONMENT=production
    volumes:
      - ./data:/app/data
    restart: always
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 512M
```

---

## Docker Manual

### Build da Imagem

```bash
docker build -t hn-enricher:latest .
```

### Executar Container

```bash
docker run -d \
  --name hn-enricher \
  -p 8000:8000 \
  -e OPENAI_API_KEY=sk-... \
  -e API_KEY=seu-token \
  -v $(pwd)/data:/app/data \
  hn-enricher:latest
```

### Comandos Úteis

```bash
# Ver logs
docker logs -f hn-enricher

# Parar container
docker stop hn-enricher

# Remover container
docker rm hn-enricher

# Executar comando no container
docker exec -it hn-enricher bash
```

---

## Servidor Tradicional

### Ubuntu/Debian

1. **Instalar Python 3.11+:**

```bash
sudo apt update
sudo apt install python3.11 python3.11-venv python3-pip
```

2. **Clonar repositório:**

```bash
git clone https://github.com/seu-usuario/hn-signal-python-fastpi.git
cd hn-signal-python-fastpi
```

3. **Criar ambiente virtual:**

```bash
python3.11 -m venv .venv
source .venv/bin/activate
```

4. **Instalar dependências:**

```bash
pip install -r requirements.txt
```

5. **Configurar variáveis:**

```bash
cp .env.example .env
nano .env  # Configure suas variáveis
```

6. **Executar migrações:**

```bash
alembic upgrade head
```

7. **Criar serviço systemd:**

```bash
sudo nano /etc/systemd/system/hn-enricher.service
```

```ini
[Unit]
Description=HN Article Enricher
After=network.target

[Service]
Type=simple
User=seu-usuario
WorkingDirectory=/caminho/para/hn-signal-python-fastpi
Environment="PATH=/caminho/para/hn-signal-python-fastpi/.venv/bin"
ExecStart=/caminho/para/hn-signal-python-fastpi/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

8. **Iniciar serviço:**

```bash
sudo systemctl daemon-reload
sudo systemctl enable hn-enricher
sudo systemctl start hn-enricher
sudo systemctl status hn-enricher
```

### Nginx como Reverse Proxy

```nginx
server {
    listen 80;
    server_name seu-dominio.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## Cloud Platforms

### Heroku

1. **Criar Procfile:**

```
web: alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

2. **Deploy:**

```bash
heroku create seu-app
heroku config:set OPENAI_API_KEY=sk-...
heroku config:set API_KEY=seu-token
git push heroku main
```

### Railway

1. **Criar `railway.json`:**

```json
{
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

2. **Deploy via CLI ou GitHub:**

```bash
railway login
railway init
railway up
```

### Render

1. **Criar `render.yaml`:**

```yaml
services:
  - type: web
    name: hn-enricher
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: OPENAI_API_KEY
        sync: false
      - key: API_KEY
        sync: false
      - key: PYTHON_VERSION
        value: 3.11.0
```

2. **Deploy via dashboard ou CLI**

### Google Cloud Run

1. **Build e push da imagem:**

```bash
gcloud builds submit --tag gcr.io/seu-projeto/hn-enricher
```

2. **Deploy:**

```bash
gcloud run deploy hn-enricher \
  --image gcr.io/seu-projeto/hn-enricher \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars OPENAI_API_KEY=sk-...,API_KEY=seu-token
```

---

## Configurações de Produção

### Variáveis de Ambiente Recomendadas

```env
# Obrigatório
OPENAI_API_KEY=sk-sua-chave-real

# Segurança (OBRIGATÓRIO em produção)
API_KEY=token-forte-e-aleatorio-aqui

# Performance
RATE_LIMIT_PER_MINUTE=100
LLM_CONCURRENCY=10

# Logs
LOG_LEVEL=WARNING
ENVIRONMENT=production

# Database (se usar PostgreSQL)
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db
```

### Checklist de Segurança

- [ ] `API_KEY` configurada e forte
- [ ] `OPENAI_API_KEY` em variável de ambiente (não hardcoded)
- [ ] HTTPS habilitado (via Nginx/Cloudflare/etc)
- [ ] Rate limiting configurado adequadamente
- [ ] Logs não expõem informações sensíveis
- [ ] Firewall configurado (apenas porta 80/443 aberta)
- [ ] Backup automático do banco de dados
- [ ] Monitoramento de erros configurado

### Monitoramento

#### Healthcheck

```bash
# Verificar saúde a cada 30s
*/30 * * * * curl -f http://localhost:8000/health || systemctl restart hn-enricher
```

#### Logs

```bash
# Rotação de logs
sudo nano /etc/logrotate.d/hn-enricher
```

```
/var/log/hn-enricher/*.log {
    daily
    rotate 7
    compress
    delaycompress
    notifempty
    create 0640 seu-usuario seu-usuario
    sharedscripts
    postrotate
        systemctl reload hn-enricher > /dev/null
    endscript
}
```

#### Métricas (Prometheus)

```python
# Adicionar ao app/main.py
from prometheus_fastapi_instrumentator import Instrumentator

Instrumentator().instrument(app).expose(app)
```

---

## Backup e Recuperação

### Backup do Banco de Dados

```bash
# Backup manual
cp hn_articles.db hn_articles.db.backup-$(date +%Y%m%d)

# Backup automático (cron)
0 2 * * * cp /caminho/hn_articles.db /backups/hn_articles.db.$(date +\%Y\%m\%d)
```

### Restauração

```bash
# Parar serviço
sudo systemctl stop hn-enricher

# Restaurar backup
cp hn_articles.db.backup-20240101 hn_articles.db

# Iniciar serviço
sudo systemctl start hn-enricher
```

---

## Troubleshooting

### Problema: Container não inicia

```bash
# Ver logs detalhados
docker logs hn-enricher

# Verificar variáveis de ambiente
docker exec hn-enricher env
```

### Problema: Migrações falham

```bash
# Entrar no container
docker exec -it hn-enricher bash

# Verificar estado das migrações
alembic current

# Aplicar manualmente
alembic upgrade head
```

### Problema: Alta latência

- Verificar logs de performance
- Aumentar `LLM_CONCURRENCY`
- Considerar cache (Redis)
- Verificar rate limits da OpenAI

---

## Escalabilidade

### Horizontal Scaling

Para escalar horizontalmente:

1. Use PostgreSQL ao invés de SQLite
2. Use Redis para rate limiting
3. Use Celery para workers
4. Load balancer (Nginx/HAProxy)

### Vertical Scaling

Recursos recomendados por carga:

| Carga | CPU | RAM | Workers |
|-------|-----|-----|---------|
| Baixa (< 10 req/min) | 1 core | 512MB | 2 |
| Média (10-50 req/min) | 2 cores | 1GB | 4 |
| Alta (> 50 req/min) | 4 cores | 2GB | 8 |

---

## Suporte

- Issues: [GitHub Issues](https://github.com/seu-usuario/hn-signal-python-fastpi/issues)
- Documentação: [README.md](./README.md)
- Melhorias: [IMPROVEMENTS.md](./IMPROVEMENTS.md)
