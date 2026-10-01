"""Engine tests for mvp/games.py. Pure: no server, no network."""
import random as _pyrandom
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import games

T = 1_000_000.0


def g2(stake=5, maxp=4):
    game, err = games.new_game("game_1", "rps", "a1", "Friday RPS", stake, maxp, T)
    assert err is None, err
    return game


# ---------- creation ----------
_, err = games.new_game("x", "chess", "a1", "l", 5, 4, T)
assert err["code"] == 400, "unknown kind rejected"
_, err = games.new_game("x", "rps", "a1", "l", -1, 4, T)
assert err["code"] == 400, "negative stake rejected"
_, err = games.new_game("x", "rps", "a1", "l", 5, 1, T)
assert err["code"] == 400, "max_players=1 rejected"
_, err = games.new_game("x", "rps", "a1", "l", 5, 99, T)
assert err["code"] == 400, "max_players=99 rejected"
game, _ = games.new_game("x", "rps", "a1", "l" * 200, 5, 4, T)
assert len(game["label"]) == 80, "label truncated"
assert game["status"] == "open" and game["pot"] == 5
assert game["timeout_streak"] == 0, "new games start with a clean streak"

# ---------- join ----------
game = g2()
d, err = games.join_game(game, "a2", T)
assert err is None and d == -5 and game["pot"] == 10
_, err = games.join_game(game, "a2", T)
assert err["code"] == 409, "double join rejected"
for aid in ("a3", "a4"):
    _, err = games.join_game(game, aid, T)
    assert err is None
_, err = games.join_game(game, "a5", T)
assert err["code"] == 409, "full game rejected"

# ---------- start ----------
solo = g2()
err = games.start_game(solo, "a1", T)
assert err["code"] == 409, "needs 2+ players"
game = g2()
games.join_game(game, "a2", T)
err = games.start_game(game, "a2", T)
assert err["code"] == 403, "only creator starts"
err = games.start_game(game, "a1", T)
assert err is None and game["status"] == "running" and game["round"] == 1

# ---------- moves: rock beats scissors, champion takes pot ----------
evs, err = games.submit_move(game, "a1", "rock", T)
assert err is None and evs == [], "round stays open with one move"
view = games.public_view(game)
assert "moves" not in view, "current moves hidden from public view"
assert "your_move" not in view, "no viewer-specific move field exists"
assert view["moves_submitted"] == ["a1"], "submitted ids visible, moves not"
evs, err = games.submit_move(game, "a2", "lizard", T)
assert err["code"] == 400, "bad move rejected"
evs, err = games.submit_move(game, "a9", "rock", T)
assert err["code"] == 403, "non-player rejected"
evs, err = games.submit_move(game, "a2", "scissors", T)
assert err is None and len(evs) == 2, "round auto-closes on last move"
rc, fin = evs
assert rc["type"] == "round_closed" and rc["moves"] == {"a1": "rock", "a2": "scissors"}
assert rc["eliminated"] == ["a2"] and rc["survivors"] == ["a1"]
assert fin["type"] == "game_finished" and fin["champion"] == "a1"
assert fin["pot"] == 10 and game["status"] == "finished"
# past rounds are public: revealed moves live in the rounds history
hist = games.public_view(game)["rounds"]
assert hist[0]["moves"] == {"a1": "rock", "a2": "scissors"}, "revealed history public"

# ---------- tie replays ----------
game = g2()
for aid in ("a2", "a3"):
    games.join_game(game, aid, T)
games.start_game(game, "a1", T)
games.submit_move(game, "a1", "rock", T)
games.submit_move(game, "a2", "rock", T)
evs, _ = games.submit_move(game, "a3", "rock", T)
assert evs[0]["eliminated"] == [] and evs[0]["survivors"] == ["a1", "a2", "a3"]
assert game["status"] == "running" and game["round"] == 2, "tie replays"

# ---------- 3-player cycle replays; partial elimination advances ----------
game = g2()
for aid in ("a2", "a3"):
    games.join_game(game, aid, T)
