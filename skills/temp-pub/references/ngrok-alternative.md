# ngrok come alternativa (opt-in)

Per default temp-pub usa Cloudflare Quick Tunnels: zero account, niente registrazione,
funziona out of the box. Se invece servono cose che le Quick Tunnels non offrono, ngrok può
essere un'alternativa. Richiede registrazione (gratuita) e configurazione manuale.

## Quando ha senso ngrok

- **Subdomain stabile** tra una sessione e l'altra (richiede piano a pagamento)
- **Basic auth** sul tunnel (`ngrok http --basic-auth user:pass`)
- **Region routing** esplicito (latenza migliore in scenari specifici)
- **Inspector locale** ricco a `http://127.0.0.1:4040` per debugging HTTP

## Setup ngrok (manuale, non gestito dalla skill)

1. **Install**:
   ```bash
   brew install ngrok          # macOS
   ```
   Linux: scarica il tarball da https://ngrok.com/download.

2. **Account**: vai su https://dashboard.ngrok.com/signup e registrati con email o
   login social (GitHub/Google). Nessuna carta di credito richiesta per il free tier.

3. **Authtoken**: vai su https://dashboard.ngrok.com/get-started/your-authtoken,
   copia il blocco di testo e lancia:
   ```bash
   ngrok config add-authtoken <TOKEN>
   ngrok config check
   ```

## Uso a mano (ngrok serve file:// direttamente)

A differenza di cloudflared, ngrok ha un file server integrato, quindi non serve
python http.server:
```bash
ngrok http "file:///path/assoluto/della/cartella"
```
L'URL pubblico appare nello stdout; lo trovi anche su `http://127.0.0.1:4040/api/tunnels`.

Per fermare: Ctrl+C nel terminale dove gira.

## Quando NON usare ngrok

- Per la maggior parte dei casi d'uso (condividi un PDF a un cliente, manda uno screenshot,
  una build locale): Cloudflare Quick Tunnels copre tutto senza account.
- Se non vuoi creare un altro account: stai su cloudflared.
