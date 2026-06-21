# Exemplos de Uso

Esta pasta contém exemplos práticos de como usar a API do HN Article Enricher.

## Pipeline Client

**Arquivo:** `pipeline_client.py`

Cliente Python completo demonstrando:
- Autenticação com API key
- Iniciar job de pipeline
- Polling de status
- Consulta de artigos enriquecidos

### Uso Básico

```bash
# Com API key configurada no .env
python examples/pipeline_client.py

# Ou especificando API key
API_KEY=seu-token python examples/pipeline_client.py
```

### Uso Programático

```python
from examples.pipeline_client import PipelineClient

# Inicializar cliente
client = PipelineClient(
    base_url="http://localhost:8000",
    api_key="seu-token"
)

# 1. Testar conexão LLM
llm_status = client.test_llm_connection()
print(f"LLM Status: {llm_status['status']}")

# 2. Iniciar pipeline
job = client.start_pipeline()
job_id = job["job_id"]

# 3. Aguardar conclusão (com timeout)
result = client.wait_for_completion(
    job_id,
    poll_interval=2,  # segundos entre checks
    timeout=300       # timeout total
)

print(f"Scraped: {result['scraped']}")
print(f"Enriched: {result['enriched']}")
print(f"Failed: {result['failed']}")

# 4. Buscar artigos
articles = client.get_articles(
    page=1,
    page_size=10,
    category="technology",
    enrichment_status="completed"
)

for article in articles['items']:
    print(f"\n{article['title']}")
    print(f"Category: {article['category']}")
    print(f"Tags: {', '.join(article['tags'] or [])}")
    print(f"Summary: {article['summary']}")
```

## Outros Exemplos

### Exemplo 1: Monitoramento Contínuo

```python
import time
from pipeline_client import PipelineClient

client = PipelineClient()

while True:
    print("Iniciando pipeline...")
    job = client.start_pipeline()
    
    result = client.wait_for_completion(job['job_id'])
    
    print(f"Concluído: {result['enriched']} artigos enriquecidos")
    
    # Aguardar 1 hora antes do próximo run
    time.sleep(3600)
```

### Exemplo 2: Processar Apenas Artigos Novos

```python
from pipeline_client import PipelineClient

client = PipelineClient()

# Buscar total atual
current = client.get_articles(page=1, page_size=1)
total_before = current['total']

# Executar pipeline
job = client.start_pipeline()
result = client.wait_for_completion(job['job_id'])

# Buscar novos artigos
if result['new_items'] > 0:
    new_articles = client.get_articles(
        page=1,
        page_size=result['new_items'],
        enrichment_status="completed"
    )
    
    print(f"Novos artigos enriquecidos: {result['new_items']}")
    for article in new_articles['items']:
        print(f"- {article['title']}")
```

### Exemplo 3: Análise de Categorias

```python
from collections import Counter
from pipeline_client import PipelineClient

client = PipelineClient()

# Buscar todos os artigos enriquecidos
all_articles = []
page = 1

while True:
    response = client.get_articles(
        page=page,
        page_size=100,
        enrichment_status="completed"
    )
    
    all_articles.extend(response['items'])
    
    if len(all_articles) >= response['total']:
        break
    
    page += 1

# Análise de categorias
categories = Counter(a['category'] for a in all_articles)
print("\nDistribuição de Categorias:")
for category, count in categories.most_common():
    print(f"{category}: {count}")

# Análise de tags
all_tags = []
for article in all_articles:
    if article['tags']:
        all_tags.extend(article['tags'])

tags = Counter(all_tags)
print("\nTop 10 Tags:")
for tag, count in tags.most_common(10):
    print(f"{tag}: {count}")
```

### Exemplo 4: Webhook Simulator

```python
import asyncio
from pipeline_client import PipelineClient

async def webhook_callback(job_result):
    """Simula um webhook quando job completa."""
    print(f"\n🔔 Webhook triggered!")
    print(f"Job ID: {job_result['id']}")
    print(f"Status: {job_result['status']}")
    print(f"Enriched: {job_result['enriched']}")
    
    # Aqui você poderia enviar para um webhook real
    # await send_to_webhook("https://example.com/webhook", job_result)

async def monitor_job(client, job_id):
    """Monitora job e dispara webhook ao completar."""
    while True:
        job = client.get_job_status(job_id)
        
        if job['status'] in ['completed', 'failed']:
            await webhook_callback(job)
            break
        
        await asyncio.sleep(2)

# Uso
client = PipelineClient()
job = client.start_pipeline()

asyncio.run(monitor_job(client, job['job_id']))
```

### Exemplo 5: Retry com Backoff

```python
import time
from pipeline_client import PipelineClient

def start_pipeline_with_retry(client, max_retries=3):
    """Tenta iniciar pipeline com retry exponencial."""
    for attempt in range(max_retries):
        try:
            job = client.start_pipeline()
            return job
        except Exception as e:
            if "409" in str(e):  # Conflict - outro job rodando
                wait_time = 2 ** attempt  # Backoff exponencial
                print(f"Job em andamento. Tentando novamente em {wait_time}s...")
                time.sleep(wait_time)
            else:
                raise
    
    raise Exception("Não foi possível iniciar pipeline após retries")

client = PipelineClient()
job = start_pipeline_with_retry(client)
print(f"Pipeline iniciado: {job['job_id']}")
```

## Requisitos

```bash
pip install httpx
```

## Variáveis de Ambiente

```env
# .env
API_KEY=seu-token-secreto
```

## Contribuindo

Tem um exemplo útil? Adicione aqui:

1. Crie arquivo `exemplo_X.py`
2. Documente no README
3. Abra PR

## Suporte

- Documentação: [../README.md](../README.md)
- Issues: [GitHub Issues](https://github.com/seu-usuario/hn-signal-python-fastpi/issues)
