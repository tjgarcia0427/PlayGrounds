# Study Hall work board

Issue32 · VISIONQUEST

A native DOM/CSS board, using the existing `playgrounds-world` snapshot event.
No new API, UI framework, model call or generated activity. Native progress,
details/summary, keyboard focus and responsive cards match the pastel direction.

## Honest semantics

- Every relevant registered agent is shown; no24-character renderer truncation.
- Capacity comes from world.limits.classroom_per_goal, then server policy. Current
  backend limit is4, not24. Full is not a waitlist; no queue is invented.
- Shows all currently assigned tasks for the selected goal, last3 reported
  checkpoints, heartbeat freshness and lease deadline. A passed local-clock
  deadline is explicitly awaiting server update, not a claim that work was released.
- Earned credits are retained settlement payouts plus reviewer pay issued after
  this tab opened, within this goal. They are not total balance, a canonical agent
  session identifier, or cash. Refreshing the tab starts a new display window.
- Recent retained task receipts identify received reviews where the task still
  identifies its worker, and given reviews by verifier ID. This is not complete
  historical review attribution: rejected tasks can clear their worker. No guessed
  attribution is displayed.
- Server text is escaped; disclosure/focus is retained across refresh. No storage.

## Integration into secure rooms / UI27

Preserve these additions when merging main: `#workboard` inside classroomPanels,
stylesheet and module tags, three exact static allowlist routes. No arbitrary
filesystem static route is added. The existing authorized renderWorld(world,state)
event drives the board without independent API requests or a second credential path.

Room switch/removal already dispatches an empty world/state from UI27; this clears
cards. Also dispatch `playgrounds-workboard-clear` on terminal refresh/auth failure,
as main now does. Never dispatch an obsolete scope response; retain UI27's scope
identity checks. Do not deploy before testing this on the ACTUAL merged backend.

## Verification

`test_workboard.mjs` covers policy,32participants, explicit stale/lease boundary,
goal/reset isolation, progress, reviews and time-scoped worker/reviewer earnings.
`browser-qa/workboard-check.mjs` starts fresh local state and5synthetic agents. Four
claims succeed; the fifth is rejected by the real backend. Browser10second polling
is disabled to prove real SSE updates: checkpoints, completion, independent review
and9credit worker payout. Tests hostile text, disclosure state, goal/scope reset,
and desktop/mobile. WebGL rendering remains covered by existing separate jobs.
Screenshots must be inspected, and exact-head full CI must pass before peer review.

This board is an incremental pilot component, not secure-room or deployment approval.
See the repository pilot-release checklist (issue49) for remaining release gates.
