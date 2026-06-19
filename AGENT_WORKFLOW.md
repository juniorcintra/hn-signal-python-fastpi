# AGENT_WORKFLOW — Como o agente de código foi usado

## Ferramenta

**Windsurf Cascade** (modelo Claude Sonnet) via painel de chat integrado no IDE.  
O agente tem acesso ao sistema de arquivos e ao terminal, e pode criar/editar arquivos
diretamente na workspace.

---

## Fluxo da sessão

### Prompt inicial

O usuário colou o enunciado completo do case (3 responsabilidades: scraping,
enriquecimento com LLM, API REST) e pediu ao agente que construísse o projeto.

O agente:

1. Inspecionou o diretório (estava vazio).
2. Tomou decisões de design antes de escrever código: domínio (HN), stack
   (FastAPI + SQLAlchemy async + OpenAI), estrutura de arquivos.
3. Gerou 17 arquivos em sequência: `requirements.txt`, `.env.example`, documentação,
   camada core (`config`, `database`, `enums`, `models`, `schemas`), scraper,
   enrichment, routers e `main.py`.

**O que funcionou bem:** a geração em lote, com decisões de design explicitadas antes
de cada bloco de código, produziu um projeto estruturalmente correto na primeira
tentativa. O agente reconheceu sozinho a necessidade de separar `enums.py` do
`models.py` para evitar imports circulares.

---

### Erros cometidos pelo agente e como foram corrigidos

#### 1. Import não utilizado em `main.py`

**O que aconteceu:** o agente gerou `from sqlalchemy.ext.asyncio import AsyncSession`
em `main.py`, import que não era usado (sobrou de uma versão anterior do health
endpoint que dependia de `get_db`).

**Como foi detectado:** revisão manual do arquivo gerado imediatamente após a criação.

**Correção:** o agente identificou o problema durante sua própria revisão de código
(antes de ser apontado pelo usuário) e removeu o import com uma edição cirúrgica.

---

#### 2. Falha no comando de instalação (Windows)

**O que aconteceu:** o agente propôs `pip install -r requirements.txt`. O comando
falhou porque o shell bash no Windows (`C:\Program Files\Git\bin\bash.exe`) tem
espaço no caminho, causando erro de sintaxe.

```
'C:\Program' is not recognized as an internal or external command
```

**Como foi detectado:** erro de execução retornado pelo terminal.

**Correção:** o agente substituiu por `python -m pip install -r requirements.txt`,
que é a forma robusta e portável em qualquer ambiente Python no Windows.

---

#### 3. Análise de ToS/anti-bot ausente no documento de raciocínio

**O que aconteceu:** o agente gerou o `REASONING.md` com foco em decisões de
arquitetura, mas omitiu a avaliação de Termos de Uso, proteção anti-bot e robustez
da fonte — que o enunciado pedia explicitamente para fontes reais.

**Como foi detectado:** o usuário re-leu a seção 3 do enunciado e percebeu a lacuna.

**Correção:** o agente adicionou a seção "Avaliação da fonte: ToS, anti-bot e
robustez" ao documento, cobrindo: conformidade legal com os ToS do HN, ausência de
mecanismos anti-bot que justificariam Selenium/Playwright, e os três níveis de
resiliência do parser.

**Lição:** o agente tende a focar nas decisões técnicas e pode negligenciar requisitos
de processo/compliance quando não estão no prompt principal. Vale reler o enunciado
completo após a geração inicial.

---

#### 4. Nome de arquivo errado: `REASONING.md` vs `RATIONALE.md`

**O que aconteceu:** o enunciado especifica `RATIONALE.md` como um dos entregáveis.
O agente nomeou o arquivo `REASONING.md` por ser uma tradução mais próxima do
"documento de raciocínio" mencionado na seção 2, sem verificar o nome exato na seção
de entregáveis (seção 5).

**Como foi detectado:** o usuário colou a seção 5 do enunciado, que lista os
entregáveis com nomes específicos.

**Correção:** criação do `RATIONALE.md` com todo o conteúdo consolidado (incluindo
a seção de limitações conhecidas). O arquivo `REASONING.md` permanece na workspace
como artefato histórico mas não é o entregável principal.

**Lição:** sempre verificar os nomes exatos de artefatos no enunciado de entregáveis,
não apenas no corpo do problema.

---

#### 5. Testes ausentes na entrega inicial

**O que aconteceu:** o enunciado pede "testes nos pontos críticos", mas o agente não
os criou na geração inicial. Focou em construir o serviço funcional primeiro.

**Como foi detectado:** o usuário colou a seção 5 completa, que lista "testes nos
pontos críticos" como parte do entregável.

**Correção:** o agente criou a suíte de testes completa:

- `tests/conftest.py` — fixtures com SQLite in-memory + `StaticPool`
- `tests/test_scraper.py` — 11 testes unitários do parser (sem rede)
- `tests/test_schemas.py` — 9 testes de validação do schema LLM
- `tests/test_api.py` — 18 testes de integração HTTP

**Lição:** em entregas com checklist de entregáveis, verificar cada item antes de
declarar conclusão.

---

## Estratégias que funcionaram bem

- **Decomposição antecipada:** pedir ao agente para explicitar as decisões de design
  (domínio, stack, trade-offs) antes de gerar código evita retrabalho arquitetural.
