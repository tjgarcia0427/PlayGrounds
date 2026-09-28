# A softer, clearer PlayGrounds

## Design direction

The interface should feel like the same place as the pastel campus: warm paper,
lilac accents, generous spacing, rounded surfaces and quiet movement. The scene
is the focal point; controls are supporting tools, not the main attraction.
System fonts avoid external requests and layout shifts. No paid services,
external analytics, remote fonts or new runtime library were added.

- Sidebar: collaboration **room** (authentication/data scope).
- Playground / Study Hall: **space** within that room (view only).
- Follow / camera: presentation only; task state moves agents.
- Goals, task board, companions and journal: readable work context.
- Native dialog: focused create, join and reconnect journeys.
- 44px primary controls, visible keyboard focus, mobile wrapping, system reduced
  motion, explicit empty states and inline failures.

## Existing-solutions preflight / references

- [W3C native dialog technique](https://www.w3.org/WAI/WCAG22/Techniques/html/H102):
  use the platform's focus containment, Escape and focus restoration rather than
  introducing a custom modal framework.
- [WAI dialog pattern](https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/):
  labels, focus and keyboard acceptance criteria.
- [GOV.UK error messages](https://design-system.service.gov.uk/components/error-message/):
  actionable errors in context, without relying only on color.
- [Lucide](https://github.com/lucide-icons/lucide) was evaluated as a free,
  maintained icon option. Not added in this pass: text labels and existing
  authored symbols are sufficient, without a new icon dependency.
- Existing Three.js, three-pathfinding and pinned Playwright-core are retained.
  No Figma/cloud connector is needed to edit and validate this code-native UI.

## Credentials and room boundaries

Room keys are passwords. Keep them only in page memory. No localStorage,
sessionStorage, console logging or URL query parameters. Create/join displays the
key once in a masked field with explicit reveal/copy and save acknowledgement.
It is displayed **before** secondary connection/directory requests so an
integration error cannot discard the only copy. Closing that screen clears it.
The browser clipboard is user-controlled; copying is explicit.

Fetch streaming sends Authorization headers for SSE; no native EventSource
query-token workaround. Switching rooms aborts all previous requests and
streams, clears old render data, and uses a scope generation to reject late
responses. Disconnect forgets that key. Reload forgets every key.

Room state containing global `rooms`, `auth` or `server_salt` is refused: the
unsafe pre-review #23 shape is not rendered. This client guard is not a fix for
the backend isolation vulnerabilities.

## Required backend contract (#23)

- `/api/rooms`: directory, create; `/api/rooms/{id}/join`: redeem.
- Authenticated room metadata includes `caller_agent_id`, owner and members.
- Authenticated `/state`, `/world`, `/ledger`, `/messages` stay scoped and omit
  global rooms/credentials. Bearer headers accepted on `/events`.
- Room owner identity is currently named after the room at creation; the UI
  discloses this instead of inventing a separate account/profile mechanism.
- Private data is cleared on failed refresh rather than silently retaining a
  previous authenticated snapshot.

Operator access has its own masked, memory-only key entry; it is used only for
lobby/directory/create requests, never for room requests. Members may join or
reconnect directly by room ID without enumerating the gated directory. The
backend must serve the non-sensitive login shell without operator auth. The
unsafe query-token propagation proposed by #23 must not replace this transport.
No remote deployment is performed here.

## Validation

`browser-qa/room-ui.mjs` is explicitly a **UI contract fixture**, not proof that
#23 is safe. It exercises create/save key, bad-key failure, switching, in-flight
response isolation, hostile room names, keyboard dialog close/return, mobile
layout, reload credential forgetting and no tokens in URLs/storage. Screenshots
are labeled synthetic; secret-bearing screens are never captured.

The existing real-server Chrome animation tour remains separate. Run both with
explicit Google Chrome on an x64 runner. Local ARM has no compatible Chrome.
Actual fixed-backend room integration remains a merge gate after #23 is fixed.
No claim of final WCAG certification or real-device GPU performance is made.
