# Shared HTTPS staging — issue #26

**Not deployed. Do not expose main or PR #23 at 59f6f5d2.** Security review
blockers remain in that PR. These templates are preparation, not a deployment
approval or proof that the application is safe over HTTPS.

## Prerequisites

1. Muse repairs #23 isolation, canonical persistence/restart, SSE revocation,
   nested A2A authorization, scoped lifecycle events and trusted HTTPS origins.
   Also fix public-mode auth/rate limits and supply #27/#28 UI contracts.
2. Independent exact-head review and green CI; integrate #27/#28. Check real
   backend + Chrome, not just the synthetic UI fixture.
3. Owned hostname, DNS A/AAAA pointing at this VPS, TCP 80/443 reachable through
   cloud and host firewalls. Do not change SSH or OpenClaw rules.

## Installation after prerequisites

- Use a supported Caddy package from its official install instructions. Inspect
  existing units/configs first; preserve unrelated sites and keep Caddy storage
  persistent for certificate renewal. Merge `Caddyfile` as one site and validate
  with `PLAYGROUNDS_HOST=<hostname> caddy validate --config deploy/Caddyfile
  --adapter caddyfile` before any reload. Make the hostname available to Caddy's
  service environment or replace only that placeholder in the staged site.
- Create an unprivileged `playgrounds` system user. Deploy a reviewed immutable
  commit under `/opt/playgrounds/releases/<sha>`; `/opt/playgrounds/current`
  points there. Use dependencies from that release, not a working branch.
- Install `runtime.env.example` as root-owned mode 0600
  `/etc/playgrounds/runtime.env`, replacing all placeholders. Generate operator
  token with Python `secrets.token_urlsafe(48)` directly into that file (never
  print or commit it); retrieve via a private interactive host terminal only.
- Install the systemd unit, verify it, then start **loopback-only** on 8472.
  Existing development port 8471 and its state are deliberately untouched.
- Verify state path and ownership on disk after a synthetic mutation/restart.
  Back up canonical state and its salt privately with restrictive permissions.
- Only then enable the Caddy site. The gateway on 18789 is never a proxy target.

## Required acceptance checks before distributing the URL

- TLS validates from a different machine, HTTP redirects to HTTPS.
- Non-sensitive join shell opens without operator credentials. Directory and
  creation APIs reject unauthenticated requests; no token-in-URL bootstrap.
- HTTPS same-origin writes succeed; hostile Origin fails; arbitrary Host fails.
- Create two synthetic rooms. Prove no cross-room/lobby state or hash disclosure,
  including after restart. No production credentials in test reports.
- Mint/redeem invite from another machine; reuse/expiry/revocation reject.
- Header-auth SSE delivers live events and closes on membership removal and
  room deletion. Test reconnect/replay and proxy-idle behavior.
- Room #27/#28 UI and navigation run against this backend in pinned Chrome.
- Caddy and app logs contain no bearer tokens/invites. Confirm unsolicited
  forwarded IP headers cannot change rate-limit identity. With this template's
  stripping, all proxy clients share the loopback budget until a reviewed
  trusted-proxy implementation replaces that behavior: safe but restrictive.

## Rollback

Disable only this Caddy site, stop only `playgrounds.service`, retain private
state/backups. Restore prior reviewed release + compatible state if necessary;
never rotate the salt or reset room data implicitly.

## Tunnel alternative

A named Cloudflare Tunnel is possible with account/domain setup, not a free
Quick Tunnel for this app: Quick Tunnels do not support SSE and have no uptime
SLA. Do not claim a random preview URL proves collaborative live-room support.

Sources: [Caddy automatic HTTPS](https://caddyserver.com/docs/automatic-https),
[Cloudflare Quick Tunnel limitations](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/do-more-with-tunnels/trycloudflare/).

Agent: VISIONQUEST
