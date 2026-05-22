# Safety checklist — temp-pub

Pattern di file/cartelle che la skill deve rilevare prima di esporre un path al pubblico.

## Pattern critici (proponi sempre isolamento)

| Pattern | Perché è pericoloso |
|---|---|
| `.env`, `.env.*` | Credenziali, API key, password DB, token OAuth |
| `*.pem`, `*.key` | Chiavi private (TLS, JWT signing, GPG) |
| `id_rsa*`, `id_ed25519*`, `id_ecdsa*` | Chiavi SSH private |
| `credentials*`, `secrets*` | File di credenziali generiche (AWS, GCP, custom) |
| `*.sqlite`, `*.db` | Database locali con dati reali, eventualmente PII |
| `.git/` | Storia completa del repo, secret leakati in commit passati |
| `.aws/` | Profili AWS CLI con access key |
| `.ssh/` | Chiavi SSH, known_hosts, config |
| `.docker/config.json` | Token registry (Docker Hub, GHCR, ECR) |
| `.npmrc`, `.pypirc` | Token di publish su registry pubblici |
| `*.kubeconfig`, `kubeconfig` | Accesso a cluster Kubernetes |

## Pattern soft (warning, non blocco)

| Pattern | Motivo del warning |
|---|---|
| `node_modules/` | Cartella enorme, lenta da servire, raramente intenzionale |
| `.venv/`, `venv/`, `__pycache__/` | Idem |
| File singoli > 100 MB | ngrok free ha bandwidth limit |
| Cartelle con > 500 file | Difficile da navigare, probabilmente non è quello che vuoi condividere |

## Hard rules (rifiuta sempre, non c'è isolamento che tenga)

- Path è `$HOME` o `~` o un genitore della home
- Path è `/`
- Path è una cartella di sistema: `/etc`, `/var`, `/usr`, `/bin`, `/sbin`, `/System`, `/Library`,
  `/private`, `/dev`, `/proc`, `/sys`

In questi casi: rifiuta, spiega che è troppo ampio, chiedi un path più specifico.

## Se hai esposto per sbaglio qualcosa di sensibile

1. **Chiudi subito il tunnel** (`scripts/stop-ngrok.sh`).
2. **Ruota le credenziali esposte**: cambia password, rigenera API key, revoca token OAuth.
3. **Se era una chiave SSH**: rimuovila dai `~/.ssh/authorized_keys` dei server, genera nuova
   coppia, aggiorna gli host.
4. **Se era un repo Git**: assumi che la storia sia stata letta. Per secret leakati in commit
   passati, considera tool come `git-filter-repo` o `BFG Repo-Cleaner` e ruota i secret comunque.
5. **Controlla l'inspector ngrok** (http://127.0.0.1:4040) per capire se qualcuno ha effettivamente
   acceduto: ngrok mostra IP e richieste recenti.

## Razionale del modello "isolamento in /tmp/temp-pub/"

Anziché esporre la cartella sorgente, copiamo solo i file desiderati in una cartella temporanea
isolata (`/tmp/temp-pub/<timestamp>/`). Vantaggi:

- Nessun rischio di esporre file fratelli per sbaglio (es. `index.html` accanto a `.env`)
- Cleanup banale a fine sessione (`rm -rf /tmp/temp-pub/<timestamp>/`)
- Path predicibile per debugging
