# Pilot staging — 2026-10-03

Agent: VISIONQUEST. This is readiness evidence, **not a completed live pilot**.

## Reviewed backend staged

- Immutable backend release: `7042fac057827d3235c6652d4e1fff456c86594b` (ops #56).
- All five post-merge CI jobs passed in [run 37125133487](https://github.com/tjgarcia0427/PlayGrounds/actions/runs/37125133487).
- Dedicated `playgrounds` system user, reviewed hardened systemd service,
  root-owned immutable release and private runtime configuration.
- Listens on **127.0.0.1:8472 only**. Existing development port 8471 untouched.
- State directory 0700, state file 0600; operator configuration root-only 0600.
  Operator credential generated directly into the file, never output.
- Exact public Host allowlist and HTTPS Origin configured and read back.
- Synthetic live-service checks passed: unauthorized/query credential denial,
  hostile Host/Origin denial, two-room isolation, one-use invite redemption,
  authenticated persistence after restart, removed member rejection.
- Synthetic rooms removed through owner APIs; no real participants enrolled.
- Captured service logs contain none of the credentials used by the probe.
- Pre-run snapshot created as service account. Restored into a separate private
  temporary directory and booted on 127.0.0.1:8474; health and ledger checks
  passed, then the isolated process and temporary copy were cleaned up.
  The ops suite separately proves nonempty room/lobby task histories survive.

## Public and rollback state

Public HTTPS still returns the maintenance response (503). The original Caddy
site is preserved privately under `/var/backups/playgrounds-pilot/`; no public
application proxy has been enabled. Rollback at this first deployment is the
maintenance site plus stopping only `playgrounds.service`, retaining state and
snapshots. Never restore a whole old firewall/config snapshot.

## Remaining release gates

1. Independently review and merge #57 core-four character integration; verify
   the exact combined revision and inspect Chrome render evidence.
2. Stage that reviewed immutable release; take another private pre-run snapshot.
3. Validate the candidate Caddy configuration, then deployed HTTPS/credential,
   SSE, restart and cross-room contracts before distributing invitations.
4. Create a dedicated pilot room with a separate operator/owner identity.
   Generate invitations only when both participants are ready; hand them off
   through an established private credential mechanism, never GitHub/chat logs.
   No client installation or privilege expansion is assumed.
5. Both actual agents must connect and perform the task/review exchange in
   `PILOT-TEST-RUN.md`. Synthetic fixtures are not a substitute.

The core-four model module preserves the approved original shell-fur colors,
faces and accessories, with named rig joints and reactive squish. Crowd views
use 8 shells (6 narrow-screen); portraits use 48 (32 narrow-screen). Software
Chrome CI is evidence of correctness, not a real-device performance benchmark.
