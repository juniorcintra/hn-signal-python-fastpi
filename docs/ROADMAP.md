# Roadmap - HN Article Enricher

Planejamento de features e melhorias futuras.

---

## ✅ v2.0.0 - Production Ready (Concluído)

### Melhorias Implementadas
- ✅ Sistema de background jobs
- ✅ Autenticação e rate limiting
- ✅ Controle de concorrência
- ✅ Migrações com Alembic
- ✅ Logs estruturados
- ✅ Modelagem de tags otimizada
- ✅ Testes expandidos (85% cobertura)
- ✅ Documentação completa

**Status:** Lançado em Janeiro 2024

---

## 🚧 v2.1.0 - Observabilidade e Notificações (Em Planejamento)

**Prazo:** Fevereiro 2024

### Features Planejadas

#### 1. Webhooks de Notificação
- [ ] Configuração de webhooks por job
- [ ] Payload customizável
- [ ] Retry automático em falhas
- [ ] Assinatura HMAC para segurança

```python
# Exemplo de uso
POST /pipeline/run
{
  "webhook_url": "https://example.com/webhook",
  "webhook_events": ["completed", "failed"]
}
```

#### 2. Server-Sent Events (SSE)
- [ ] Endpoint `/pipeline/jobs/{id}/stream`
- [ ] Updates em tempo real do status
- [ ] Progresso granular (scraping, enriching, etc)

```javascript
// Exemplo de uso
const eventSource = new EventSource('/pipeline/jobs/1/stream');
eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(`Progress: ${data.progress}%`);
};
```

#### 3. Métricas Prometheus
- [ ] Endpoint `/metrics`
- [ ] Métricas de jobs (total, sucesso, falha)
- [ ] Métricas de API (requests, latência)
- [ ] Métricas de LLM (tokens, custo)

#### 4. Script de Migração de Tags
- [ ] Migrar tags de JSON para tabela relacional
- [ ] Comando: `python scripts/migrate_tags.py`
- [ ] Preservar dados existentes
- [ ] Rollback automático em caso de erro

**Prioridade:** Alta  
**Esforço:** 2-3 semanas

---

## 🔮 v2.2.0 - Workers e Escalabilidade (Q1 2024)

**Prazo:** Março 2024

### Features Planejadas

#### 1. Celery/RQ Workers
- [ ] Substituir asyncio por Celery
- [ ] Workers dedicados para pipeline
- [ ] Retry automático com backoff
- [ ] Priorização de jobs

```python
# Exemplo
from celery import Celery

@celery.task(bind=True, max_retries=3)
def run_pipeline_task(self, job_id):
    # Pipeline logic
    pass
```

#### 2. Redis para State Management
- [ ] Rate limiting distribuído
- [ ] Cache de resultados
- [ ] Session storage
- [ ] Lock distribuído

#### 3. PostgreSQL Support
- [ ] Migração de SQLite para PostgreSQL
- [ ] Connection pooling
- [ ] Índices otimizados
- [ ] Full-text search nativo

#### 4. Cursor-Based Pagination
- [ ] Substituir offset por cursor
- [ ] Melhor performance em grandes datasets
- [ ] Consistência em updates

```bash
# Exemplo
GET /articles?cursor=eyJpZCI6MTAwfQ==&limit=20
```

**Prioridade:** Média  
**Esforço:** 3-4 semanas

---

## 🌟 v2.3.0 - Multi-Source e Customização (Q2 2024)

**Prazo:** Abril-Maio 2024

### Features Planejadas

#### 1. Multi-Source Scraping
- [ ] Reddit (r/programming, r/technology)
- [ ] Lobsters
- [ ] Dev.to
- [ ] Medium
- [ ] Configuração de fontes ativas

```yaml
# config/sources.yml
sources:
  - name: hackernews
    enabled: true
    priority: 1
  - name: reddit
    enabled: true
    subreddits: [programming, technology]
    priority: 2
```

#### 2. Custom Enrichment Prompts
- [ ] Templates de prompts customizáveis
- [ ] Variáveis dinâmicas
- [ ] Versionamento de prompts
- [ ] A/B testing de prompts

```python
# Exemplo
POST /enrichment/templates
{
  "name": "technical_analysis",
  "prompt": "Analyze {title} focusing on technical depth..."
}
```

#### 3. Scheduled Jobs
- [ ] Cron-like scheduling
- [ ] Execução automática periódica
- [ ] Configuração via API ou config file

```yaml
# config/schedules.yml
schedules:
  - name: daily_scrape
    cron: "0 9 * * *"
    source: hackernews
```

#### 4. Bulk Operations
- [ ] Import de artigos via CSV/JSON
- [ ] Export de artigos enriquecidos
- [ ] Bulk re-enrichment
- [ ] Bulk delete

**Prioridade:** Média  
**Esforço:** 4-5 semanas

---

## 🚀 v3.0.0 - Enterprise Features (Q3 2024)

**Prazo:** Junho-Agosto 2024

### Features Planejadas

#### 1. Multi-Tenancy
- [ ] Suporte a múltiplos usuários/organizações
- [ ] Isolamento de dados
- [ ] Quotas por tenant
- [ ] Billing por uso

