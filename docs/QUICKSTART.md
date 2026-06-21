# Guia Rápido - HN Article Enricher v2.0

Comece a usar o projeto em 5 minutos.

## Instalação Rápida

```bash
# 1. Clone o repositório
git clone https://github.com/seu-usuario/hn-signal-python-fastpi.git
cd hn-signal-python-fastpi

# 2. Crie ambiente virtual
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/macOS

# 3. Instale dependências
pip install -r requirements.txt

# 4. Configure variáveis de ambiente
cp .env.example .env
# Edite .env e adicione sua OPENAI_API_KEY
```

## Configuração Mínima

Edite `.env`:

```env
# Obrigatório
OPENAI_API_KEY=sk-sua-chave-aqui

# Opcional (para proteger endpoints)
API_KEY=meu-token-secreto

# Opcional (padrões funcionam bem)
DATABASE_URL=sqlite+aiosqlite:///./hn_articles.db
RATE_LIMIT_PER_MINUTE=10
LOG_LEVEL=INFO
```

## Iniciar Servidor

```bash
# Aplicar migrações
alembic upgrade head

# Iniciar servidor
uvicorn app.main:app --reload
```

Acesse:
- **API:** http://localhost:8000
- **Docs:** http://localhost:8000/docs
- **Health:** http://localhost:8000/health

## Primeiro Uso

### 1. Testar Conexão LLM

```bash
curl http://localhost:8000/api/v1/pipeline/test-llm \
  -H "X-API-Key: meu-token-secreto"
```

Resposta esperada:
```json
{
  "status": "ok",
  "model": "gpt-4o-mini",
  "reply": "ok"
}
```

### 2. Executar Pipeline

```bash
curl -X POST http://localhost:8000/api/v1/pipeline/run \
  -H "X-API-Key: meu-token-secreto"
```

Resposta:
```json
{
  "job_id": 1,
  "status": "pending",
  "message": "Pipeline job 1 started in background"
}
```

### 3. Verificar Status

```bash
curl http://localhost:8000/api/v1/pipeline/jobs/1
```

Aguarde até `status` ser `"completed"`:
```json
{
  "id": 1,
  "status": "completed",
  "scraped": 30,
  "new_items": 30,
  "enriched": 28,
  "failed": 2
}
```

### 4. Listar Artigos

```bash
curl http://localhost:8000/api/v1/articles?page=1&page_size=5
```

### 5. Filtrar por Categoria

```bash
curl "http://localhost:8000/api/v1/articles?category=technology&page_size=10"
```

## Usando o Cliente Python

```bash
python examples/pipeline_client.py
```

Ou use programaticamente:

```python
from examples.pipeline_client import PipelineClient

client = PipelineClient(api_key="meu-token-secreto")

# Iniciar pipeline
job = client.start_pipeline()
print(f"Job iniciado: {job['job_id']}")

# Aguardar conclusão
result = client.wait_for_completion(job['job_id'])
print(f"Enriquecidos: {result['enriched']}")

# Buscar artigos
articles = client.get_articles(category="technology", page_size=5)
for article in articles['items']:
    print(f"- {article['title']}")
```

## Comandos Úteis

### Desenvolvimento

```bash
# Rodar testes
pytest tests/ -v

# Testes com cobertura
pytest tests/ --cov=app --cov-report=html

# Criar nova migração
alembic revision --autogenerate -m "descrição"

# Aplicar migrações
alembic upgrade head

# Reverter última migração
alembic downgrade -1
```

### Produção

```bash
# Iniciar com Gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker

# Verificar saúde
curl http://localhost:8000/health

# Ver estatísticas
curl http://localhost:8000/api/v1/pipeline/stats

# Listar jobs recentes
curl http://localhost:8000/api/v1/pipeline/jobs?limit=10
```

## Troubleshooting

### Erro: "API key required"

Configure `API_KEY` no `.env` ou remova a proteção deixando vazio:
```env
API_KEY=
```

### Erro: "Rate limit exceeded"

Aguarde 1 minuto ou aumente o limite:
```env
RATE_LIMIT_PER_MINUTE=100
```

### Erro: "Another job is already running"

Aguarde o job atual terminar ou consulte status:
```bash
curl http://localhost:8000/api/v1/pipeline/jobs
```

### Erro: "OpenAI API error"

Verifique:
1. `OPENAI_API_KEY` está correto no `.env`
2. Você tem créditos na conta OpenAI
3. Teste a conexão: `/api/v1/pipeline/test-llm`

### Banco de dados corrompido

```bash
# Backup
cp hn_articles.db hn_articles.db.backup

# Recriar
rm hn_articles.db
alembic upgrade head
```

## Próximos Passos

1. ✅ Explore a [documentação completa](./README.md)
2. ✅ Leia sobre as [melhorias implementadas](./IMPROVEMENTS.md)
3. ✅ Configure monitoramento e logs
4. ✅ Ajuste rate limiting para sua necessidade
5. ✅ Considere usar Redis para rate limiting distribuído

## Recursos

- **Documentação API:** http://localhost:8000/docs
- **Código Fonte:** [GitHub](https://github.com/seu-usuario/hn-signal-python-fastpi)
- **Issues:** [GitHub Issues](https://github.com/seu-usuario/hn-signal-python-fastpi/issues)

## Suporte

Problemas? Abra uma issue no GitHub ou consulte:
- [IMPROVEMENTS.md](./IMPROVEMENTS.md) - Detalhes técnicos
- [MIGRATION_GUIDE.md](./MIGRATION_GUIDE.md) - Migração de v1.0
- [CHANGELOG.md](./CHANGELOG.md) - Histórico de mudanças

---

**Versão:** 2.0.0  
**Última atualização:** Janeiro 2024
