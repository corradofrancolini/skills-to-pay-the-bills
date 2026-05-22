---
name: temp-pub
description: |
  Crea un link pubblico temporaneo a partire da un file o cartella sul computer locale, da condividere
  rapidamente con clienti o colleghi. Usa SEMPRE questa skill quando l'utente vuole "far vedere",
  "passare", "mandare", "mostrare", o "condividere" qualcosa che ha sul proprio Mac/PC senza
  inviarlo per email o caricarlo su Google Drive — anche se non menziona esplicitamente "tunnel",
  "ngrok", o "URL pubblico". Casi d'uso tipici: condividere un HTML statico, una demo locale, un PDF,
  uno screenshot, una cartella di asset, una build di sviluppo. Gestisce installazione e configurazione
  automatica per chi non ha mai usato strumenti di tunneling. Creates a temporary public URL from a
  local file or folder for quick sharing — use whenever the user wants to share, expose, show, or
  send something from their local machine without uploading to cloud storage.
---

# temp-pub

Crea un link pubblico temporaneo per un file o cartella locale, senza email o cloud storage.
Backend unico: ngrok (free tier).

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

- **Lingua user-facing:** italiano, sempre. Tono colloquiale, uso del "tu".
- **Lunghezza:** conferme in 1 frase, spiegazioni in 2-3 frasi. Niente paragrafi lunghi.
- **No emoji.**
- **Sicurezza:** non mostrare mai l'authtoken ngrok nelle risposte, nemmeno parzialmente.

## Rileva il livello dell'utente

Se l'utente menziona `ngrok` per nome, parla di "tunnel", "authtoken", "port forwarding",
o passa un path assoluto preciso → modalità rapida, salta i preamboli educativi.

Altrimenti → modalità guidata: spiega brevemente cosa stai facendo a ogni passo importante.

## Flusso principale

```
[1] Conferma cosa esporre (file o cartella, path completo)
[2] scripts/check-prerequisites.sh → JSON {brew, ngrok, authtoken, platform}
[3] Se manca qualcosa → onboarding (sezione sotto)
[4] Safety check sul path
[5] Se file sensibili → proponi isolamento via scripts/safe-prepare-share.sh
[6] scripts/launch-ngrok.sh <path> → URL + PID, URL già in clipboard
[7] Output finale all'utente con URL, istruzioni chiusura, link inspector
```

### [1] Conferma input

Mai assumere il path. Se l'utente dice "questo HTML", chiedi: "Qual è il path completo?".
Se l'utente non specifica nulla, chiedi cosa vuole esporre.

### [2] Prerequisiti

```bash
bash ~/.claude/skills/temp-pub/scripts/check-prerequisites.sh
```

Output JSON: `{"platform":"darwin","brew":true,"ngrok":true,"authtoken":false}`.

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
- `node_modules/` → peso elevato
- File > 100 MB → bandwidth limit ngrok free
- Cartelle con > 500 file → proponi di esporre un subset

### [5] Isolamento (se richiesto)

```bash
bash ~/.claude/skills/temp-pub/scripts/safe-prepare-share.sh <file_o_cartella_da_includere> [...]
```
Lo script copia gli input in `/tmp/temp-pub/<timestamp>/` e stampa il path isolato su stdout.
Usa quel path come target per il lancio.

### [6] Lancio

