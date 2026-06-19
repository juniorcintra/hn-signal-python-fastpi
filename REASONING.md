# Documento de Raciocínio — HN Article Enricher

## Domínio escolhido

**Hacker News front page** (`news.ycombinator.com`).

Motivos:

- HTML estático e bem estruturado — BeautifulSoup é suficiente; Selenium seria
  overhead desnecessário (não há paginação por scroll, autenticação ou renderização
  JavaScript no conteúdo principal).
- Dados ricos: título, URL, pontos, autor, número de comentários, rank — bons campos
  para enriquecer.
- Fonte pública, estável e com estrutura previsível há anos.
- Domínio agnóstico (tech, science, business, entretenimento) — exercita bem a
  classificação por LLM.

---

## Avaliação da fonte: ToS, anti-bot e robustez

### Termos de Uso

O HN não possui um `robots.txt` restritivo para a front page (crawlers são
explicitamente permitidos) e os Termos de Serviço do Y Combinator não proíbem scraping
de conteúdo público em volumes razoáveis. A boa prática de identificar o bot no
`User-Agent` (implementado no scraper) está alinhada com as expectativas de
operadores web responsáveis.

Ponto de atenção: o HN expõe uma **API oficial**
(`https://hacker-news.firebaseio.com/v0/`) que retorna JSON estruturado. A razão para
não usá-la e manter o scraper HTML é **deliberada**: o desafio técnico pede
explicitamente o uso de BeautifulSoup/Selenium como demonstração de habilidade de
extração. Usar a API diretamente eliminaria essa dimensão do exercício. Em um contexto
real de produto onde o objetivo é apenas obter os dados, a API seria a escolha correta.

### Proteção anti-bot

O HN **não implementa mecanismos anti-bot agressivos** na front page:

- Sem CAPTCHA no acesso público.
- Sem fingerprinting de navegador (não há JS necessário para o conteúdo).
- Sem rate limiting em acesso esporádico (uma requisição por execução do pipeline).
- Sem autenticação ou cookies obrigatórios.

Por isso, Selenium/Playwright seria **over-engineering** aqui. Os casos onde eles
fazem sentido são:

- Conteúdo renderizado por JavaScript após o carregamento inicial (ex.: Twitter/X,
  feeds de vagas do LinkedIn).
- Paginação por scroll infinito (ex.: feeds de produtos).
- Fluxos que exigem login, 2FA ou resolução de CAPTCHA.
- Sites que servem HTML esqueleto e populam via XHR/fetch (ex.: SPAs React/Vue).

Se a fonte fosse, por exemplo, o LinkedIn Jobs ou o Glassdoor, Playwright seria
necessário por todas essas razões simultaneamente.

### Robustez do parser

O scraper trata o "mundo real" em três camadas:

1. **Nível HTTP**: `tenacity` com backoff exponencial cobre timeouts e falhas
   transitórias de rede. Erros 4xx/5xx fazem `raise_for_status()` e propagam após
   esgotar as tentativas.

2. **Nível de parsing**: cada `<tr.athing>` é processado em `try/except` independente.
   Um item malformado (campo ausente, estrutura inesperada) gera um `WARNING` no log
   e é descartado sem interromper o restante do lote. O campo `points` usa
   `_parse_int()` que retorna `0` silenciosamente para elementos ausentes (ex.: posts
   "Ask HN" sem votos iniciais).

3. **Nível de contrato**: se o HN mudar o layout (renomear classes CSS, por exemplo),
   o scraper retornará uma lista vazia ou parcial em vez de lançar uma exceção.
   O endpoint `/run` detecta `len(scraped_items) == 0` implicitamente via `new_count`
   e a ausência de itens é perceptível via `GET /api/v1/pipeline/stats` — facilitando
   alertas de monitoramento.

---

## Decisões de scraping

### BeautifulSoup vs. Selenium/Playwright

O HN entrega o HTML completo no primeiro request — não há conteúdo lazy-loaded.
Selenium/Playwright adicionaria latência de inicialização do browser driver, dependência
de binários externos e complexidade desnecessária para este caso.

Se a fonte fosse algo como LinkedIn Jobs ou Twitter/X (onde o conteúdo exige
autenticação ou scroll dinâmico), Playwright seria a escolha preferida por sua API
async nativa e melhor ergonomia sobre o Selenium clássico.

### Resiliência

