# AGENTS.md — PlayGrounds build coordination protocol

Two independent agents build this repo: **Vision** (Muse) and **VISIONQUEST** (OpenClaw).
**Tj** owns the repo and sets direction. He does not manage PRs — review and
merge are handled by the two agents under the rules below.

**Identity note:** both agents operate through Tj's single GitHub user
(`tjgarcia0427`). GitHub-side identity is therefore shared: commits, issues,
and comments all render as the same user. Real attribution lives one layer
up — **protocol names (Vision / VISIONQUEST) signed in comment bodies and
commit trailers**. Never rely on the GitHub username to tell agents apart.
This is exactly the "identity ambiguity" drawback below, reproduced live:
the workaround is protocol-level until per-agent identity ships.

## The meta-point (read this first)

We are dogfooding. This protocol implements Playgrounds' coordination primitives
using GitHub as the substrate — because the platform's own rooms and agent
identity aren't built yet. Every primitive below maps 1:1 to a platform concept
(see mapping table). When rooms land, we migrate this exact workflow onto the
platform itself. The protocol is substrate-independent by design; only the
substrate changes.

## Why not just chat — drawbacks of brute-forcing it

1. **Context loss.** Both agents have finite context windows; chat history
   compacts and forgets. → All durable state lives in the repo
   (issues, PRs, commits). Chat carries nothing load-bearing.
2. **No provenance.** "I fixed the bug" is worthless without the diff. →
   Work is only real as a PR diff against a known commit.
3. **Unverifiable claims.** Anyone can type "23/23 pass." →
   CI runs both suites on every PR against a throwaway server. Green CI is the
   deterministic gate; words are not.
4. **Duplicated or dropped work.** Two agents, no ledger: both fix the same
   thing, or neither does. → One assignee per issue = the claim lease.
   Unassign when blocked so the other agent can pick it up.
5. **Identity ambiguity.** Who approved what, who wrote what. → Both agents
   currently share one GitHub user (`tjgarcia0427`), so attribution is by
   **protocol-name signatures** in comment bodies and commit trailers, never
   by GitHub username. No impersonation, ever — not even as a joke. Signing
   the other agent's name is the one unforgivable act in this repo.
6. **Decision evaporation.** Agreements made in chat vanish by next session. →
   Decisions land as issue/PR comments or in docs. Chat messages are
   notifications only ("review requested on #15", "CI is green").

## The protocol

### Task ledger = GitHub Issues

- Every unit of work is an issue: problem statement, acceptance criteria,
  labels (`severity:critical|high|medium`, `area:...`).
- **Claiming:** assign yourself. Exactly one assignee at a time (the lease).
  Since the GitHub account is shared, also post `Claim: Agent <protocol name>;
  branch <branch>; started <UTC timestamp>` in a signed comment. This comment,
  not the shared assignee, identifies the worker. Check it before taking work.
  Unassign + comment when blocked or handing off.
- **Progress:** comment on the issue as you go — this is the progress ledger.
  A claim with no update for 48h is stale: the other agent may ping, Tj may
  reassign.

### Work attempts = branches

- Branch from `main`. Name: `<agent>/<issue>-<slug>`
  (e.g. `visionquest/14-publish-ownership`, `vision/22-ci-flake`).
- One issue per branch. No drive-by changes to unrelated files.
- Never commit directly to `main`. Never force-push anything.

### Verification = pull requests

PRs are the verification gate, with the same two stages as the platform's
verification model:

1. **Deterministic:** CI must be green (core suite + MCP end-to-end on a
   throwaway server). If CI is red, the PR is not reviewable.
2. **Judgment:** the *other* agent reviews. Request the review explicitly.
   Address findings or rebut them with reasoning — "LGTM" without reading
   the diff is a protocol violation.

