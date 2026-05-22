---
name: temp-pub
description: |
  Create a temporary public URL from a local file or folder so the user can share it
  quickly with clients or colleagues without going through email or cloud storage. USE
  THIS SKILL whenever the user wants to share, expose, show, send, hand off, or pass
  something they have on their own machine to an external person — even when they don't
  explicitly say "tunnel", "public URL", or "cloudflared". Triggers on colloquial requests
  in any language: "voglio passare questo PDF a un cliente", "share this folder with
  someone outside the network", "mandami un link per questo screenshot", "expose this
  build", "fais voir ce HTML à quelqu'un", "manda este archivo a un cliente". Typical
  targets: a static HTML, a local demo, a PDF, a screenshot, an asset folder, a
  development build. Handles install and configuration end-to-end. User-facing replies
  mirror the user's prompt language automatically.
---

# temp-pub

Crea un link pubblico temporaneo per un file o cartella locale, senza email o cloud storage.
Backend: Cloudflare Quick Tunnels (zero account, niente registrazione).

## Quando usare

L'utente vuole "passare", "mandare", "far vedere", "mostrare", "condividere" qualcosa dal proprio
Mac/PC a una persona esterna. Tipicamente: HTML statico, PDF, screenshot, demo locale, build,
cartella di asset.

## Quando NON usare

- Invio via Gmail/email
- Upload su Google Drive / Dropbox / cloud storage
- Deploy su produzione (CI/CD)
- Pubblicazione permanente su blog o sito
- Creazione di domini o DNS

## Convenzioni di comunicazione

- **Lingua user-facing:** rispecchia la lingua del prompt dell'utente (se ti scrive in
  italiano rispondi in italiano, se in inglese rispondi in inglese, e così via). Le frasi
  di esempio dell'onboarding più sotto sono in italiano per chiarezza, ma sono *modelli di
  intento* — rendile nella lingua corrente dell'utente. Tono colloquiale (tu / you / du / tú
  secondo la lingua).
- **Lunghezza:** conferme in 1 frase, spiegazioni in 2-3 frasi. Niente paragrafi lunghi.
- **No emoji.**
- **Output degli script:** i messaggi degli script bundle sono in inglese (log tecnici).
  Quando li mostri all'utente, riformulali nella sua lingua.

## Rileva il livello dell'utente

Se l'utente menziona `cloudflared`, `tunnel`, `localhost`, `porta`, o passa un path assoluto
preciso → modalità rapida, salta i preamboli educativi.

Altrimenti → modalità guidata: spiega brevemente cosa stai facendo a ogni passo importante.

## Flusso principale

```
[1] Conferma cosa esporre (file o cartella, path completo)
[2] scripts/check-prerequisites.sh → JSON {brew, cloudflared, python3, platform}
[3] Se manca qualcosa → onboarding (sezione sotto)
[4] Safety check sul path
[5] Se file sensibili → proponi isolamento via scripts/safe-prepare-share.sh
[6] scripts/launch-tunnel.sh <path> → URL pubblico, copiato in clipboard
[7] Output finale all'utente con URL e istruzioni di chiusura
```

### [1] Conferma input

Mai assumere il path. Se l'utente dice "questo HTML", chiedi: "Qual è il path completo?".
Se l'utente non specifica nulla, chiedi cosa vuole esporre.

### [2] Prerequisiti

```bash
bash ~/.claude/skills/temp-pub/scripts/check-prerequisites.sh
```

Output JSON: `{"platform":"darwin","brew":true,"cloudflared":true,"python3":true}`.

Decidi cosa fare in base ai campi `false`.

### [3] Onboarding

Vedi sezione "Onboarding" sotto.

### [4] Safety check

**Hard rules (rifiuta sempre):**
- Path è `$HOME`, `~`, `/`, o un genitore della home → rifiuta e chiedi un path più specifico
- Path è una cartella di sistema (`/etc`, `/var`, `/usr`, `/System`, `/Library`) → rifiuta

**Pattern sensibili (proponi isolamento, non bloccare):**
```
.env  .env.*  *.pem  *.key  id_rsa*  credentials*  secrets*  *.sqlite  *.db
.git/  .aws/  .ssh/  .docker/config.json
```
Lista completa e razionale in `references/safety-checklist.md`.

Quando il path è una cartella, controlla la presenza di questi pattern (`find` con `-maxdepth 2`
è sufficiente per la maggior parte dei casi).

**Soft warning (avverti, non bloccare):**
- `node_modules/` → peso elevato, lascia procedere
- File > 100 MB → tempi di trasferimento lunghi per il destinatario
- Cartelle con > 500 file → proponi di esporre un subset

### [5] Isolamento (se richiesto)