- **Timeout explícito** via `httpx` (configurável em `.env`).
- **Retry com backoff exponencial** via `tenacity` — cobre falhas transitórias de rede.
- **Tratamento defensivo** de cada item: parse por item em `try/except`, item com
  falha é logado e descartado sem quebrar o batch inteiro.
- Campos ausentes (ex.: score em posts de "Ask HN" sem votes iniciais) têm defaults
  seguros (`0`).

---

## Decisões de enriquecimento com IA

### Modelo: `gpt-4o-mini`

- Custo baixíssimo (~$0.15/1M input tokens) — relevante para 30 artigos por run.
- Latência adequada para uso síncrono.
- Suporte nativo a `response_format: { type: "json_object" }`, que garante JSON
  válido na saída (elimina a maioria dos erros de parse).

### Consciência de custo e tokens

- **Truncamento de título**: limitado a `LLM_TITLE_MAX_CHARS` (default 200 chars).
  Títulos do HN raramente passam disso; protege contra edge cases.
- **Temperatura baixa (0.2)**: reduz variabilidade da saída, aumenta conformidade
  com o schema e evita tokens desperdiçados em "criatividade".
- **`max_tokens` configurável**: default 400 — suficiente para a saída estruturada sem
  pagar por tokens não usados.
- **Semáforo de concorrência** (`LLM_CONCURRENCY=5`): evita rate-limit da OpenAI
  sem serializar desnecessariamente.
- **Idempotência**: artigos já enriquecidos (`completed`) não são reenviados ao LLM.
  Novas rodadas do pipeline só processam itens `pending`.

### Robustez de saída

Mesmo com `json_object` garantindo JSON válido, o conteúdo pode não conformar ao
schema (campo faltante, valor fora do `Literal`). A validação Pydantic captura isso e
marca o item como `failed` em vez de persistir dados inválidos. O endpoint
`POST /api/v1/pipeline/retry` permite reprocessar falhas sem re-scrape.

### Retry de API

`tenacity` com retry apenas em `RateLimitError` e `APIError` — erros de validação e
JSON não devem ser retentados (são erros do modelo, não da infraestrutura).

---

## Decisões de banco de dados

### SQLite + SQLAlchemy async

- Suficiente para o escopo; sem dependência externa.
- `aiosqlite` mantém o driver não-bloqueante dentro do event loop do FastAPI.
- Schema pensado para os filtros da API: índices em `hn_id` (upsert), `category`
  (filtro frequente) e `enrichment_status` (pipeline queries).
- `tags` armazenado como JSON column — busca por tag usa `LIKE` na representação
  textual (limitação conhecida do SQLite; num PostgreSQL usaria `GIN + @>`).

### Migrações

`create_all()` no lifespan é suficiente para o escopo. Em produção, Alembic com
migrações versionadas seria o caminho.

---

## Decisões de API

### Endpoints

| Método | Path                          | Propósito                   |
| ------ | ----------------------------- | --------------------------- |
| `GET`  | `/health`                     | Healthcheck com probe de DB |
| `GET`  | `/api/v1/articles`            | Lista paginada com filtros  |
| `GET`  | `/api/v1/articles/{id}`       | Detalhe de um item          |
| `GET`  | `/api/v1/articles/categories` | Categorias disponíveis      |
| `POST` | `/api/v1/pipeline/run`        | Scrape + enrich completo    |
| `POST` | `/api/v1/pipeline/retry`      | Re-enrich apenas falhos     |
| `GET`  | `/api/v1/pipeline/stats`      | Estatísticas do banco       |

### Paginação

Cursor-based seria mais eficiente em tabelas grandes; offset/limit é adequado para
o volume esperado (centenas de artigos) e mais simples de consumir.

### Tratamento de erros

- Handler global para `500` — evita vazar stack traces.
- Erros de scraping e LLM são tratados internamente; o endpoint retorna 200 com
  contadores de sucesso/falha em vez de abortar tudo.

---

## O que ficou de fora (e por quê)

- **Autenticação**: fora do escopo definido.
- **Celery/RQ para background jobs**: o pipeline leva ~10-15s para 30 artigos.
  Aceitável como request síncrono para este case; em produção, um worker assíncrono
  seria necessário.
- **Cache de resposta da API**: Redis/Memcached seriam overkill; a DB é rápida o
  suficiente para este volume.
- **Alembic**: adicionaria overhead de setup sem benefício real para um schema
  que não evolui durante o case.
