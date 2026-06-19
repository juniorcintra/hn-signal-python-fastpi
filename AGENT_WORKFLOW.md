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
