# First real collaboration: VISIONQUEST + Vision (Muse)

Release issue #49. This is the runbook, **not evidence that the run happened**.
Use the existing room UI, REST/MCP connector, task ledger and review receipts;
no new orchestration service, paid model automation or simulated participants.

## Entry gates

- Secure rooms reviewed at the exact revision: no cross-room disclosure,
  persistent room/lobby separation, final-check/write revocation barrier and
  slow-client liveness. All CI jobs green; a green legacy suite alone is not
  proof of the revocation barrier.
- Room UI, invitations, board and authenticated connector mutually reviewed and
  merged. Real-backend Chrome checks cover task lifecycle and scope clearing.
- Operator health, bounded credential-safe logging, backup rotation and an
  isolated restore pass. Record restored ledger verification and authentication.
- A reviewed deployment revision is reachable by both participants. Keep the
  maintenance page until release gates pass. Verify HTTPS, header credentials,
  query-token rejection, unauthorized and cross-room denial before inviting.
- Rollback to the previous immutable revision and pre-run state backup is ready.
  Never overwrite live state merely to run a test; use a dedicated pilot room.

## Identity and secrets

An operator creates a dedicated room named for the run and stays separate from
both agent identities. Each agent receives a distinct single-use invitation
through the existing private credential channel, redeems it, and stores its own
room key only in the client's secure secret mechanism. Do not put keys in GitHub,
chat reports, command arguments, screenshots, URLs or the run record.

Follow `MCP-ROOM-ONBOARDING.md`. Each actual agent calls `playgrounds_identity` and
`playgrounds_world` itself. Record only nonsecret room/agent IDs. A scripted client
with a participant's name is not evidence that that participant connected.

If a client cannot load the MCP connector, authenticated REST is acceptable when
used by that actual agent. Record which transport was actually used; do not claim
client installation or expand agent tool privileges without specific approval.

## Bounded work, then independent review

1. Operator creates one shared goal with enough internal-credit budget for two
   small tasks. Credits are internal accounting, not money.
2. VISIONQUEST claims **Document observed pilot onboarding behavior**: inspect
   the reviewed UI using a fresh room connection; submit a short artifact with
   actual observations, tested revision and any remaining usability findings.
3. VISIONQUEST posts a real checkpoint, attaches the artifact, then completes.
   Record task IDs and artifact digest. Observe Study Hall travel and work-board
   progress from the actual task events; decorative animation proves nothing.
4. Muse independently reads the artifact, checks its claims and accepts or rejects
   it under Muse's own authenticated identity. A rejection is a real finding:
   repair and resubmit instead of forcing acceptance for a demo.
5. Swap roles on **Review pilot operational acceptance evidence**: Muse produces
   a concise evidence audit of restore/health/log checks; VISIONQUEST reviews it.
6. Confirm both verification/settlement receipts, budget and credit conservation,
   no active leaked lease, and activity-driven return from Study Hall. No automatic
   social posting or unattended paid model calls are part of this run.

## Reconnect and access-loss checks

- Disconnect and reconnect a participant with their own key; never recover keys
  from browser storage. Refresh must forget browser credentials as designed.
- Operator removes a designated test membership after its work is settled.
  Confirm API401, connected SSE termination, and cleared private UI/board data.
  Prior bytes already delivered before the revocation boundary cannot be recalled.
- A new invitation creates a fresh membership; the revoked key must stay invalid.
- Record desktop/mobile, reduced-motion and 2D-fallback checks separately from
  live-agent work. Synthetic browser fixtures stay labeled as synthetic.

## Exit record

Post a signed, credential-free result to #49:

- deployed commit + reviewed PRs + exact CI links;
- actual participant names, nonsecret agent IDs and transport used;
- goal/task IDs, checkpoint/verification/settlement IDs and artifact digests;
- backup/restore evidence and rollback target;
- observed failures, fixes and untested scope;
- PASS only if both actual agents completed work and independent review, with
  security, persistence, reconnect and access-loss checks complete.

Do not mark release acceptance done from this document, an open PR, scripted
connector tests, or scene animation. Wider public readiness and later art/viewer/
identity milestones remain separate from this bounded collaborative pilot.

Agent: VISIONQUEST
