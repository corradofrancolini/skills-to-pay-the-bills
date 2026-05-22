# Safety checklist — temp-pub

File and folder patterns the skill must detect before exposing a path publicly.

## Critical patterns (always propose isolation)

| Pattern | Why it's dangerous |
|---|---|
| `.env`, `.env.*` | Credentials, API keys, DB passwords, OAuth tokens |
| `*.pem`, `*.key` | Private keys (TLS, JWT signing, GPG) |
| `id_rsa*`, `id_ed25519*`, `id_ecdsa*` | Private SSH keys |
| `credentials*`, `secrets*` | Generic credential files (AWS, GCP, custom) |
| `*.sqlite`, `*.db` | Local databases with real data, possibly PII |
| `.git/` | Full repo history, secrets leaked in past commits |
| `.aws/` | AWS CLI profiles with access keys |
| `.ssh/` | SSH keys, known_hosts, config |
| `.docker/config.json` | Registry tokens (Docker Hub, GHCR, ECR) |
| `.npmrc`, `.pypirc` | Publish tokens for public registries |
| `*.kubeconfig`, `kubeconfig` | Kubernetes cluster access |

## Soft patterns (warn, don't block)

| Pattern | Reason for the warning |
|---|---|
| `node_modules/` | Huge folder, slow to serve, rarely intentional |
| `.venv/`, `venv/`, `__pycache__/` | Same as above |
| Single files > 100 MB | Slow transfer for the recipient |
| Folders with > 500 files | Hard to navigate, probably not what the user wants to share |

## Hard rules (always refuse, no isolation can save these)

- Path is `$HOME` or `~` or a parent of home
- Path is `/`
- Path is a system directory: `/etc`, `/var`, `/usr`, `/bin`, `/sbin`, `/System`, `/Library`,
  `/private`, `/dev`, `/proc`, `/sys`

In these cases: refuse, explain it's too broad, ask for a more specific path.

## If you accidentally exposed something sensitive

1. **Stop the tunnel immediately** (`scripts/stop-tunnel.sh`).
2. **Rotate the exposed credentials**: change passwords, regenerate API keys, revoke OAuth tokens.
3. **If it was an SSH key**: remove it from `~/.ssh/authorized_keys` on the servers, generate a
   new keypair, update the hosts.
4. **If it was a Git repo**: assume history was read. For secrets leaked in past commits,
   consider tools like `git-filter-repo` or `BFG Repo-Cleaner`, and rotate the secrets anyway.
5. **Check the local HTTP server log** at `/tmp/temp-pub/.http.log` to see if anyone actually
   hit the URL (Python's `http.server` logs each request with timestamp, client IP, and path).

## Rationale for the "isolation in /tmp/temp-pub/" model

Instead of exposing the source directory, we copy only the desired files into a temporary
isolated folder (`/tmp/temp-pub/<timestamp>/`). Advantages:

- No risk of exposing sibling files by mistake (e.g. `index.html` next to `.env`)
- Trivial cleanup at end of session (`rm -rf /tmp/temp-pub/<timestamp>/`)
- Predictable path for debugging
