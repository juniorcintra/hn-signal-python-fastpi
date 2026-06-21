# Guia de Migração - v1.0 para v2.0

Este guia ajuda a migrar de uma instalação existente para a versão melhorada do projeto.

## Mudanças Importantes

### 1. Pipeline Endpoint Mudou

**Antes (v1.0):**
```bash
curl -X POST http://localhost:8000/api/v1/pipeline/run
# Resposta após 10-15 segundos com resultados completos
```

**Depois (v2.0):**
```bash
curl -X POST http://localhost:8000/api/v1/pipeline/run \
  -H "X-API-Key: your-key"
# Resposta imediata com job_id

# Verificar status
curl http://localhost:8000/api/v1/pipeline/jobs/1
```

### 2. Autenticação Necessária

Endpoints protegidos agora requerem API key:
- `POST /api/v1/pipeline/run`
- `GET /api/v1/pipeline/test-llm`

Configure no `.env`:
```env
API_KEY=seu-token-secreto-aqui
```

### 3. Endpoint de Retry Removido

O endpoint `POST /api/v1/pipeline/retry` foi removido. Para reprocessar artigos falhados:

1. Marque artigos como `pending`:
```sql
UPDATE articles 
SET enrichment_status = 'pending' 
WHERE enrichment_status = 'failed';
```

2. Execute novo job do pipeline

## Passo a Passo da Migração

### 1. Backup do Banco de Dados

```bash
# Faça backup do banco existente
cp hn_articles.db hn_articles.db.backup
```

### 2. Atualizar Código

```bash
git pull origin main
# ou baixe a nova versão
```

### 3. Instalar Novas Dependências

```bash
pip install -r requirements.txt
```

Novas dependências:
- `alembic>=1.13.0` - Migrações de banco

### 4. Atualizar Variáveis de Ambiente

Adicione ao seu `.env`:

```env
# Opcional: deixe vazio para desabilitar autenticação
API_KEY=

# Rate limiting
RATE_LIMIT_PER_MINUTE=10

# Logs
ENVIRONMENT=production
LOG_LEVEL=INFO
```

### 5. Executar Migrações

```bash
# Aplicar migrações para adicionar tabela de jobs
alembic upgrade head
```

Isso criará a tabela `pipeline_jobs` sem afetar dados existentes.

### 6. Testar a Migração

```bash
# 1. Verificar saúde
curl http://localhost:8000/health

# 2. Listar artigos existentes
curl http://localhost:8000/api/v1/articles

# 3. Testar novo pipeline (com API key se configurada)
curl -X POST http://localhost:8000/api/v1/pipeline/run \
  -H "X-API-Key: your-key"

# 4. Verificar status do job
curl http://localhost:8000/api/v1/pipeline/jobs/1
```

## Compatibilidade de Dados

### Artigos Existentes

✅ Todos os artigos existentes continuam funcionando  
✅ Campos de enriquecimento mantidos  
✅ Índices preservados  
✅ Queries antigas funcionam normalmente

### Nova Tabela de Jobs

A tabela `pipeline_jobs` é criada vazia. Jobs anteriores não são rastreados retroativamente.

### Tags

A coluna JSON `tags` é mantida para compatibilidade. A nova modelagem relacional é opcional:

```python
# Código antigo continua funcionando
article.tags  # ['python', 'fastapi']

# Novo código pode usar
article.tag_objects  # [Tag(name='python'), Tag(name='fastapi')]
```

## Rollback (Se Necessário)

Se precisar reverter para v1.0:

```bash
# 1. Restaurar backup do banco
cp hn_articles.db.backup hn_articles.db

# 2. Reverter código
git checkout v1.0
# ou restaure versão anterior

# 3. Reinstalar dependências antigas
pip install -r requirements.txt
```

## Mudanças de Comportamento

### Rate Limiting

Por padrão, endpoints protegidos aceitam 10 requisições/minuto por IP.

Para desabilitar temporariamente durante migração:
```env
RATE_LIMIT_PER_MINUTE=1000
```

### Concorrência

Apenas 1 job de pipeline pode executar por vez. Requisições concorrentes retornam HTTP 409.

### Logs

Logs agora incluem mais contexto:
```
2024-01-01 12:00:00 [INFO] app.background_jobs [background_jobs.py:85] — Job 1 completed
```

## Integração com Sistemas Existentes

### Scripts de Automação

Se você tem scripts que chamam o pipeline:

**Antes:**
```python
response = requests.post("http://localhost:8000/api/v1/pipeline/run")
results = response.json()
print(f"Enriched: {results['enriched']}")
```

**Depois:**
```python
# Iniciar job
response = requests.post(
    "http://localhost:8000/api/v1/pipeline/run",
    headers={"X-API-Key": "your-key"}
)
job_id = response.json()["job_id"]

# Polling de status
import time
while True:
    status_response = requests.get(f"http://localhost:8000/api/v1/pipeline/jobs/{job_id}")
    job = status_response.json()
    
    if job["status"] in ["completed", "failed"]:
        break
    
    time.sleep(2)

print(f"Enriched: {job['enriched']}")
```

### Webhooks/Notificações

Se você precisa de notificações quando jobs completam, considere:

1. **Polling:** Verificar status periodicamente
2. **Logs:** Monitorar logs para mensagens de conclusão
3. **Futuro:** Webhooks serão adicionados em v2.1

## Perguntas Frequentes

### Q: Preciso reprocessar todos os artigos?
**A:** Não. Artigos já enriquecidos permanecem inalterados.

### Q: Posso desabilitar autenticação?
**A:** Sim. Deixe `API_KEY` vazio no `.env`.

### Q: Como migrar tags para nova modelagem?
**A:** Execute o script de migração (será fornecido em v2.1) ou mantenha JSON.

### Q: Jobs antigos são rastreados?
**A:** Não. Apenas jobs iniciados após a migração aparecem na tabela.

### Q: Posso usar v1.0 e v2.0 simultaneamente?
**A:** Não recomendado. Use bancos de dados separados se necessário.

## Suporte

- Issues: https://github.com/seu-usuario/hn-signal-python-fastpi/issues
- Documentação: [IMPROVEMENTS.md](./IMPROVEMENTS.md)
- Changelog: [CHANGELOG.md](./CHANGELOG.md)

## Checklist de Migração

- [ ] Backup do banco de dados criado
- [ ] Código atualizado para v2.0
- [ ] Dependências instaladas (`pip install -r requirements.txt`)
- [ ] Variáveis de ambiente atualizadas
- [ ] Migrações executadas (`alembic upgrade head`)
- [ ] Testes executados com sucesso
- [ ] Endpoint de health verificado
- [ ] Primeiro job de pipeline testado
- [ ] Scripts de automação atualizados
- [ ] Equipe notificada sobre mudanças
