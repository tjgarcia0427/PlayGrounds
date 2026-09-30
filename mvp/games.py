"""Mini-games: credit-staked games agents play in playground mode.

v1: rock-paper-scissors, last-agent-standing elimination rounds.

Honest limits (documented, tested):
- Simultaneous rounds. The server holds every move hidden until the round
  closes, so there is no second-mover advantage. This is enforced by the
  server (moves are never exposed before reveal), not by cryptography — v1
  trusts the server.
- Timeouts: a round closes ROUND_TIMEOUT seconds after opening; any alive
  player who has not moved auto-plays a deterministic seeded choice, so
  stalled rounds always resolve.

Liveness design (no background threads):
- Timeout progression is *lazy*. The server runs no scheduler; every games
  API access first sweeps rounds open longer than ROUND_TIMEOUT. A round
  whose game sees no API traffic does not auto-advance — the next access
  closes it. Each sweep is guaranteed to make progress (missing moves are
  auto-filled), and MAX_TIMEOUT_ROUNDS bounds total stall time: a game
  whose rounds close by timeout that many times in a row is stalled out and
  terminal (all stakes refunded, pot not awarded — the exact rule is in
  close_round's docstring).

Threat model for seeded auto-moves (read this before relying on them):
- The fallback is *determinism for liveness, not randomness*. The seed is
  derived from public inputs (game id, round, agent id), so anyone can
  compute what an absent player will auto-play. This is accepted because
  auto-moves only ever apply to players who failed to move before the
  timeout, and their purpose is to keep the game moving, not to be
  unpredictable. A present player gains no advantage from predicting an
  absent player's fallback — the absent player already forfeited the round
  by not moving. Do not use auto-moves anywhere unpredictability matters.

- Credits are internal and non-cash. Stakes move through the caller's
  credit ledger; this module only reports the deltas.

The engine is pure: it mutates plain game dicts and reports credit moves
and events. Persistence, auth, SSE and the ledger belong to the server.
"""

import random

RPS_MOVES = ("rock", "paper", "scissors")
_BEATS = {"rock": "scissors", "scissors": "paper", "paper": "rock"}

MIN_PLAYERS = 2
MAX_PLAYERS = 16
ROUND_TIMEOUT = 120.0  # seconds per round before auto-play
# Consecutive timeout-closed rounds before a game is stalled out and
# terminal (refunded). Bounds total stall time to
# MAX_TIMEOUT_ROUNDS * ROUND_TIMEOUT per game with zero genuine moves.
MAX_TIMEOUT_ROUNDS = 10


def _err(code, error):
    return {"code": code, "error": error}


def new_game(game_id, kind, creator_id, label, stake, max_players, now):
    """Create an open game. Returns (game, None) or (None, error)."""
    if kind != "rps":
        return None, _err(400, "unknown game kind")
    if not isinstance(label, str):
        return None, _err(400, "label must be a string")
    if isinstance(stake, bool) or not isinstance(stake, (int, float)) \
            or not 0 <= stake <= 1000000:
        return None, _err(400, "stake must be a number 0..1000000")
    if isinstance(max_players, bool) or not isinstance(max_players, int) \
            or not MIN_PLAYERS <= max_players <= MAX_PLAYERS:
        return None, _err(400, f"max_players must be {MIN_PLAYERS}..{MAX_PLAYERS}")
    game = {
        "id": game_id, "kind": kind, "label": label[:80],
        "creator": creator_id, "created_at": now,
        "stake": round(float(stake), 2), "max_players": max_players,
        "players": [creator_id], "status": "open",
        "round": 0, "round_opened_at": None,
        "timeout_streak": 0,
        "alive": [creator_id], "moves": {}, "rounds": [],
        "pot": round(float(stake), 2),
        "champion": None, "finished_at": None,
    }
    return game, None


def join_game(game, agent_id, now):
    """Seat an agent. Returns (credit_delta, error): delta is negative stake."""
    if game["status"] != "open":
        return 0, _err(409, "game is not open for joining")
    if agent_id in game["players"]:
        return 0, _err(409, "already seated")
    if len(game["players"]) >= game["max_players"]:
        return 0, _err(409, "game is full")
    game["players"].append(agent_id)
    game["alive"].append(agent_id)
    game["pot"] = round(game["pot"] + game["stake"], 2)
    return -game["stake"], None


def start_game(game, caller_id, now):
    """The creator opens round 1. Returns error or None."""
    if game["status"] != "open":
        return _err(409, "game already started")
    if caller_id != game["creator"]:
        return _err(403, "only the creator can start the game")
    if len(game["players"]) < MIN_PLAYERS:
        return _err(409, f"need at least {MIN_PLAYERS} players to start")
    game["status"] = "running"
    game["round"] = 1
    game["round_opened_at"] = now
    game["moves"] = {}
    return None


def _auto_move(game, agent_id):
    # Per-player/per-round derivation: every absent player gets their own
    # deterministic move, so a round of absent players does not degenerate
    # into a uniform tie that replays forever. The seed is public inputs
    # only (game id + round + agent id) — see the module docstring's threat
    # model: this is determinism for liveness, NOT randomness.
    rng = random.Random(f"{game['id']}:{game['round']}:{agent_id}")
    return rng.choice(RPS_MOVES)


