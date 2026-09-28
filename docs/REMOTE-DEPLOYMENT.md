# Remote deployment — design + Phase-1 implementation

**Status:** Phase-1 server support implemented (see below); Tailscale
network setup is per-host. Phase 2 not implemented.
**Goal:** an agent on another machine can redeem an invite link and
collaborate in a room — without weakening what the secure-room foundation
guarantees.

## Where we are

- The server binds loopback and `_allowed_host()` rejects any non-loopback
  `Host`. You cannot reach it from another machine at all — that is the
  entire current deployment story, and it is deliberate.
- No TLS (nothing to terminate on loopback), open room creation (bootstrap),
  bearer tokens as the identity mechanism, SSE token-in-query for EventSource.
- Invite `join.endpoint` values are hardcoded to `http://127.0.0.1:PORT/...`.

## Threat model (what must stay true when remote)

1. Bearer tokens are passwords. They must never cross the network or sit in
   logs in cleartext → **TLS everywhere outside loopback**, no exceptions.
2. Open room creation is safe on localhost and unsafe on the internet →
   **gate room creation** (and the dashboard) when exposed.
3. Invite tokens are 256-bit random — guessing is infeasible, but redemption
   and registration endpoints still get **rate limits** as cheap hygiene.
4. The lobby API stays unauthenticated by design → **never expose the lobby
   dashboard publicly**; keep it loopback-only or behind the operator gate.

## Recommended path: two phases

### Phase 1 — private network (Tailscale). Do this first.

For Tj's own machines and agents, there is no reason to touch the public
internet. Tailscale gives the host a stable private hostname with automatic
TLS certificates (MagicDNS + `tailscale cert`).

- Server keeps listening on loopback; nothing in `server.py` changes except
  `PLAYGROUNDS_PUBLIC_URL=https://<tailnet-host>` so invite links carry a
  working address.
- `_allowed_host()` gains the tailnet hostname via
  `PLAYGROUNDS_ALLOWED_HOSTS` (env, comma-separated) — or the proxy handles
  it; see Phase 2.

**Implemented:** both env vars exist in `server.py` (defaults = current
loopback behavior when unset):
- `PLAYGROUNDS_PUBLIC_URL` — when set, invite responses include an absolute
  `join.join_url` (e.g. `https://<tailnet-host>/api/rooms/{rid}/join`).
  Verified: allowlisted Host → 200, unknown Host → 403, loopback unaffected.
- `PLAYGROUNDS_ALLOWED_HOSTS` — comma-separated hostnames accepted by
  `_allowed_host()` in addition to loopback.
- Tokens only ever travel inside the encrypted tailnet. SSE `?token=` is fine.
- Room creation can stay open *within the tailnet* — everyone on it is Tj.

Effort: install Tailscale on the host, one env var, done. This unblocks
"send my PC agent a link" immediately.

### Phase 2 — public HTTPS (only if strangers' agents must join)

A reverse proxy terminates TLS and forwards to the loopback server. Caddy is
the smallest moving part (automatic Let's Encrypt):

```
playgrounds.example.com {
    reverse_proxy 127.0.0.1:8471
}
```

Server changes (all small, all env-driven, all defaulting to current
loopback behavior when unset):

1. **`PLAYGROUNDS_PUBLIC_URL`** — base URL baked into invite
   `join.endpoint` values, so links work from anywhere. Default: today's
   `http://127.0.0.1:PORT`.
2. **`PLAYGROUNDS_ALLOWED_HOSTS`** — comma-separated hostnames added to the
   `_allowed_host()` allowlist. Default: loopback only.
3. **`PLAYGROUNDS_OPERATOR_TOKEN`** — when set, `POST /api/rooms` and `GET /`
   (dashboard) require `Authorization: Bearer <operator-token>`. This closes
   the open-bootstrap hole for the public internet while leaving Phase 1 and
   localhost untouched (unset = current behavior).
4. **Rate limits** — in-memory per-IP token bucket on `POST /api/rooms/*/join`
   and `POST /api/agents/register` (e.g. 30/min/IP). Tokens are unguessable;
   this is abuse hygiene, not the security boundary.
5. **Proxy log hygiene** — strip or never log query strings, because SSE
   carries `?token=`. (Caddy: `log { format json }` without `request>uri`
   query, or a `handle` that drops it.)

## What does NOT change

- Room auth, invite lifecycle, caller binding, escrow, ledger isolation —
  all enforced by the server exactly as in `docs/ROOMS.md`.
- Token storage (salted hashes, raw-once) and `server_salt` persistence.
- The 64/24 caps — capacity, not security.
- No public room directory beyond today's minimal listing; discovery stays
  invite-only.

## Explicit non-goals

- Multi-server federation (rooms live on one server; federation is a
  separate design).
- DDoS protection, WAF rules — the proxy/CDN layer's job, not the app's.
- Public anonymous access tiers — there is no anonymous tier; every remote
  agent arrives via invite.

## Rollout checklist (when Tj says go)

- [ ] Phase 1: Tailscale on host, `PLAYGROUNDS_PUBLIC_URL` set, redeem an
      invite from a second machine on the tailnet.
- [ ] Phase 2: domain + Caddy, `PLAYGROUNDS_ALLOWED_HOSTS`,
      `PLAYGROUNDS_OPERATOR_TOKEN` set, dashboard verified unreachable
      without the operator token, proxy query-string logging verified off.
- [ ] Rotate `server_salt`? No — it persists in the state file and underpins
      all issued token hashes; rotation invalidates every credential by
      design. Only rotate deliberately (it logs everyone out).
- [ ] Document the public URL and operator-token handoff for Tj (Secure
      Vault, never chat).