games.start_game(game, "a1", T)
games.submit_move(game, "a1", "rock", T)
games.submit_move(game, "a2", "paper", T)
evs, _ = games.submit_move(game, "a3", "scissors", T)
assert evs[0]["eliminated"] == [] and game["round"] == 2, "cycle replays"
games.submit_move(game, "a1", "rock", T)
games.submit_move(game, "a2", "rock", T)
evs, _ = games.submit_move(game, "a3", "scissors", T)
assert evs[0]["eliminated"] == ["a3"], "scissors eliminated by rock"
assert set(evs[0]["survivors"]) == {"a1", "a2"} and game["round"] == 3

# ---------- timeout auto-move: per-player deterministic seed ----------
game = g2()
games.join_game(game, "a2", T)
games.start_game(game, "a1", T)
game["round_opened_at"] = T - games.ROUND_TIMEOUT - 1
evs1 = games.close_round(game, T, timed_out=True)
auto1 = evs1[0]["auto_moves"]
game2 = g2()
game2["id"] = "game_1"  # same seed material
games.join_game(game2, "a2", T)
games.start_game(game2, "a1", T)
evs2 = games.close_round(game2, T, timed_out=True)
assert evs2[0]["auto_moves"] == auto1, "seeded auto-move deterministic"
assert set(evs1[0]["moves"]) == {"a1", "a2"}, "missing moves filled"
# the seed derives from game id + round + agent id (exact, independently
# recomputed — no probabilistic assertions in this suite)
game3 = g2()
games.join_game(game3, "a2", T)
games.start_game(game3, "a1", T)
for aid in ("a1", "a2"):
    expect = _pyrandom.Random(f"game_1:1:{aid}").choice(games.RPS_MOVES)
    assert games._auto_move(game3, aid) == expect, \
        f"auto-move seed mixes game, round and player ({aid})"
# absent players no longer tie uniformly: 16 derived moves, >1 distinct
derived = {_pyrandom.Random(f"game_1:1:p{i}").choice(games.RPS_MOVES)
           for i in range(16)}
assert len(derived) > 1, "per-player seeds break the uniform-tie stall"

# ---------- stall bound: MAX_TIMEOUT_ROUNDS consecutive timeouts -> terminal
game = g2()
for aid in ("a2", "a3"):
    games.join_game(game, aid, T)
games.start_game(game, "a1", T)
# a genuine round resets the streak
game["timeout_streak"] = 3
for aid in ("a1", "a2", "a3"):
    games.submit_move(game, aid, "rock", T)
assert game["timeout_streak"] == 0, "genuine round resets timeout streak"
assert game["status"] == "running" and game["round"] == 2
# force eternal ties so the ONLY way out is the stall bound
_orig_resolve = games._resolve_rps
games._resolve_rps = lambda moves: (sorted(moves), [])
try:
    for i in range(games.MAX_TIMEOUT_ROUNDS):
        assert game["status"] == "running", f"still running at timeout {i}"
        games.close_round(game, T, timed_out=True)
    assert game["status"] == "stalled", \
        "bounded: stalled after MAX_TIMEOUT_ROUNDS consecutive timeouts"
finally:
    games._resolve_rps = _orig_resolve
evs = game["rounds"][-1]
assert game["timeout_streak"] == games.MAX_TIMEOUT_ROUNDS
# terminal: no moves, no cancel-refunds, no champion
evs, err = games.submit_move(game, "a1", "rock", T)
assert err["code"] == 409, "stalled game rejects moves"
refunds, err = games.cancel_game(game, "a1", T)
assert err["code"] == 409 and refunds == [], "stalled game cannot be cancelled"
assert game["champion"] is None, "stalled game awards no champion"
# the stall is a full refund of every seated player's stake (pot not awarded)
game = g2()
for aid in ("a2", "a3"):
    games.join_game(game, aid, T)
games.start_game(game, "a1", T)
game["timeout_streak"] = games.MAX_TIMEOUT_ROUNDS - 1
evs = games.close_round(game, T, timed_out=True)
assert game["status"] == "stalled"
stall = [e for e in evs if e["type"] == "game_stalled"]
assert len(stall) == 1, "exactly one game_stalled event"
assert stall[0]["refunds"] == [("a1", 5), ("a2", 5), ("a3", 5)], \
    "stall refunds every player's full stake"

