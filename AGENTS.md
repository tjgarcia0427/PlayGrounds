# AGENTS.md — PlayGrounds build coordination protocol

Two independent agents build this repo: **Vision** (Muse) and **VISIONQUEST** (OpenClaw).
**Tj** owns the repo, sets direction, and merges. No one else merges.

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
5. **Identity ambiguity.** Who approved what, who wrote what. →
   Every action is attributed by the platform (commit author, reviewer,
   merger). No impersonation, ever — not even as a joke.
6. **Decision evaporation.** Agreements made in chat vanish by next session. →
   Decisions land as issue/PR comments or in docs. Chat messages are
   notifications only ("review requested on #15", "CI is green").

## The protocol

### Task ledger = GitHub Issues

- Every unit of work is an issue: problem statement, acceptance criteria,
  labels (`severity:critical|high|medium`, `area:...`).
- **Claiming:** assign yourself. Exactly one assignee at a time (the lease).
  Comment when you start; unassign + comment when blocked or handing off.
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

**No self-merge, ever.** Tj merges. This is load-bearing: while agent
identity on the platform is still unsigned stubs, Tj-as-merger is the one
human trust anchor in the loop.

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
| Tj merge                   | Settlement + human verification        |
| Commit hash                | Artifact digest                        |
| This file                  | Room policy                            |

## Migration path

When rooms + per-agent identity ship: issues become room tasks, branches/PRs
become artifact submissions against those tasks, CI remains the deterministic
check runner, and this file's rules are re-expressed as room policy. The
workflow doesn't change — only the substrate does. That migration is itself
the first real recursion test: two agents moving their own collaboration
onto the platform they're building.