```bash
bash ~/.claude/skills/temp-pub/scripts/safe-prepare-share.sh <file_o_cartella_da_includere> [...]
```
Lo script copia gli input in `/tmp/temp-pub/<timestamp>/` e stampa il path isolato su stdout.
Usa quel path come target per il lancio.

### [6] Lancio

```bash
bash ~/.claude/skills/temp-pub/scripts/launch-tunnel.sh <path>
```
Lo script:
- Ferma eventuale tunnel/server precedente (`/tmp/temp-pub/.tunnel.pid`, `.http.pid`)
- Sceglie una porta locale libera
- Lancia `python3 -m http.server` in background sul `127.0.0.1:<porta>` servendo la cartella target
- Lancia `cloudflared tunnel --url http://127.0.0.1:<porta>` in background
- Legge l'URL pubblico (`https://*.trycloudflare.com`) dal log di cloudflared
- Copia l'URL in clipboard (`pbcopy` / `xclip` / `wl-copy`)
- Stampa l'URL su stdout

**Nota safety quando l'input è un file singolo:** servire la cartella genitore espone tutti i
file fratelli a chi conosce i nomi. Se il file è in una cartella "sporca" (es. `~/Desktop/` o
un repo con `.env`), proponi PRIMA l'isolamento via `safe-prepare-share.sh` anche se il file
in sé è innocuo.

### [7] Output finale

Messaggio all'utente (esempio):
```
Link pronto: https://networking-lawyer-ago-muscles.trycloudflare.com
(già copiato negli appunti, puoi incollarlo dove ti serve)

Per chiudere: dimmi "ferma il link" oppure premi Ctrl+C nel terminale.

Il link resta attivo finché non lo fermi.
```

Nota: Cloudflare Quick Tunnels non ha un "inspector" locale come ngrok. Se serve vedere chi
sta accedendo, suggerisci di guardare il log di python http.server in `/tmp/temp-pub/.http.log`.

## Onboarding

Esegui solo i passi mancanti secondo l'output di `check-prerequisites.sh`. Tutti i passi sono
idempotenti: rilanciarli è sicuro.

### Brew mancante (macOS)

Messaggio:
```
Per installare cloudflared mi serve Homebrew, il "gestore di pacchetti" del Mac
(pensa a un App Store da terminale). Te lo installo? Ci vorrà 1-2 minuti.
```
Comando (su conferma):
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```
Se l'utente rifiuta: spiega che può scaricare cloudflared manualmente da
https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/.

### cloudflared mancante

Messaggio:
```
Installo cloudflared. È uno strumento di Cloudflare che crea un "ponte" temporaneo tra
il tuo Mac e internet, in modo che chi ha il link possa vedere i tuoi file. Niente
registrazione richiesta. Procedo? (~30 secondi)
```
Comando (macOS): `brew install cloudflared`.
Per Linux: vedi `references/troubleshooting.md` (binario da Cloudflare).

### Python 3 mancante

Praticamente sempre presente su macOS (anche se in alcune versioni va invocato come `python3`,
che è il comando che usiamo). Se davvero manca:
- macOS: `brew install python3`
- Linux: già presente quasi ovunque, oppure `apt install python3` / equivalente distro

### Niente account, niente token

Cloudflare Quick Tunnels non richiede registrazione. Dopo `brew install cloudflared` puoi
lanciare un tunnel immediatamente. Limiti: l'URL è casuale ogni volta (es.
`https://random-words.trycloudflare.com`), nessun custom subdomain, nessuna autenticazione.
Va benissimo per condividere un file a uso e getta.

## Shutdown

Quando l'utente dice "ferma il link", "chiudi", "stop", "spegni il tunnel" o equivalenti:
```bash
bash ~/.claude/skills/temp-pub/scripts/stop-tunnel.sh
```
Conferma in una frase nella lingua dell'utente (es. "Tunnel chiuso.", "Tunnel stopped.").

## Cleanup a fine sessione

A fine sessione, se hai usato `safe-prepare-share.sh`, proponi:
```
Posso ripulire le cartelle temporanee in /tmp/temp-pub/? (le ho create durante la sessione)
```
Su conferma: `rm -rf /tmp/temp-pub/<timestamp>/`. Mai `rm -rf /tmp/temp-pub/` intero se c'è
un tunnel ancora attivo — controlla `.tunnel.pid` e `.http.pid` prima.

## Riferimenti

- `references/safety-checklist.md` — pattern sensibili, razionale, cosa fare se hai esposto
  per sbaglio qualcosa
- `references/troubleshooting.md` — errori comuni di cloudflared e fix
- `references/ngrok-alternative.md` — come usare ngrok al posto di cloudflared (opt-in, se
  servono custom subdomain o autenticazione di base, richiede signup)