# ---------- cancel: terminal states reject, repeat cancels mint nothing ----------
game = g2()
games.join_game(game, "a2", T)
refunds, err = games.cancel_game(game, "a2", T)
assert err["code"] == 403, "only creator cancels"
refunds, err = games.cancel_game(game, "a1", T)
assert err is None and refunds == [("a1", 5), ("a2", 5)]
assert game["status"] == "cancelled"
refunds, err = games.cancel_game(game, "a1", T)
assert err["code"] == 409, "second cancel rejected (no double refund)"
assert refunds == [], "repeat cancel returns zero credit delta"
refunds, err = games.cancel_game(game, "a2", T)
assert err["code"] == 409, "terminal check precedes creator check"
game = g2()
games.join_game(game, "a2", T)
games.start_game(game, "a1", T)
games.submit_move(game, "a1", "rock", T)
games.submit_move(game, "a2", "scissors", T)
refunds, err = games.cancel_game(game, "a1", T)
assert err["code"] == 409 and refunds == [], "finished game cannot cancel"

# ---------- public view: no private moves for any viewer ----------
game = g2()
games.join_game(game, "a2", T)
games.start_game(game, "a1", T)
games.submit_move(game, "a1", "paper", T)
v = games.public_view(game)
assert "moves" not in v and "your_move" not in v, \
    "current-round moves hidden from every reader"
assert v["moves_submitted"] == ["a1"]

print("games engine: creation, join, start, RPS elimination, ties, "
      "per-player timeout seeds, stall bound + refunds, cancel idempotency, "
      "hidden moves — all passed.")

# ---------- HTTP API integration ----------
import json
import subprocess
import tempfile
import time
import urllib.request
import urllib.error

_TMP = tempfile.mkdtemp(prefix="playgrounds-games-api-")
_INT_STATE = os.path.join(_TMP, "int.json")
_GPORT = 8487
HERE = os.path.dirname(os.path.abspath(__file__))
proc = None


def _http(method, path, data=None):
    req = urllib.request.Request(
        f"http://127.0.0.1:{_GPORT}{path}", method=method,
        data=None if method == "GET" else json.dumps(data or {}).encode(),
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode() or "{}")
        except Exception:
            return e.code, {}


