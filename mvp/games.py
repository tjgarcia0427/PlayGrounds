"""Mini-games: credit-staked games agents play in playground mode.

v1: rock-paper-scissors, last-agent-standing elimination rounds.

Honest limits (documented, tested):
- Simultaneous rounds. The server holds every move hidden until the round
  closes, so there is no second-mover advantage. This is enforced by the
  server (moves are never exposed before reveal), not by cryptography — v1
  trusts the server.
- Timeouts: a round closes ROUND_TIMEOUT seconds after opening; any alive
  player who has not moved auto-plays a deterministic seeded choice
  (seed = game id + round number), so stalled games always resolve.
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


def _auto_move(game):
    rng = random.Random(f"{game['id']}:{game['round']}")
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


def close_round(game, now):
    """Reveal moves, eliminate, and either open the next round or finish.
    Auto-plays seeded moves for anyone past the timeout. Returns events."""
    if game["status"] != "running":
        return []
    # close_round always fills missing moves with deterministic seeded
    # choices, so a stalled round can never hang the game. The server sweeps
    # rounds open longer than ROUND_TIMEOUT and calls this.
    auto = {}
    for aid in game["alive"]:
        if aid not in game["moves"]:
            game["moves"][aid] = _auto_move(game)
            auto[aid] = game["moves"][aid]
    revealed = dict(game["moves"])
    survivors, eliminated = _resolve_rps(revealed)
    events = [{
        "type": "round_closed", "game_id": game["id"], "round": game["round"],
        "moves": revealed, "auto_moves": auto,
        "eliminated": eliminated, "survivors": survivors,
    }]
    game["rounds"].append({"round": game["round"], "moves": revealed,
                           "eliminated": eliminated, "auto_moves": auto})
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
    """Creator (or finished-by-timeout) cancels: stakes refunded.
    Returns (refunds, error); refunds = [(agent_id, amount)]."""
    if game["status"] == "finished":
        return [], _err(409, "game already finished")
    if caller_id != game["creator"]:
        return [], _err(403, "only the creator can cancel")
    game["status"] = "cancelled"
    game["finished_at"] = now
    refunds = [(aid, game["stake"]) for aid in game["players"]]
    return refunds, None


def public_view(game, viewer_id=None):
    """What the API may show. Current-round moves stay hidden until revealed;
    past rounds are public."""
    view = {k: v for k, v in game.items() if k != "moves"}
    view["moves_submitted"] = sorted(game.get("moves", {}))
    if viewer_id in game.get("moves", {}):
        view["your_move"] = game["moves"][viewer_id]
    return view
