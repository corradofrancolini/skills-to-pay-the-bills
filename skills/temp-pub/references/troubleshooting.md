# Troubleshooting — temp-pub

Common errors and fixes. When showing them to the user, rephrase in their language.

## cloudflared doesn't start / URL not readable

**Symptom:** `launch-tunnel.sh` exits with "could not read the public URL from cloudflared".

**Diagnosis:**
1. Read `/tmp/temp-pub/.tunnel.log` for the real message.
2. Typical causes:
   - **Network blocked**: the log says "failed to connect" → check internet, or a corporate
     firewall blocking traffic to Cloudflare (UDP port 7844 for QUIC, TCP 443).
   - **Local port unreachable**: the log says "connection refused on 127.0.0.1:<port>" → the
     Python http.server didn't start; see below.
   - **Stale cloudflared**: upgrade with `brew upgrade cloudflared`.

## Python http.server doesn't start

**Symptom:** `/tmp/temp-pub/.http.log` shows a binding error, or the public URL returns 502.

`launch-tunnel.sh` always picks a free port via `socket.bind(('127.0.0.1', 0))`, so this is
rare. If it happens, check python3:
```bash
python3 --version
```
On macOS python3 is present by default; if missing, `brew install python3`.

## URL doesn't respond from outside

1. Confirm both processes are alive:
   ```bash
   cat /tmp/temp-pub/.tunnel.pid /tmp/temp-pub/.http.pid
   ps -p $(cat /tmp/temp-pub/.tunnel.pid) -p $(cat /tmp/temp-pub/.http.pid)
   ```
2. Check internet (`ping -c 1 cloudflare.com`).
3. Check that the local server responds:
   ```bash
   port=$(grep -oE 'http://127\.0\.0\.1:[0-9]+' /tmp/temp-pub/.tunnel.log | head -1 | grep -oE '[0-9]+$')
   curl -I "http://127.0.0.1:$port"
   ```
   If local responds but public doesn't, tunnel propagation is slow: relaunch.

## cloudflared not found after `brew install`

After `brew install cloudflared`, the binary lands in `/opt/homebrew/bin` (Apple Silicon) or
`/usr/local/bin` (Intel). If `command -v cloudflared` doesn't find it:
- Check that `$PATH` includes the right directory
- Open a fresh shell, or run `eval "$(/opt/homebrew/bin/brew shellenv)"` on Apple Silicon

## Linux: installing cloudflared without brew

Cloudflare distributes per-architecture binaries directly. Example for amd64:
```bash
sudo curl -L --output /usr/local/bin/cloudflared \
  https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64
sudo chmod +x /usr/local/bin/cloudflared
cloudflared --version
```
For arm64 / 386 / armhf, swap the suffix. Full list:
https://github.com/cloudflare/cloudflared/releases/latest

## Tunnel too slow

Cloudflare Quick Tunnels run on the POPs closest to whoever accesses the URL. If the
recipients are far away there can be added latency. For very large files consider
Drive/Dropbox. To choose the region (a paid ngrok feature), see `ngrok-alternative.md`.

## Cloudflare error page instead of the file

Happens rarely if the tunnel has issues. Relaunch with `launch-tunnel.sh`.

## Tunnel drops on its own

Cloudflare Quick Tunnels don't have an explicit expiration, but if cloudflared loses
connectivity for several minutes the tunnel drops. Relaunch to get a new URL.

## Network down

`launch-tunnel.sh` fails, the log shows "failed to connect to Cloudflare edge".

**Message for the user:** "Looks like your machine can't reach Cloudflare. Check your
internet connection and try again." Don't show the cloudflared stack trace.
