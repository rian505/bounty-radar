"""Offline tests for the source adapters — no network required.

Fixtures mirror the real API shapes captured 2026-06-07.
"""

import datetime as dt

from bounty_radar.sources import (
    from_immunefi, from_code4rena, from_cantina, from_sherlock,
    _parse_usd, _window_status, _epoch_to_iso,
)


# --- fixtures (trimmed real responses) ------------------------------------

IMMUNEFI = [
    {"project": "Sky", "maxBounty": 10000000, "language": ["Solidity"],
     "ecosystem": ["ETH"], "kyc": False, "slug": "sky"},
    {"project": "Chainlink", "maxBounty": 3000000,
     "language": ["Go", "Rust", "Solidity"], "ecosystem": ["multi"],
     "kyc": True, "slug": "chainlink"},
]

CODE4RENA = {"data": {"audits": [
    {"title": "Monetrix", "status": "Active",
     "formattedAmount": "$135,000 in USDC",
     "startTime": "2026-06-01T20:00:00.000Z",
     "endTime": "2026-06-30T20:00:00.000Z", "slug": "2026-06-monetrix"},
    {"title": "OldThing", "status": "Completed",
     "formattedAmount": "$22,000 in USDC",
     "startTime": "2026-04-24T20:00:00.000Z",
     "endTime": "2026-05-04T20:00:00.000Z", "slug": "old"},
]}}

CANTINA = [
    {"name": "Morpho Midnight", "status": "live",
     "totalRewardPot": 400000, "currencyCode": "USDC",
     "timeframe": {"start": "2026-05-29T12:00:00Z",
                   "end": "2026-06-12T20:00:00Z"},
     "url": "https://cantina.xyz/competitions/abc"},
]

SHERLOCK = {"items": [
    {"title": "DRE App - dreUSD", "status": "CREATED", "prize_pool": 48000,
     "rewards": 60000, "starts_at": 1780930800, "ends_at": 1781708400,
     "type_label": "Public Bug Bounty"},
    {"title": "Done One", "status": "FINISHED", "prize_pool": 50000,
     "rewards": 50000, "starts_at": 1770000000, "ends_at": 1771000000,
     "type_label": "Contest"},
]}


# --- helper tests ---------------------------------------------------------

def test_parse_usd_from_string():
    assert _parse_usd("$135,000 in USDC") == 135000
    assert _parse_usd(400000) == 400000
    assert _parse_usd(None) is None
    assert _parse_usd("no digits") is None


def test_epoch_to_iso_roundtrip():
    iso = _epoch_to_iso(1780930800)
    assert iso is not None and iso.startswith("2026-")
    assert _epoch_to_iso("bad") is None


def test_window_status():
    past = "2000-01-01T00:00:00+00:00"
    future = "2999-01-01T00:00:00+00:00"
    assert _window_status(past, future) == "live"
    assert _window_status(future, future) == "upcoming"
    assert _window_status(past, past) == "ended"


# --- adapter tests --------------------------------------------------------

def test_immunefi_adapter():
    out = from_immunefi(IMMUNEFI)
    assert len(out) == 2
    sky = out[0]
    assert sky.source == "immunefi"
    assert sky.max_reward_usd == 10000000
    assert sky.kyc is False
    assert sky.kind == "bounty"
    assert "Solidity" in sky.languages
    assert sky.url == "https://immunefi.com/bug-bounty/sky/"


def test_code4rena_adapter_status_mapping():
    out = from_code4rena(CODE4RENA)
    by_name = {b.name: b for b in out}
    assert by_name["Monetrix"].status == "live"
    assert by_name["Monetrix"].max_reward_usd == 135000
    assert by_name["OldThing"].status == "ended"
    assert by_name["Monetrix"].kind == "contest"


def test_cantina_adapter():
    out = from_cantina(CANTINA)
    assert len(out) == 1
    c = out[0]
    assert c.status == "live"
    assert c.max_reward_usd == 400000
    assert c.url.endswith("/abc")


def test_sherlock_adapter_status_mapping():
    out = from_sherlock(SHERLOCK)
    by_name = {b.name: b for b in out}
    assert by_name["DRE App - dreUSD"].status == "upcoming"
    assert by_name["DRE App - dreUSD"].max_reward_usd == 60000  # rewards > pool
    assert by_name["Done One"].status == "ended"


def test_adapters_handle_empty():
    assert from_immunefi([]) == []
    assert from_code4rena({}) == []
    assert from_cantina([]) == []
    assert from_sherlock({"items": []}) == []