- **Revisão por arquivo:** ler cada arquivo gerado antes de passar para o próximo
  captura imports não utilizados, inconsistências de nomenclatura e lógica incorreta
  enquanto o contexto ainda está fresco.
- **Prompts com o enunciado original:** colar trechos do enunciado durante a sessão
  é mais eficaz do que resumir o que está faltando — o agente consegue rastrear os
  requisitos originais com precisão.
- **Correções incrementais:** em vez de pedir ao agente para refazer tudo quando algo
  está errado, edições cirúrgicas (um arquivo de cada vez) preservam o que estava
  correto e reduzem o risco de regressão.

---

## O que ficaria diferente numa próxima iteração

- Passar o enunciado completo (incluindo a seção de entregáveis) no prompt inicial,
  não em etapas. Isso teria evitado os erros 3, 4 e 5.
- Pedir ao agente para criar um checklist dos entregáveis antes de escrever código,
  e verificá-lo ao final da sessão.

---

## Iteração 2 — Execução real, naming e push para GitHub

### Servidor rodando + 429 Rate Limit

O usuário rodou `uvicorn app.main:app --reload` e acionou o pipeline. Os logs mostraram
que o scraper funcionou corretamente (artigos coletados do HN) e o enriquecimento foi
acionado, mas a API key do OpenAI retornou `429 Too Many Requests` para todos os itens.

```
Enrichment failed for hn_id=...: RateLimitError: Error code: 429 -
{'error': {'message': 'You exceeded your current quota...'}}
```

**O que isso valida:**

- O retry via `tenacity` funcionou (as mensagens "Retrying request... in X seconds"
  confirmam as tentativas com backoff).
- Após esgotar as tentativas, o artigo foi marcado como `failed` no banco — exatamente
  o comportamento esperado.
- O pipeline não abortou: retornou contadores parciais com `failed > 0`.

**Causa:** quota da API key excedida (plano free ou limite de tier). Não é bug do código.
Solução: adicionar créditos na conta OpenAI ou usar outra key.

**Observação sobre o `--reload`:** o uvicorn em modo reload detectou criação dos
arquivos de teste na workspace e reiniciou o processo várias vezes durante a sessão.
Isso não é problema, mas em uso real convém rodar sem `--reload` para evitar
reinicializações desnecessárias.

---

### Decisão de processo

O usuário solicitou que o agente **atualize este documento a cada iteração relevante**
da sessão, registrando decisões, erros, correções e observações em tempo real.

---

## Iteração 3 — Bug 422 em parâmetros opcionais vazios

### O que aconteceu

O usuário testou o endpoint `GET /api/v1/articles` via Postman com os três filtros
opcionais habilitados mas sem valor preenchido (`?category=technology&tag=&enrichment_status=`).
A resposta foi `422 Unprocessable Content`:

```json
{
  "detail": [
    {
      "type": "enum",
      "loc": ["query", "enrichment_status"],
      "msg": "Input should be 'pending', 'processing', 'completed' or 'failed'",
      "input": ""
    }
  ]
}
```

### Causa raiz

O parâmetro `enrichment_status` era declarado como `Optional[EnrichmentStatus]` no
router. Quando o cliente envia `enrichment_status=` (string vazia), FastAPI/Pydantic
tenta validá-la contra o enum — e `""` não é um valor válido, causando o 422.
Ferramentas como Insomnia e Postman costumam enviar parâmetros vazios quando o campo
está habilitado mas sem valor, o que torna esse comportamento comum em uso real.

### Correção

- `enrichment_status` passou a ser recebido como `Optional[str]`.
- Empty strings são normalizadas para `None` antes de qualquer lógica de filtro.
- A conversão para `EnrichmentStatus` é feita manualmente com `try/except ValueError`,
  retornando um 422 claro com mensagem descritiva para valores inválidos não-vazios.
- O mesmo tratamento foi aplicado a `category` e `tag` (`or None`).
- Dois novos testes adicionados: `test_empty_string_params_are_ignored` (200) e
  `test_invalid_enrichment_status_returns_422` (422 com mensagem útil).

---

## Iteração 4 — Endpoint de diagnóstico do LLM

### Contexto

O usuário perguntou como verificar se a API key do OpenAI estava funcionando antes de
rodar o pipeline completo (que custa mais tokens e leva ~15s).

### Decisão

Adicionado `GET /api/v1/pipeline/test-llm` — faz uma chamada de ~5 tokens ao modelo
configurado e retorna `status: ok` ou `status: error` com a mensagem de exceção.

**Resposta esperada quando a key funciona:**

```json
{ "status": "ok", "model": "gpt-4o-mini", "reply": "ok" }
```

**Resposta quando há quota excedida (429):**

```json
{ "status": "error", "model": "gpt-4o-mini", "error": "RateLimitError: ..." }
```

O endpoint reutiliza `_client` (o `AsyncOpenAI` singleton já instanciado em
`llm_enricher.py`) — sem criar nova conexão, sem tocar no banco.

### Observação de design

O endpoint não tem `response_model` fixo (retorna `dict`) porque os campos diferem
entre sucesso (`reply`) e erro (`error`). Uma alternativa mais tipada seria um
schema union com `Literal["ok"] | Literal["error"]`, mas para um endpoint de
diagnóstico a clareza do `dict` simples supera o custo de manutenção do schema.
