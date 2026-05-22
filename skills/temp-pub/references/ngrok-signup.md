# Signup ngrok — walkthrough in italiano

Guida pensata per essere letta da un utente al primo utilizzo di ngrok. Claude può rimandare qui
quando l'utente non capisce un passo dell'onboarding.

## 1. Apri la pagina di registrazione

URL: https://dashboard.ngrok.com/signup

Puoi registrarti con:
- **Email + password** (il modo standard, consigliato se vuoi tenere ngrok separato da altri account)
- **GitHub** (login con il tuo account GitHub)
- **Google** (login con un account Google)

Scegli quello che preferisci. Per uso professionale ti consiglio email aziendale.

## 2. Verifica email

Se hai scelto email+password, ngrok ti manda una mail di verifica. Aprila e clicca il link.

Se non arriva entro 1 minuto, controlla la cartella Spam.

## 3. Onboarding ngrok (pagine di benvenuto)

ngrok ti fa qualche domanda di profilazione (es. "perché usi ngrok?"). Puoi rispondere quello che
vuoi, non cambia nulla — oppure cercare un link "Skip" in fondo alla pagina.

## 4. Trova il tuo authtoken

URL diretto: https://dashboard.ngrok.com/get-started/your-authtoken

In questa pagina vedrai un blocco di testo simile a:
```
2abc...xyzDEF_4567...
```
(una stringa lunga di lettere e numeri, ~40-50 caratteri).

**Copia tutta la stringa** (il pulsante "Copy" in alto a destra del blocco fa il lavoro).

## 5. Incolla il token in Claude

Torna in Claude Code e incollalo. Claude lo salverà con il comando:
```
ngrok config add-authtoken <il-tuo-token>
```

Il token viene salvato in `~/.config/ngrok/ngrok.yml` sul tuo Mac. Da quel momento ngrok sa chi sei
e puoi creare tunnel.

## 6. (Opzionale) Nome del dispositivo

Se ngrok ti chiede una "description" o un "name" durante la creazione del token, suggerisco di
mettere il nome del Mac, per esempio:
- `macbook-mario`
- `mac-websolute`
- `imac-ufficio`

Serve solo a riconoscere il dispositivo, nel caso in futuro tu usi ngrok da più computer.

## Cosa NON serve fare

- **Non serve la carta di credito** — il piano gratuito è sufficiente per condividere file
- **Non serve installare nient'altro** — ngrok è autonomo, basta il binario installato via brew
- **Non serve un dominio custom** — ngrok ti dà un URL del tipo `xxx.ngrok-free.dev` ogni volta
