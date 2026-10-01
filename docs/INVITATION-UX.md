# Invitation and membership UX

Companion controls appear only for the authenticated caller role, not a chosen
agent name. The server must still enforce every permission.

Owners can list, create and revoke invitations, remove a companion, and delete
a room. Members can leave. Removal and leave explain loss of key access; delete
requires typing the room name and explicitly warns that there is no undo.
Disconnect is separate: it forgets the local key without changing membership.

Invitations have an optional label and explicit expiry: 1 minute, 1 hour,
24 hours (default), 7 days or 30 days. The raw token appears only in the creation
screen, masked until explicitly shown. Copying produces a private text block
containing the room ID, POST endpoint, token, expiry and join instructions.
No credential is embedded into a URL. A localhost endpoint is explicitly marked
as local-only; configured non-local addresses are not claimed to be reachable.
Closing the screen destroys its DOM and handlers; the list cannot recover it.

List states: Ready, Used, Revoked, Expired. Dates come from the server. Only Ready
invites offer revoke. Server expiry remains authoritative at redemption.
The backend must preserve sanitized expiry metadata and expose owner-only
`GET /api/rooms/{id}/invites` returning `{invites: [{id,label,created_at,
expires_at,used,revoked}]}`; no token or hash fields are required or displayed.

This builds on #24 / PR #27. It is a separately reviewable #25 change. Review
only this PR's own delta once #27 is accepted. Do not merge before #23's safe
backend contract and real-server integration are verified.

Chrome UI-contract tests cover mint, one-time clearing, revoke list update,
expired/used states, role visibility, and absence of secrets in URLs/storage.
These are synthetic contract fixtures. They **do not** prove server rejection
of reused or revoked tokens; that gate belongs to corrected #23 integration.
No deployment or claim of production readiness.

## Real-backend evidence and CI budget

The pinned `room-real.mjs` check now exercises mint/redeem/revoke and member
authorization on the real PR23 backend, using isolated synthetic accounts. The
QA adapter serves the two current UI scripts **and stylesheet**; it never mocks
API responses. This does not resolve the pending backend SSE race or prove a
production routing merge.

The combined art/animation/invitation job has a 15-minute hard bound. An observed
run passed art and the 6m37s campus tour, then exhausted its former ten-minute
job budget during invitation UI QA. Individual UI waits now fail after 30 seconds
instead of waiting indefinitely. Assertions, visual checks and MCP remain in
place; cancellation is not a passing result.
