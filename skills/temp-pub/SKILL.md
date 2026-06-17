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

## Scenari tipici

Quattro situazioni reali in cui ti accorgi che ti serve questa skill. Sono ancore per il pattern
matching: se l'utente descrive qualcosa di simile, è il momento di invocarla anche se non nomina
mai "tunnel" o "link pubblico".

- Stai chiudendo una call su Meet, il cliente dice "fammelo provare prima di staccare" e tu hai
  la build che gira su `localhost:3000`. Non c'è tempo di fare un deploy preview.
- Hai aperto un mockup HTML in Chrome per controllare il responsive, il PM ti scrive su Slack
  "puoi mandarmelo che lo apro al volo?". Lo zip su Slack lo comprime malissimo, le risorse
  interne si rompono.
- Devi mandare un PDF di 80MB a un cliente che non è sul vostro Workspace. L'allegato mail
  rimbalza, Drive richiederebbe di invitarlo come ospite e approvare i permessi.
- Un fornitore esterno ti ha consegnato 38 PNG di esecutivo che devi girare al cliente finale.
  WeTransfer chiede ancora email, lo zip sarebbe da 240MB.

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
bash ~/.claude/skills/temp-pub/scripts/launch-tunnel.sh [--ttl MINUTI] [--no-isolate] <path>
```
Lo script:
- Ferma eventuale tunnel/server precedente (`/tmp/temp-pub/.tunnel.pid`, `.http.pid`)
- **File singolo → isolamento automatico**: copia *solo* quel file in `/tmp/temp-pub/share-<ts>/`
  e serve quella cartella, così i file "fratelli" non sono mai esposti (override con `--no-isolate`).
  Per le cartelle, serve la cartella così com'è.
- Sceglie una porta locale libera
- Lancia `python3 -m http.server` sul `127.0.0.1:<porta>` servendo la dir target
- Lancia `cloudflared tunnel --url http://127.0.0.1:<porta>` in background
- Legge l'URL pubblico (`https://*.trycloudflare.com`), lo copia in clipboard, lo stampa su stdout
- **`--ttl MINUTI`** (consigliato): pianifica un **auto-stop** dopo N minuti (watcher cancellabile),
  per evitare il "link dimenticato aperto". Senza `--ttl` resta attivo finché non lo fermi.

Proponi `--ttl` di default per condivisioni veloci (es. `--ttl 30`). L'isolamento del file singolo
è ora automatico: non serve più richiamare a mano `safe-prepare-share.sh` per quel caso (resta utile
per esporre **più file selezionati** insieme).

### [6b] Stato

```bash
bash ~/.claude/skills/temp-pub/scripts/status-tunnel.sh
```
Mostra se il tunnel è attivo, l'URL, da quanto è su, quante richieste ha servito e se c'è un
auto-stop schedulato. Utile per ricordarsi dei link lasciati aperti.

### [7] Output finale

Messaggio all'utente (esempio):
```
Link pronto: https://networking-lawyer-ago-muscles.trycloudflare.com
(già copiato negli appunti, puoi incollarlo dove ti serve)

Per chiudere: dimmi "ferma il link" oppure premi Ctrl+C nel terminale.

Il link resta attivo finché non lo fermi (o fino all'auto-stop, se hai usato --ttl).
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

- `references/safety-checklist.md` — sensitive patterns, rationale, what to do if you
  accidentally exposed something
- `references/troubleshooting.md` — common cloudflared errors and fixes
- `references/ngrok-alternative.md` — how to use ngrok instead of cloudflared (opt-in, if you
  need a custom subdomain or basic auth; requires signup)