```bash
bash ~/.claude/skills/temp-pub/scripts/launch-ngrok.sh <path>
```
Lo script:
- Ferma eventuale tunnel precedente (`/tmp/temp-pub/.ngrok.pid`)
- Lancia `ngrok http file://<dir>` in background (ngrok serve solo cartelle; se l'input è
  un file singolo, lo script serve la cartella genitore e appende il filename all'URL)
- Attende e legge l'URL pubblico via API locale `http://127.0.0.1:4040/api/tunnels`
- Copia l'URL completo in clipboard (`pbcopy` / `xclip` / `wl-copy`)
- Stampa l'URL su stdout

**Nota safety quando l'input è un file singolo:** servire la cartella genitore espone tutti i
file fratelli. Se il file è in una cartella "sporca" (es. `~/Desktop/` o un repo con `.env`),
proponi PRIMA l'isolamento via `safe-prepare-share.sh` anche se il file in sé è innocuo.

### [7] Output finale

Messaggio all'utente (esempio):
```
Link pronto: https://spectrum-vitally-refinance.ngrok-free.dev
(già copiato negli appunti, puoi incollarlo dove ti serve)

Per chiudere: dimmi "ferma il link" oppure premi Ctrl+C nel terminale.
Per vedere chi sta accedendo in tempo reale: apri http://127.0.0.1:4040 nel browser.

Il link resta attivo finché non lo fermi.
```

## Onboarding

Esegui solo i passi mancanti secondo l'output di `check-prerequisites.sh`. Tutti i passi sono
idempotenti: rilanciarli è sicuro.

### Brew mancante (macOS)

Messaggio:
```
Per installare ngrok mi serve Homebrew, il "gestore di pacchetti" del Mac
(pensa a un App Store da terminale). Te lo installo? Ci vorrà 1-2 minuti.
```
Comando (su conferma):
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```
Se l'utente rifiuta: spiega che può scaricare ngrok manualmente da https://ngrok.com/download.

### ngrok mancante

Messaggio:
```
Installo ngrok. È uno strumento che crea un "ponte" temporaneo tra il tuo Mac e
internet, in modo che chi ha il link possa vedere i tuoi file. Procedo? (~30 secondi)
```
Comando (macOS): `brew install ngrok`.
Per Linux: vedi `references/troubleshooting.md` (download tarball da ngrok.com).

### Account ngrok mancante

Messaggio:
```
ngrok richiede un account gratuito (serve solo per identificare il tuo Mac,
nessuna carta di credito). Ti apro la pagina di registrazione: completa la
procedura e poi torna qui e dimmi "fatto".
```
Comando: `open https://dashboard.ngrok.com/signup` (macOS) oppure `xdg-open` (Linux).

Se ngrok chiede un "description" durante la creazione del token, suggerisci il nome del
computer (es. `macbook-mario`). Per il walkthrough completo vedi
`references/ngrok-signup-it.md`.

### Authtoken mancante

Messaggio:
```
Adesso prendiamo la "chiave" che collega ngrok al tuo account. Te la apro nel
browser: copia il blocco di testo che vedi sotto "Your Authtoken" e incollalo qui.
```
Comando: `open https://dashboard.ngrok.com/get-started/your-authtoken`.

Attendi che l'utente incolli il token. Validazione:
- Formato alfanumerico (con eventuali `_`), almeno 40 caratteri
- Se non corrisponde → "Il token non sembra valido, controlla di averlo copiato per intero"

Salvataggio (NON loggare il token nelle risposte di Claude):
```bash
ngrok config add-authtoken <TOKEN>
```
Verifica:
```bash
ngrok config check
```

## Shutdown

Quando l'utente dice "ferma il link", "chiudi", "stop", "spegni il tunnel" o equivalenti:
```bash
bash ~/.claude/skills/temp-pub/scripts/stop-ngrok.sh
```
Conferma in una frase: "Tunnel chiuso."

## Cleanup a fine sessione

A fine sessione, se hai usato `safe-prepare-share.sh`, proponi:
```
Posso ripulire le cartelle temporanee in /tmp/temp-pub/? (le ho create durante la sessione)
```
Su conferma: `rm -rf /tmp/temp-pub/<timestamp>/` (mai `rm -rf /tmp/temp-pub/` intero se c'è
un tunnel ancora attivo — controlla `.ngrok.pid` prima).

## Riferimenti

- `references/safety-checklist.md` — pattern sensibili, razionale, cosa fare se hai esposto
  per sbaglio qualcosa
- `references/troubleshooting.md` — errori comuni di ngrok e fix in italiano
- `references/ngrok-signup-it.md` — walkthrough signup ngrok per utenti novizi
