"""Tests for watch / change-detection state."""

from pathlib import Path

from bounty_radar.sources import Bounty
from bounty_radar.state import identity, save_seen, load_seen, split_new


def _b(name, source="immunefi"):
    return Bounty(source, name, "bounty", "live", 1000, [], [], None,
                  None, None, f"https://x/{name}")


def test_identity_stable():
    b = _b("Sky")
    assert identity(b) == "immunefi:Sky:bounty"


def test_save_and_load_roundtrip(tmp_path):
    p = tmp_path / "seen.json"
    save_seen(["a", "b", "a"], p)
    assert load_seen(p) == {"a", "b"}


def test_load_missing_file_is_empty(tmp_path):
    assert load_seen(tmp_path / "nope.json") == set()


def test_split_new_detects_only_unseen(tmp_path):
    p = tmp_path / "seen.json"
    save_seen([identity(_b("Sky"))], p)
    bounties = [_b("Sky"), _b("Spark"), _b("GMX")]
    new, all_ids = split_new(bounties, p)
    names = {b.name for b in new}
    assert names == {"Spark", "GMX"}        # Sky already seen
    assert identity(_b("Sky")) in all_ids   # union keeps the old one


def test_split_new_first_run_all_new(tmp_path):
    p = tmp_path / "seen.json"
    bounties = [_b("Sky"), _b("Spark")]
    new, _ = split_new(bounties, p)
    assert len(new) == 2                     # nothing seen yet → all new