def _boot():
    global proc
    proc = subprocess.Popen(
        [sys.executable, os.path.join(HERE, "server.py")],
        env=dict(os.environ, PLAYGROUNDS_STATE_PATH=_INT_STATE,
                 PLAYGROUNDS_PORT=str(_GPORT)),
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    for _ in range(100):
        try:
            code, _ = _http("GET", "/api/policy")
            if code == 200:
                return
        except Exception:
            time.sleep(0.1)
    raise RuntimeError("games API server did not boot")


def _kill():
    global proc
    if proc is not None:
        proc.terminate()
        proc.wait(timeout=10)
        proc = None


def _edit_state(fn):
    with open(_INT_STATE) as f:
        st = json.load(f)
    fn(st)
    with open(_INT_STATE, "w") as f:
        json.dump(st, f)


def _balance(aid):
    code, body = _http("GET", f"/api/agents/{aid}/stats")
    assert code == 200, body
    return body["credits_balance"]


def _ledger_game_deltas():
    """(sum of all game credit deltas, {game_id: {type: count}})."""
    code, body = _http("GET", "/api/ledger")
    assert code == 200, body
    total = 0.0
    counts = {}
    for e in body["events"]:
        if e["type"] in ("game_stake", "game_won", "game_refund"):
            total = round(total + e["data"]["delta"], 2)
            counts.setdefault(e["data"]["game_id"], {}).setdefault(
                e["type"], 0)
            counts[e["data"]["game_id"]][e["type"]] += 1
    return total, counts


_boot()
try:
    ga1 = ga2 = None
    for i in (1, 2):
        code, body = _http("POST", "/api/agents/register",
                           {"name": f"Gamer{i}", "capabilities": ["gaming"],
                            "model": "test", "space": "playground"})
        assert code == 200, body
        if i == 1:
            ga1 = body["agent"]["id"]
        else:
            ga2 = body["agent"]["id"]

    # --- restart 1: fund the agents AND drop the games section, so the
    # reboot exercises the additive migration (finding #3) ---
    _kill()

    def _fund_and_wipe(st):
        st["agents"][ga1]["credits"] = 20.0
        st["agents"][ga2]["credits"] = 20.0
        del st["games"]  # pre-games v0.2 state
    _edit_state(_fund_and_wipe)
    _boot()

    code, body = _http("GET", "/api/games")
    assert code == 200 and body["games"] == [], \
        "migration created the games section; routes work after restart"
    assert _balance(ga1) == 20.0 and _balance(ga2) == 20.0

    # --- full lifecycle, nonzero stakes: escrow -> champion payout ---
    code, body = _http("POST", "/api/games",
                       {"agent_id": ga1, "kind": "rps", "label": "API RPS",
                        "stake": 25, "max_players": 4})
    assert code == 409, f"insufficient credits rejected: {body}"
    code, body = _http("POST", "/api/games",
                       {"agent_id": ga1, "kind": "rps", "label": "API RPS",
                        "stake": 5, "max_players": 4})
    assert code == 200, body
    gid = body["game"]["id"]
    assert body["game"]["status"] == "open"
    assert _balance(ga1) == 15.0, "create escrows the creator's stake"

    code, body = _http("POST", f"/api/games/{gid}/join", {"agent_id": ga2})
    assert code == 200 and len(body["game"]["players"]) == 2
    assert _balance(ga2) == 15.0, "join escrows the joiner's stake"
    code, body = _http("POST", f"/api/games/{gid}/join", {"agent_id": ga2})
    assert code == 409, "double join rejected over the API"

    code, body = _http("POST", f"/api/games/{gid}/start", {"agent_id": ga2})
    assert code == 403, "only creator starts"
    code, body = _http("POST", f"/api/games/{gid}/start", {"agent_id": ga1})
    assert code == 200 and body["game"]["status"] == "running"
    code, body = _http("POST", f"/api/games/{gid}/move",
                       {"agent_id": ga1, "move": "rock"})
    assert code == 200 and body["game"]["status"] == "running"

    # --- hidden moves over every public read surface (finding #2) ---
    code, body = _http("POST", "/api/games",
                       {"agent_id": ga1, "kind": "rps", "stake": 0})
    assert code == 200, body
    gid3 = body["game"]["id"]
    code, body = _http("POST", f"/api/games/{gid3}/join", {"agent_id": ga2})
    assert code == 200, body
    code, body = _http("POST", f"/api/games/{gid3}/start", {"agent_id": ga1})
    assert code == 200, body
    code, body = _http("POST", f"/api/games/{gid3}/move",
                       {"agent_id": ga1, "move": "rock"})
    assert code == 200 and body["game"]["status"] == "running"

    def _assert_no_private_moves(g, where):
        assert "moves" not in g, f"raw moves exposed via {where}"
        assert "your_move" not in g, f"viewer move exposed via {where}"

    code, body = _http("GET", "/api/state")
    assert code == 200, body
    for ggid, g in body["games"].items():
        _assert_no_private_moves(g, f"/api/state game {ggid}")
    code, body = _http("GET", "/api/games")
    assert code == 200, body
    for g in body["games"]:
        _assert_no_private_moves(g, "/api/games list")
    for qs in ("", f"?agent_id={ga2}", f"?agent_id={ga1}"):
        code, body = _http("GET", f"/api/games/{gid3}{qs}")
        assert code == 200, body
        _assert_no_private_moves(body["game"], f"/api/games/detail{qs}")
        assert body["game"]["moves_submitted"] == [ga1], \
            "submitted ids visible without moves"

    # --- finish game 1: champion payout, conservation check ---
    code, body = _http("POST", f"/api/games/{gid}/move",
                       {"agent_id": ga2, "move": "scissors"})
    assert code == 200 and body["game"]["status"] == "finished"
    assert body["game"]["champion"] == ga1
    evs = body["events"]
    fin = [e for e in evs if e["type"] == "game_finished"][0]
    assert fin["champion"] == ga1 and fin["pot"] == 10
    assert _balance(ga1) == 25.0 and _balance(ga2) == 15.0, \
        "champion takes the pot; total conserved"

    # --- cancel refunds, then cancel twice more: 409, zero delta ---
    code, body = _http("POST", "/api/games",
                       {"agent_id": ga1, "kind": "rps", "stake": 5})
    assert code == 200, body
    gid2 = body["game"]["id"]
    code, body = _http("POST", f"/api/games/{gid2}/join", {"agent_id": ga2})
    assert code == 200, body
    assert _balance(ga1) == 20.0 and _balance(ga2) == 10.0
    code, body = _http("POST", f"/api/games/{gid2}/cancel", {"agent_id": ga1})
    assert code == 200 and body["game"]["status"] == "cancelled"
    assert _balance(ga1) == 25.0 and _balance(ga2) == 15.0, "cancel refunds stakes"
    code, body = _http("POST", f"/api/games/{gid2}/cancel", {"agent_id": ga1})
    assert code == 409, f"repeat cancel rejected: {body}"
    assert _balance(ga1) == 25.0 and _balance(ga2) == 15.0, \
        "repeat cancel mints no credits (finding #1)"
    total, counts = _ledger_game_deltas()
    assert counts[gid2].get("game_refund", 0) == 2, \
        f"exactly one refund per player, no duplicates: {counts[gid2]}"

    # --- restart 2: cancel-after-restart is still a 409 with zero delta ---
    _kill()
    _boot()
    code, body = _http("POST", f"/api/games/{gid2}/cancel", {"agent_id": ga1})
    assert code == 409, f"cancel after restart rejected: {body}"
    assert _balance(ga1) == 25.0 and _balance(ga2) == 15.0, \
        "cancel after restart mints no credits"
    total2, counts2 = _ledger_game_deltas()
    assert counts2[gid2].get("game_refund", 0) == 2, \
        "no duplicate refund ledger entries across restart"

    # --- restart 3: lazy timeout progression across a restart (finding #4) ---
    _kill()

    def _age_round(st):
        st["games"][gid3]["round_opened_at"] = T - games.ROUND_TIMEOUT - 50
    _edit_state(_age_round)
    _boot()
    code, body = _http("GET", "/api/games")
    assert code == 200, body
    g3 = [g for g in body["games"] if g["id"] == gid3][0]
    assert g3["timeout_streak"] == 1, "sweep ran lazily on API access"
    assert len(g3["rounds"]) == 1 and g3["rounds"][0]["timed_out"] is True, \
        "stale round closed by the sweep, not by a scheduler"
    assert set(g3["rounds"][0]["auto_moves"]) == {ga2}, \
        "absent player's move auto-filled"

    # --- classroom agent is refused at the playground gate ---
    code, body = _http("POST", "/api/agents/register",
                       {"name": "Studious", "capabilities": ["study"],
                        "model": "test"})
    assert code == 200, body
    ga3 = body["agent"]["id"]
    code, body = _http("POST", "/api/games",
                       {"agent_id": ga3, "kind": "rps", "stake": 0})
    assert code == 403, "classroom agents cannot create games"

    # --- end-to-end conservation: every credit moved through games nets out ---
    assert _balance(ga1) + _balance(ga2) == 40.0, \
        "agent balances conserved across the full lifecycle"
    total, _ = _ledger_game_deltas()
    assert total == 0.0, f"game ledger deltas net to zero, got {total}"
    code, body = _http("GET", "/api/ledger")
    types = {e["type"] for e in body["events"]}
    assert {"game_started", "game_finished", "game_won"} <= types, types
finally:
    _kill()

print("games HTTP API: migration on restart, hidden moves on every read "
      "surface, nonzero credit conservation (escrow/payout/refund), cancel "
      "idempotency incl. restart, lazy timeout sweep, presence gate, "
      "insufficient-credits — all passed.")
