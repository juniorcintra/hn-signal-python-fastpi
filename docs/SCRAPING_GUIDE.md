# Guia de Scraping

Este projeto suporta dois métodos de scraping, conforme recomendado nas melhores práticas:

## 1. BeautifulSoup (Conteúdo Estático)

**Quando usar:**
- Sites com HTML server-rendered (ex: Hacker News)
- Sem JavaScript rendering
- Sem paginação infinita ou scroll
- Sem autenticação complexa

**Vantagens:**
- ✅ Rápido e leve
- ✅ Baixo consumo de recursos
- ✅ Fácil de debugar
- ✅ Não requer browser

**Exemplo:**
```python
from app.scraper.hn_scraper import scrape_hn_front_page

articles = await scrape_hn_front_page()
```

## 2. Selenium (Conteúdo Dinâmico)

**Quando usar:**
- Sites renderizados por JavaScript (React, Vue, Angular)
- Paginação por scroll infinito
- Interações complexas (cliques, formulários)
- Conteúdo carregado dinamicamente

**Vantagens:**
- ✅ Suporta JavaScript
- ✅ Simula comportamento real do usuário
- ✅ Lida com scroll infinito
- ✅ Suporta autenticação

**Desvantagens:**
- ⚠️ Mais lento
- ⚠️ Maior consumo de recursos
- ⚠️ Requer ChromeDriver

**Exemplo:**
```python
from app.scraper.example_dynamic_scraper import scrape_dynamic_site

articles = await scrape_dynamic_site("https://example.com")
```

## Criando um Novo Scraper

### Para sites estáticos (BeautifulSoup):

```python
from app.scraper.base import BaseScraper
import httpx
from bs4 import BeautifulSoup

class MyStaticScraper(BaseScraper):
    async def fetch(self, url: str) -> str:
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            return response.text
    
    def parse(self, html: str) -> list[dict]:
        soup = BeautifulSoup(html, "lxml")
        # Sua lógica de parsing aqui
        return articles
```

### Para sites dinâmicos (Selenium):

```python
from app.scraper.selenium_scraper import SeleniumScrollScraper
from bs4 import BeautifulSoup

class MyDynamicScraper(SeleniumScrollScraper):
    def parse(self, html: str) -> list[dict]:
        soup = BeautifulSoup(html, "lxml")
        # Sua lógica de parsing aqui
        return articles
```

## Configurações

Todas as configurações estão em `.env`:

```bash
# BeautifulSoup
SCRAPER_TIMEOUT=30
SCRAPER_MAX_RETRIES=3

# Selenium
SELENIUM_HEADLESS=true
SELENIUM_WAIT_TIMEOUT=10
SELENIUM_PAGE_LOAD_TIMEOUT=30
SELENIUM_SCROLL_PAUSE_TIME=2.0
SELENIUM_MAX_SCROLLS=10
```

## Boas Práticas

1. **Respeite robots.txt** - Sempre verifique as regras do site
2. **Use rate limiting** - Não sobrecarregue o servidor
3. **User-Agent apropriado** - Identifique seu bot corretamente
4. **Tratamento de erros** - Timeouts, elementos ausentes, mudanças de layout
5. **Retry com backoff** - Já implementado no HNScraper
6. **Logging** - Registre sucessos e falhas

## Troubleshooting

### Selenium não inicia
```bash
# Instale o ChromeDriver automaticamente
pip install webdriver-manager
```

### Timeout errors
- Aumente `SELENIUM_PAGE_LOAD_TIMEOUT`
- Aumente `SELENIUM_WAIT_TIMEOUT`

### Elementos não encontrados
- Verifique se o site mudou a estrutura HTML
- Use `WebDriverWait` para elementos dinâmicos
- Adicione logs para debugar seletores
