#!/usr/bin/env python3
"""state.json snapshot rotation and restore (issue #33).

Standalone on purpose: backup tooling must keep working even if the
server module itself is broken, so nothing here imports server.py.

Snapshots live next to the state file and are named
    <state>.bak-YYYYmmddTHHMMSSffffffZ     (UTC, fixed width, sortable)
Rotation keeps the newest N snapshots (PLAYGROUNDS_BACKUP_KEEP env or
--keep, default 10); older ones are deleted. The server takes one
snapshot at every startup; take more any time with the CLI, e.g. from
a systemd timer (see docs/REMOTE-DEPLOYMENT.md).

Usage:
    python3 state_backup.py snapshot [--state PATH] [--keep N]
    python3 state_backup.py list     [--state PATH]
    python3 state_backup.py restore SNAPSHOT [--state PATH]

Restore first copies the current state file to <state>.pre-restore
(a single safety copy, overwritten on each restore), then atomically
swaps the snapshot in. Stop the server before restoring; verify
afterwards with GET /api/health (ledger_ok and room_ledgers_ok must
be true).

Snapshots, safety copies and the restored state file are always
created owner-only (0600): state.json carries credential hashes and
the utility must never widen its access, whatever the caller's umask.
Retention must be a positive count; keep < 1 is rejected outright
rather than silently pruning every snapshot.
"""
import argparse
import os
import shutil
import sys
from datetime import datetime, timezone

DEFAULT_KEEP = 10
HERE = os.path.dirname(os.path.abspath(__file__))


def default_state_path():
    return os.environ.get("PLAYGROUNDS_STATE_PATH",
                          os.path.join(HERE, "state.json"))


def default_keep():
    try:
        return max(1, int(os.environ.get("PLAYGROUNDS_BACKUP_KEEP",
                                         DEFAULT_KEEP)))
    except ValueError:
        return DEFAULT_KEEP


def _stamp(when=None):
    when = when or datetime.now(timezone.utc)
    return when.strftime("%Y%m%dT%H%M%S") + f"{when.microsecond:06d}Z"


def snapshot_path(state_path, when=None):
    return f"{state_path}.bak-{_stamp(when)}"


def list_snapshots(state_path):
    """All snapshots for STATE_PATH, oldest first."""
    prefix = os.path.basename(state_path) + ".bak-"
    d = os.path.dirname(os.path.abspath(state_path))
    if not os.path.isdir(d):
        return []
    return [os.path.join(d, n) for n in sorted(os.listdir(d))
            if n.startswith(prefix)]


def _validate_keep(keep):
    """Retention must be a positive count. Reject bad CLI/API input
    explicitly: silently treating keep=0 as 'prune everything' would
    delete every snapshot, including the one just taken."""
    if keep is not None and keep < 1:
        raise ValueError(f"keep must be a positive integer, got {keep!r}")


def _copy_private(src, dest):
    """Copy SRC to DEST with DEST owner-only (0600) from creation.
    os.open's mode applies at creation; fchmod tightens DEST even when
    it already existed with looser permissions, so the caller's umask
    can never widen access to a copy of the state file."""
    with open(src, "rb") as fsrc:
        fd = os.open(dest, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        try:
            os.fchmod(fd, 0o600)
            with os.fdopen(fd, "wb") as fdst:
                fd = None  # fdst owns the descriptor now
                shutil.copyfileobj(fsrc, fdst)
        finally:
            if fd is not None:
                os.close(fd)


def prune_snapshots(state_path, keep=None):
    """Delete all but the newest KEEP snapshots. Returns removed paths."""
    _validate_keep(keep)
    keep = default_keep() if keep is None else keep
    snaps = list_snapshots(state_path)
    removed = []
    for p in snaps[:max(0, len(snaps) - keep)]:
        os.remove(p)
        removed.append(p)
    return removed


def make_snapshot(state_path, keep=None, when=None):
    """Copy the state file to a timestamped snapshot, then rotate.
    Returns the snapshot path, or None when there is no state file yet.
    Raises ValueError on a nonpositive keep — before anything is
    copied or pruned."""
    _validate_keep(keep)
    if not os.path.exists(state_path):
        return None
    dest = snapshot_path(state_path, when)
    _copy_private(state_path, dest)
    prune_snapshots(state_path, keep)
    return dest


def restore_snapshot(snap, state_path):
    """Swap SNAPSHOT in as the live state file. The current state file
    (if any) is preserved at <state>.pre-restore first. All copies are
    owner-only (0600) from creation."""
    if not os.path.exists(snap):
        raise FileNotFoundError(snap)
    if os.path.exists(state_path):
        _copy_private(state_path, state_path + ".pre-restore")
    tmp = state_path + ".restore-tmp"
    _copy_private(snap, tmp)
    os.replace(tmp, state_path)
    return state_path


def main(argv=None):
    ap = argparse.ArgumentParser(description="PlayGrounds state backups")
    ap.add_argument("command", choices=["snapshot", "list", "restore"])
    ap.add_argument("snapshot", nargs="?", help="snapshot path (restore only)")
    ap.add_argument("--state", default=None)
    ap.add_argument("--keep", type=int, default=None)
    args = ap.parse_args(argv)
    state_path = args.state or default_state_path()
    if args.command == "snapshot":
        try:
            dest = make_snapshot(state_path, args.keep)
        except ValueError as e:
            print(f"error: {e}", file=sys.stderr)
            return 2
        print(dest or "no state file yet; nothing to snapshot")
        return 0 if dest else 1
    if args.command == "list":
        for p in list_snapshots(state_path):
            print(p)
        return 0
    if not args.snapshot:
        ap.error("restore requires a snapshot path")
    restore_snapshot(args.snapshot, state_path)
    print(f"restored {args.snapshot} -> {state_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