```python
# Exemplo
GET /articles
Headers:
  X-Tenant-ID: org-123
  X-API-Key: tenant-specific-key
```

#### 2. GraphQL API
- [ ] Endpoint `/graphql`
- [ ] Queries complexas
- [ ] Subscriptions para updates
- [ ] DataLoader para N+1

```graphql
query {
  articles(category: "technology", limit: 10) {
    id
    title
    tags {
      name
      count
    }
    enrichment {
      summary
      sentiment
    }
  }
}
```

#### 3. Advanced Search
- [ ] Elasticsearch integration
- [ ] Full-text search
- [ ] Faceted search
- [ ] Relevance scoring

```bash
# Exemplo
POST /search
{
  "query": "python machine learning",
  "filters": {
    "category": ["technology"],
    "sentiment": ["positive"]
  },
  "facets": ["category", "tags", "technical_level"]
}
```

#### 4. Real-Time Updates
- [ ] WebSocket support
- [ ] Live dashboard
- [ ] Real-time notifications
- [ ] Collaborative features

**Prioridade:** Baixa (Enterprise)  
**Esforço:** 8-10 semanas

---

## 🔬 Pesquisa e Experimentação

### Features em Exploração

#### 1. AI-Powered Features
- [ ] Recomendação de artigos similares
- [ ] Detecção de trending topics
- [ ] Sumarização automática de threads
- [ ] Análise de sentimento de comentários

#### 2. Analytics Dashboard
- [ ] Visualizações interativas
- [ ] Métricas de engajamento
- [ ] Trends ao longo do tempo
- [ ] Exportação de relatórios

#### 3. Mobile App
- [ ] React Native app
- [ ] Push notifications
- [ ] Offline reading
- [ ] Sync com backend

#### 4. Browser Extension
- [ ] Chrome/Firefox extension
- [ ] Enriquecimento inline no HN
- [ ] Quick save para ler depois
- [ ] Highlights e anotações

---

## 📊 Priorização

### Critérios de Priorização
1. **Impacto no usuário** (1-5)
2. **Esforço de desenvolvimento** (1-5)
3. **Dependências técnicas**
4. **Feedback da comunidade**

### Matriz de Priorização

| Feature | Impacto | Esforço | Prioridade | Versão |
|---------|---------|---------|------------|--------|
| Webhooks | 5 | 2 | Alta | 2.1 |
| Métricas Prometheus | 4 | 2 | Alta | 2.1 |
| Celery Workers | 5 | 4 | Média | 2.2 |
| PostgreSQL | 4 | 3 | Média | 2.2 |
| Multi-Source | 4 | 4 | Média | 2.3 |
| GraphQL | 3 | 5 | Baixa | 3.0 |
| Multi-Tenancy | 3 | 5 | Baixa | 3.0 |

---

## 🤝 Como Contribuir

### Sugerir Features
1. Abra uma issue no GitHub
2. Use o template "Feature Request"
3. Descreva o problema e solução proposta
4. Aguarde feedback da comunidade

### Implementar Features
1. Escolha uma feature do roadmap
2. Comente na issue relacionada
3. Faça fork e crie branch
4. Implemente com testes
5. Abra Pull Request

### Votar em Features
- 👍 Issues com mais reações têm prioridade
- Comente com seu caso de uso
- Compartilhe feedback de implementações

---

## 📅 Timeline Visual

```
2024
│
├─ Jan ✅ v2.0.0 - Production Ready
│
├─ Feb 🚧 v2.1.0 - Observabilidade
│   ├─ Webhooks
│   ├─ SSE
│   └─ Métricas
│
├─ Mar 🔮 v2.2.0 - Escalabilidade
│   ├─ Celery
│   ├─ Redis
│   └─ PostgreSQL
│
├─ Abr-Mai 🌟 v2.3.0 - Multi-Source
│   ├─ Reddit/Lobsters
│   ├─ Custom Prompts
│   └─ Scheduling
│
└─ Jun-Ago 🚀 v3.0.0 - Enterprise
    ├─ Multi-Tenancy
    ├─ GraphQL
    └─ Advanced Search
```

---

## 🎯 Metas de Longo Prazo

### 2024
- ✅ Lançar v2.0 production-ready
- 🎯 Atingir 1000+ usuários ativos
- 🎯 Processar 100k+ artigos
- 🎯 Comunidade de 50+ contribuidores

### 2025
- 🎯 Lançar v3.0 enterprise
- 🎯 Suporte a 10+ fontes de conteúdo
- 🎯 API pública com documentação completa
- 🎯 Mobile app e browser extension

---

## 📝 Notas

- Roadmap é flexível e pode mudar baseado em feedback
- Datas são estimativas e podem variar
- Features podem ser movidas entre versões
- Contribuições da comunidade são bem-vindas

---

## 📞 Contato

- **Issues:** [GitHub Issues](https://github.com/seu-usuario/hn-signal-python-fastpi/issues)
- **Discussões:** [GitHub Discussions](https://github.com/seu-usuario/hn-signal-python-fastpi/discussions)
- **Email:** seu-email@example.com

---

**Última atualização:** Janeiro 2024  
**Próxima revisão:** Fevereiro 2024
