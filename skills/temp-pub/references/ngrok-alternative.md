# ngrok as an alternative (opt-in)

By default temp-pub uses Cloudflare Quick Tunnels: zero account, no signup, works out of the
box. If you need things Quick Tunnels don't offer, ngrok is an alternative. It requires a
(free) signup and manual configuration.

## When ngrok makes sense

- **Stable subdomain** across sessions (requires a paid plan)
- **Basic auth** on the tunnel (`ngrok http --basic-auth user:pass`)
- **Explicit region routing** (better latency in specific scenarios)
- **Rich local inspector** at `http://127.0.0.1:4040` for HTTP debugging

## ngrok setup (manual, not managed by the skill)

1. **Install**:
   ```bash
   brew install ngrok          # macOS
   ```
   Linux: download the tarball from https://ngrok.com/download.

2. **Account**: go to https://dashboard.ngrok.com/signup and register with email or social
   login (GitHub/Google). No credit card required for the free tier.

3. **Authtoken**: go to https://dashboard.ngrok.com/get-started/your-authtoken, copy the
   token, and run:
   ```bash
   ngrok config add-authtoken <TOKEN>
   ngrok config check
   ```

## Manual use (ngrok serves file:// directly)

Unlike cloudflared, ngrok has a built-in file server, so no need for Python http.server:
```bash
ngrok http "file:///absolute/path/to/folder"
```
The public URL appears on stdout; you also find it at `http://127.0.0.1:4040/api/tunnels`.

To stop: Ctrl+C in the terminal where it runs.

## When NOT to use ngrok

- For most use cases (sharing a PDF with a client, sending a screenshot, exposing a local
  build): Cloudflare Quick Tunnels cover everything without an account.
- If you don't want to create yet another account: stick with cloudflared.
