"""Snapshot state for change-detection (watch mode).

Stores the set of bounty identities seen on the last run so a later run can
report only what's *new*. Used by ``bounty-radar --new-only`` and the cron
alerter. State is a small JSON file under the user's home by default.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Iterable

from .sources import Bounty

DEFAULT_STATE = Path(
    os.environ.get("BOUNTY_RADAR_STATE",
                   str(Path.home() / ".bounty-radar-seen.json"))
)


def identity(b: Bounty) -> str:
    """Stable key for a bounty across runs."""
    return f"{b.source}:{b.name}:{b.kind}"


def load_seen(path: Path = DEFAULT_STATE) -> set[str]:
    try:
        data = json.loads(path.read_text())
        if isinstance(data, dict):
            return set(data.get("seen", []))
        if isinstance(data, list):
            return set(data)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        pass
    return set()


def save_seen(ids: Iterable[str], path: Path = DEFAULT_STATE) -> None:
    path.write_text(json.dumps({"seen": sorted(set(ids))}, indent=0))


def split_new(
    bounties: list[Bounty], path: Path = DEFAULT_STATE
) -> tuple[list[Bounty], set[str]]:
    """Return ``(new_bounties, all_ids)`` given the previously-seen state.

    Caller decides whether/when to persist ``all_ids`` via ``save_seen``.
    """
    seen = load_seen(path)
    new = [b for b in bounties if identity(b) not in seen]
    all_ids = {identity(b) for b in bounties} | seen
    return new, all_ids