def submit_move(game, agent_id, move, now):
    """Record a hidden move. Auto-closes the round when all alive players
    have moved. Returns (events, error)."""
    if game["status"] != "running":
        return [], _err(409, "game is not running")
    if agent_id not in game["alive"]:
        return [], _err(403, "agent is not alive in this game")
    if agent_id in game["moves"]:
        return [], _err(409, "move already submitted this round")
    if move not in RPS_MOVES:
        return [], _err(400, f"move must be one of {', '.join(RPS_MOVES)}")
    game["moves"][agent_id] = move
    if set(game["moves"]) >= set(game["alive"]):
        return close_round(game, now), None
    return [], None


def _resolve_rps(moves):
    """Elimination: a player survives iff nobody's move beats theirs.
    Returns (survivors, eliminated). A full tie (or a beats-cycle) replays."""
    alive = list(moves)
    beaten = {p for p in alive
              for q in alive if q != p and _BEATS[moves[q]] == moves[p]}
    survivors = [p for p in alive if p not in beaten]
    if not survivors or len(survivors) == len(alive):
        return alive, []  # tie: everybody replays
    return survivors, [p for p in alive if p not in survivors]


def close_round(game, now, timed_out=False):
    """Reveal moves, eliminate, and either open the next round or finish.
    Auto-plays seeded moves for anyone past the timeout. Returns events.

    Exact stall rule: close_round always fills missing moves with
    deterministic seeded choices, so a stalled round can never hang the
    game. The server sweeps rounds open longer than ROUND_TIMEOUT and calls
    this with timed_out=True. A round closed by the timeout sweep
    increments the game's timeout_streak; a round closed by genuine play
    (all alive players submitted moves) resets it to 0. When the streak
    reaches MAX_TIMEOUT_ROUNDS the game is terminal-stalled: status
    becomes "stalled", every seated player is refunded their full stake,
    and the pot is NOT awarded. A game_stalled event carries the refunds.
    """
    if game["status"] != "running":
        return []
    auto = {}
    for aid in game["alive"]:
        if aid not in game["moves"]:
            game["moves"][aid] = _auto_move(game, aid)
            auto[aid] = game["moves"][aid]
    if timed_out:
        game["timeout_streak"] = game.get("timeout_streak", 0) + 1
    else:
        game["timeout_streak"] = 0
    revealed = dict(game["moves"])
    survivors, eliminated = _resolve_rps(revealed)
    events = [{
        "type": "round_closed", "game_id": game["id"], "round": game["round"],
        "moves": revealed, "auto_moves": auto,
        "eliminated": eliminated, "survivors": survivors,
        "timed_out": timed_out,
        "timeout_streak": game["timeout_streak"],
    }]
    game["rounds"].append({"round": game["round"], "moves": revealed,
                           "eliminated": eliminated, "auto_moves": auto,
                           "timed_out": timed_out})
    if game["timeout_streak"] >= MAX_TIMEOUT_ROUNDS:
        game["status"] = "stalled"
        game["finished_at"] = now
        refunds = [(aid, game["stake"]) for aid in game["players"]]
        events.append({"type": "game_stalled", "game_id": game["id"],
                       "round": game["round"],
                       "timeout_streak": game["timeout_streak"],
                       "refunds": refunds,
                       "reason": (f"no genuine move for {MAX_TIMEOUT_ROUNDS} "
                                  "consecutive timeout rounds; stakes refunded")})
        return events
    if len(survivors) == 1:
        game["status"] = "finished"
        game["champion"] = survivors[0]
        game["finished_at"] = now
        events.append({"type": "game_finished", "game_id": game["id"],
                       "champion": survivors[0], "pot": game["pot"],
                       "rounds": game["round"]})
    else:
        game["alive"] = survivors
        game["round"] += 1
        game["round_opened_at"] = now
        game["moves"] = {}
    return events


def cancel_game(game, caller_id, now):
    """Creator cancels: stakes refunded.
    Returns (refunds, error); refunds = [(agent_id, amount)].

    Cancellation is terminal and idempotent at the credit level: cancelling
    an already-terminal game (finished, cancelled, or stalled) is rejected
    with a 409 and returns NO refunds, so repeat cancels can never mint
    credits."""
    if game["status"] not in ("open", "running"):
        return [], _err(409, f"game is terminal ({game['status']})")
    if caller_id != game["creator"]:
        return [], _err(403, "only the creator can cancel")
    game["status"] = "cancelled"
    game["finished_at"] = now
    refunds = [(aid, game["stake"]) for aid in game["players"]]
    return refunds, None


def public_view(game):
    """What the API may show. Current-round moves stay hidden from everyone
    until revealed; past rounds are public via the rounds history.

    There is deliberately NO viewer-specific field. The lobby has no
    authenticated agent identity on this branch (see server policy), so a
    `your_move` field could only be keyed off a caller-supplied agent_id —
    which discloses any player's move to anyone who names them. Until
    per-agent auth ships (issue #35), current-round moves are hidden from
    all readers equally; an agent that already moved can confirm via
    `moves_submitted`, which lists agent ids (not moves)."""
    view = {k: v for k, v in game.items() if k != "moves"}
    view["moves_submitted"] = sorted(game.get("moves", {}))
    return view
