# Firecrawl fallback (siti JS-only / SPA)

Usa Firecrawl **solo** quando il percorso primario (`curl`/sitemap + passata
browser) non basta: tipicamente single-page app dove l'HTML statico è un guscio
vuoto e i media compaiono solo dopo il rendering JS, o quando vuoi una scoperta
pagine + estrazione più robusta in un colpo solo.

## Regola tassativa (globale)

NON usare mai il backend **Gemini/Google**. `GOOGLE_API_KEY` / `GEMINI_API_KEY`
nell'env sono credenziali aziendali. Firecrawl con la sua **`FIRECRAWL_API_KEY`**
dedicata è ok. Se la chiave non è impostata:

```bash
echo 'export FIRECRAWL_API_KEY="fc-..."' >> ~/.env && source ~/.env
```

## Pattern d'uso

1. **Mappa le pagine** (rendering JS incluso):
   ```bash
   firecrawl map https://example.com
   ```
2. **Scrape con HTML renderizzato** di ogni pagina, poi passa l'HTML risultante
   allo stesso estrattore della pipeline (`extract_assets`) — oppure usa
   `firecrawl scrape --formats html` e salva l'HTML in una cartella, quindi:
   ```bash
   python3 scripts/inventory.py --url https://example.com --pages <pagine dal map> --out ./out
   ```
   (Se preferisci, scrivi gli HTML renderizzati su file e adatta lo script a
   leggere HTML locali invece di rifare il fetch.)

## Quando NON serve Firecrawl

- Siti server-rendered (WordPress, la maggior parte dei CMS, marketing site
  classici): l'HTML statico contiene già i `<img>`. La pipeline `curl` basta.
- Lazy-load / background CSS: di solito coperti dalla **passata browser** con
  Chrome DevTools MCP, senza bisogno di Firecrawl.
