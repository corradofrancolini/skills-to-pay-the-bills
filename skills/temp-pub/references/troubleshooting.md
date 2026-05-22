# Troubleshooting — temp-pub

Errori comuni e fix. Tutti i messaggi rivolti all'utente sono in italiano.

## ngrok non parte / URL non leggibile

**Sintomo:** `launch-ngrok.sh` esce con "non sono riuscito a leggere l'URL pubblico".

**Diagnosi:**
1. Leggi `/tmp/temp-pub/.ngrok.log` per il messaggio reale.
2. Cause tipiche:
   - **Authtoken non configurato**: il log dice "authentication failed". → Lancia il flusso
     authtoken dell'onboarding.
   - **Port 4040 occupata**: il log dice "address already in use". → `lsof -i :4040` per
     trovare il processo, poi `kill <PID>`.
   - **ngrok già in esecuzione**: c'è già un'altra istanza. Chiudila o usa
     `scripts/stop-ngrok.sh`.

## Tunnel scaduto — ERR_NGROK_3200

ngrok free ha sessioni limitate nel tempo. Quando scade:
- L'URL smette di rispondere
- L'inspector mostra "tunnel session expired"

**Fix:** rilancia il tunnel con `scripts/launch-ngrok.sh`. L'URL pubblico cambia.

Avverti l'utente: "I link gratuiti hanno durata limitata, te ne genero uno nuovo".

## Pagina interstiziale del browser (ngrok free)

ngrok free mostra una pagina di warning prima del contenuto reale. È normale, NON è un errore.

**Cosa dire all'utente:** "Chi apre il link vedrà una pagina di avviso ngrok, deve cliccare
'Visit Site' per procedere. È normale sul piano gratuito."

**Workaround:** aggiungere header `ngrok-skip-browser-warning: true` alle richieste HTTP — utile
solo per chiamate API, non per browser umani.

## URL non risponde dall'esterno

1. Verifica che il processo sia attivo:
   ```bash
   cat /tmp/temp-pub/.ngrok.pid
   ps -p $(cat /tmp/temp-pub/.ngrok.pid)
   ```
2. Verifica che il PC abbia internet (`ping -c 1 ngrok.com`).
3. Apri l'inspector locale: `http://127.0.0.1:4040`. Se l'inspector non risponde, ngrok è morto.
4. Se l'inspector risponde ma il pubblico no, può essere un blocco firewall lato rete cliente
   (raro ma succede in alcune VPN aziendali).

## ngrok non trovato dopo `brew install`

Su macOS, dopo `brew install ngrok`, il binario va in `/opt/homebrew/bin` (Apple Silicon) o
`/usr/local/bin` (Intel). Se `command -v ngrok` non lo trova:
- Verifica `echo $PATH` include la directory corretta
- Su shell nuova: `eval "$(/opt/homebrew/bin/brew shellenv)"` per Apple Silicon

## Linux: come installare ngrok senza brew

ngrok non distribuisce via apt/yum. Procedura:
1. Scarica da https://download.ngrok.com/linux (architettura corretta)
2. Estrai: `tar xvzf ~/Downloads/ngrok-v3-stable-linux-amd64.tgz -C /usr/local/bin`
3. Verifica: `ngrok version`
4. Procedi col flusso authtoken normale

## Token rifiutato (`ngrok config check` fallisce)

Cause:
- Token incollato parziale → "incolla di nuovo il token per intero"
- Token revocato lato dashboard → "genera un nuovo token dalla dashboard ngrok"

Mai mostrare il token in chiaro nei messaggi di errore.

## Rete giù

`launch-ngrok.sh` fallisce, il log mostra "failed to connect to ngrok server".

**Messaggio all'utente:** "Sembra che il Mac non riesca a raggiungere ngrok.com. Controlla la
connessione internet e riprova."

Non mostrare lo stack trace tecnico di ngrok.
