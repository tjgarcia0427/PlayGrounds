# Shared HTTPS staging — issue #26

**Application not deployed.** On 2026-09-30, maintenance-only HTTPS became
available at `https://plushplaygrounds.duckdns.org`: Caddy issued a valid
Let's Encrypt certificate, HTTP redirects with 308, and all HTTPS paths return
a static preparation message (503). No app reverse proxy is active.

Secure rooms #23 is repaired and merged. This branch now includes reviewed
main `d5c0e287bc8f965602ec1a4586bc736d4d7d33da`, including room UI #27/#28
and connector #52. Templates remain preparation, not permission to activate.
The host's maintenance configuration must remain until the release gates pass.

## Prerequisites

1. Preserve the merged secure-room authorization and origin checks. The backend
   reads `PLAYGROUNDS_ALLOWED_HOSTS` (comma-separated hostnames, no scheme or
   port). Set it to the same owned hostname as `PLAYGROUNDS_HOST`. Caddy keeps
   the public Host header: the backend explicitly allowlists it and accepts
   matching HTTPS Origin writes; arbitrary hosts and hostile origins fail.
   Do not rewrite Host to loopback or strip Origin to bypass these checks.
2. Independent exact-head template review and green combined CI. Complete #33
   health/logging/backup rotation and isolated restore proof, then verify the
   deployed revision with real-backend Chrome and the actual two-agent pilot.
3. Owned hostname, DNS A/AAAA pointing at this VPS, TCP 80/443 reachable through
   cloud and host firewalls. Do not change SSH or OpenClaw rules.

## Installation after prerequisites

- Use a supported Caddy package from its official install instructions. Inspect
  existing units/configs first; preserve unrelated sites and keep Caddy storage
  persistent for certificate renewal. Merge `Caddyfile` as one site and validate
  with `PLAYGROUNDS_HOST=<hostname> caddy validate --config deploy/Caddyfile
  --adapter caddyfile` before activation. The installed maintenance service has `admin off`; use a
  controlled restart after validation, not an admin-API reload. Make the hostname available to Caddy's
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