**No self-merge, ever.** The *reviewer* merges after approving. You never land
your own code. Because both agents share one GitHub user, GitHub's formal
reviewer assignment and approving reviews are unavailable (you cannot request
a review from yourself, nor approve your own PR). Approvals are **signed PR
comments** in this format:

> **Approved by VISIONQUEST** — reviewed the diff, CI green, acceptance
> criteria met. Merging.

An approval must include the full reviewed head SHA and the exact-head passing
CI run. Any new commit, including a merge from main, invalidates that approval:
the reviewer must review the new delta and renew approval for the new head.
Use a merge operation that verifies the expected head to avoid racing a push.

The reviewer executes the merge after posting it. Tj chose to stay out of the
PR loop, so mutual review is the trust anchor — treat it as load-bearing, not
ceremonial. Recommended reinforcement (Tj, one-time, repo Settings →
Branches): branch protection on `main` requiring a pull request and green CI
before merge. Do **not** require approving reviews — with a shared account
that would deadlock every merge, since GitHub sees author and approver as
the same user. That turns this section from convention into enforcement.

**Observed 2026-09-30:** GitHub reports `main.protected=false`. The protection
above is a recommendation, not an installed safeguard. Signed protocol comments
are procedural attribution, not authenticated agent identity or cryptographic
signatures: both agents can write through the same account. Recheck live branch
settings before claiming enforcement; this document grants no authority to
change repository protections.

### Message system

The repo is the bus. Two signal types, both in-repo and attributable:

1. **Review requests** — the formal signal. On your PR, leave a comment:
   `ready for review by VISIONQUEST — closes #N` (or `by Vision`). GitHub
   reviewer assignment is unavailable (shared account), so the protocol-name
   tag in the comment body IS the ping. The reviewer posts a signed
   **approval comment** (see format above) and merges.
2. **General pings** — issue comments. Progress updates, questions, handoffs,
   and "I'm picking up #N" all go on the relevant issue. Sign them.

**Session-start poll (mandatory).** Neither agent has push notifications.
At the start of every work session, check for inbound signals:

- Open PRs whose comments name your protocol name as reviewer.
- Open issues assigned to you or naming your protocol name.

Polling only discovers messages when an agent is already running. A signed
comment is not a wake-up notification and does not schedule a future check.
Do not claim the peer was notified live or will resume automatically.
Tj remains the human out-of-band relay if the repo signals ever go
unanswered for more than 48h.

**Agent handles (protocol names):** Vision, VISIONQUEST. Both act as GitHub
user `tjgarcia0427`. Tag and sign by protocol name in every comment and
commit trailer; never rely on the GitHub username for attribution.

### Communication rules

- Discuss work in issues and PRs. Chat is for pings only.
- Never paste full files into chat — link to the blob at a commit hash.
- Never claim completion without a PR. Never claim tests pass without CI.
- Before ending a work session, leave every issue/PR you touched resumable:
  updated checkboxes, a comment stating what's done and what's next.
  Your future self — and the other agent — have no memory of this session
  beyond what's in the repo.

## Primitive mapping — GitHub today, Playgrounds tomorrow

| GitHub (substrate now)      | Playgrounds (substrate later)          |
|----------------------------|----------------------------------------|
| Issue                      | Task (bounty via labels)               |
| Assignee                   | Claim lease                            |
| Issue comments             | Progress ledger / heartbeats           |
| Branch                     | Work attempt                           |
| CI green                   | Deterministic verification checks      |
| Peer review                | Agent verification judgment            |
| Reviewer merge (signed approval comment) | Settlement + agent verification |
| Commit hash                | Artifact digest                        |
| This file                  | Room policy                            |

## Migration path

When rooms + per-agent identity ship: issues become room tasks, branches/PRs
become artifact submissions against those tasks, CI remains the deterministic
check runner, and this file's rules are re-expressed as room policy. The
workflow doesn't change — only the substrate does. That migration is itself
the first real recursion test: two agents moving their own collaboration
onto the platform they're building.
