# Troubleshooting — temp-pub

Errori comuni e fix. Quando li mostri all'utente, riformula nella sua lingua.

## cloudflared non parte / URL non leggibile

**Sintomo:** `launch-tunnel.sh` esce con "could not read the public URL from cloudflared".

**Diagnosi:**
1. Leggi `/tmp/temp-pub/.tunnel.log` per il messaggio reale.
2. Cause tipiche:
   - **Rete bloccata**: il log dice "failed to connect" → controlla connessione internet
     o firewall aziendale che blocca traffico verso Cloudflare (porta 7844 UDP per QUIC, 443).
   - **Porta locale non raggiungibile**: il log dice "connection refused on 127.0.0.1:<port>"
     → il python http.server non è partito; vedi sotto.
   - **Versione vecchia di cloudflared**: aggiorna con `brew upgrade cloudflared`.

## python http.server non parte

**Sintomo:** `/tmp/temp-pub/.http.log` mostra errore di binding o l'URL pubblico ritorna 502.

`launch-tunnel.sh` sceglie sempre una porta libera con `socket.bind(('127.0.0.1', 0))`,
quindi è raro. Se succede, verifica python3:
```bash
python3 --version
```
Su macOS python3 è di default presente; se manca, `brew install python3`.

## URL non risponde dall'esterno

1. Verifica che entrambi i processi siano vivi:
   ```bash
   cat /tmp/temp-pub/.tunnel.pid /tmp/temp-pub/.http.pid
   ps -p $(cat /tmp/temp-pub/.tunnel.pid) -p $(cat /tmp/temp-pub/.http.pid)
   ```
2. Verifica internet (`ping -c 1 cloudflare.com`).
3. Verifica che il server locale risponda:
   ```bash
   port=$(grep -oE 'http://127\.0\.0\.1:[0-9]+' /tmp/temp-pub/.tunnel.log | head -1 | grep -oE '[0-9]+$')
   curl -I "http://127.0.0.1:$port"
   ```
   Se il locale risponde ma il pubblico no, propagazione del tunnel lenta: rilancia.

## cloudflared non trovato dopo `brew install`

Dopo `brew install cloudflared`, il binario va in `/opt/homebrew/bin` (Apple Silicon) o
`/usr/local/bin` (Intel). Se `command -v cloudflared` non lo trova:
- Controlla che `$PATH` includa la directory corretta
- Apri una nuova shell, o `eval "$(/opt/homebrew/bin/brew shellenv)"` per Apple Silicon

## Linux: come installare cloudflared senza brew

Cloudflare distribuisce binari diretti per ogni architettura. Esempio amd64:
```bash
sudo curl -L --output /usr/local/bin/cloudflared \
  https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64
sudo chmod +x /usr/local/bin/cloudflared
cloudflared --version
```
Per arm64 / 386 / armhf sostituisci il suffisso. Lista completa:
https://github.com/cloudflare/cloudflared/releases/latest

## Tunnel troppo lento

Cloudflare Quick Tunnels girano sui POP più vicini. Se i destinatari sono lontani può
esserci latenza extra. Per file molto grandi considera Drive/Dropbox. Per scegliere la
region (opzione a pagamento di ngrok), vedi `ngrok-alternative.md`.

## Pagina di Cloudflare invece del file

Capita rarissimamente se il tunnel ha problemi. Rilancia con `launch-tunnel.sh`.

## Tunnel cade da solo

Cloudflare Quick Tunnels non hanno una scadenza esplicita, ma se cloudflared perde
connettività per qualche minuto il tunnel cade. Rilancia per ottenere un nuovo URL.

## Rete giù

`launch-tunnel.sh` fallisce, il log mostra "failed to connect to Cloudflare edge".

**Messaggio all'utente:** "Sembra che il Mac non riesca a raggiungere Cloudflare. Controlla
la connessione internet e riprova." Non mostrare lo stack trace tecnico.
