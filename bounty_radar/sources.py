"""Source adapters: fetch + normalise each platform's public feed.

Every adapter returns a list of ``Bounty`` dataclasses with a common schema,
so the CLI never has to care about per-platform quirks.

All four endpoints are public and require no authentication (verified
2026-06-07). If a feed changes shape, the adapter degrades gracefully:
missing fields become ``None`` rather than raising.
"""

from __future__ import annotations

import datetime as _dt
import json
import re
import urllib.request
import urllib.error
from dataclasses import dataclass, asdict
from typing import Any, Iterable, Optional

USER_AGENT = "bounty-radar/0.1 (+https://github.com/rian505/bounty-radar)"
DEFAULT_TIMEOUT = 30

ENDPOINTS = {
    "immunefi": "https://immunefi.com/public-api/bounties.json",
    "code4rena": "https://code4rena.com/api/v1/audits?perPage=100",
    "cantina": "https://cantina.xyz/api/v0/competitions",
    "sherlock": "https://audits.sherlock.xyz/api/contests",
}


@dataclass
class Bounty:
    """Normalised cross-platform bounty/contest record."""

    source: str
    name: str
    kind: str               # "bounty" (ongoing) or "contest" (time-boxed)
    status: str             # normalised: live | upcoming | ended | unknown
    max_reward_usd: Optional[int]
    languages: list[str]
    ecosystems: list[str]
    kyc: Optional[bool]
    starts_at: Optional[str]   # ISO-8601 or None
    ends_at: Optional[str]
    url: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def _fetch_json(url: str, timeout: int = DEFAULT_TIMEOUT) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
        return json.loads(resp.read().decode("utf-8"))


def _epoch_to_iso(value: Any) -> Optional[str]:
    if not isinstance(value, (int, float)):
        return None
    try:
        return _dt.datetime.fromtimestamp(
            value, tz=_dt.timezone.utc
        ).isoformat()
    except (OverflowError, OSError, ValueError):
        return None


def _parse_usd(text: Any) -> Optional[int]:
    """Extract an integer USD amount from a string like '$135,000 in USDC'."""
    if isinstance(text, (int, float)):
        return int(text)
    if not isinstance(text, str):
        return None
    digits = "".join(ch for ch in text if ch.isdigit())
    return int(digits) if digits else None


def _as_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(v) for v in value]
    if value is None:
        return []
    return [str(value)]


# Best-effort language detection from free-text scope/description.
# These feeds expose no structured language field, so we scan the text for
# well-known smart-contract languages using WORD-BOUNDARY matching (so "rust"
# doesn't match "trust" and "move" doesn't match "remove"). This is a
# heuristic hint, not ground truth — always confirm on the program page.
_LANG_PATTERNS = {
    "Solidity": (r"solidity", r"\bevm\b", r"erc-?20", r"erc-?4626",
                 r"erc-?721", r"ethereum virtual machine"),
    "Rust": (r"\brust\b", r"\banchor\b", r"solana program", r"cosmwasm"),
    "Move": (r"\bmove\b", r"\baptos\b", r"\bsui\b"),
    "Vyper": (r"\bvyper\b",),
    "Cairo": (r"\bcairo\b", r"starknet"),
    "Go": (r"\bgolang\b", r"cosmos sdk"),
}


def _infer_languages(*texts: Any) -> list[str]:
    blob = " ".join(t for t in texts if isinstance(t, str)).lower()
    if not blob:
        return []
    found = [lang for lang, pats in _LANG_PATTERNS.items()
             if any(re.search(p, blob) for p in pats)]
    return found


def _now() -> _dt.datetime:
    return _dt.datetime.now(tz=_dt.timezone.utc)


def _window_status(starts: Optional[str], ends: Optional[str]) -> str:
    """Derive live/upcoming/ended from an ISO start/end window."""
    now = _now()

    def _p(s: Optional[str]) -> Optional[_dt.datetime]:
        if not s:
            return None
        try:
            return _dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
        except ValueError:
            return None

    s, e = _p(starts), _p(ends)
    if s and now < s:
        return "upcoming"
    if e and now > e:
        return "ended"
    if s and e and s <= now <= e:
        return "live"
    return "unknown"


# --------------------------------------------------------------------------
# adapters
# --------------------------------------------------------------------------

def from_immunefi(raw: Iterable[dict]) -> list[Bounty]:
    out: list[Bounty] = []
    for item in raw:
        slug = item.get("slug", "")
        out.append(Bounty(
            source="immunefi",
            name=str(item.get("project", "?")),
            kind="bounty",
            status="live",  # Immunefi programs are ongoing unless invite-only
            max_reward_usd=_parse_usd(item.get("maxBounty")),
            languages=_as_list(item.get("language")),
            ecosystems=_as_list(item.get("ecosystem")),
            kyc=item.get("kyc") if isinstance(item.get("kyc"), bool) else None,
            starts_at=None,
            ends_at=None,
            url=f"https://immunefi.com/bug-bounty/{slug}/" if slug else "https://immunefi.com/explore/",
        ))
    return out


def from_code4rena(raw: dict) -> list[Bounty]:
    audits = (raw or {}).get("data", {}).get("audits", [])
    out: list[Bounty] = []
    status_map = {"Active": "live", "Upcoming": "upcoming"}
    for a in audits:
        slug = a.get("slug", "")
        raw_status = str(a.get("status", ""))
        league = a.get("league")
        out.append(Bounty(
            source="code4rena",
            name=str(a.get("title", "?")),
            kind="contest",
            status=status_map.get(raw_status, "ended"),
            max_reward_usd=_parse_usd(a.get("formattedAmount")),
            languages=_infer_languages(a.get("title"), a.get("details")),
            ecosystems=[str(league)] if league else [],
            kyc=None,
            starts_at=a.get("startTime"),
            ends_at=a.get("endTime"),
            url=f"https://code4rena.com/audits/{slug}" if slug else "https://code4rena.com/audits",
        ))
    return out


def from_cantina(raw: Any) -> list[Bounty]:
    items = raw if isinstance(raw, list) else (raw or {}).get("competitions", [])
    out: list[Bounty] = []
    for c in items:
        tf = c.get("timeframe", {}) or {}
        raw_status = str(c.get("status", "")).lower()
        status = {"live": "live", "upcoming": "upcoming"}.get(raw_status, "ended")
        kyc = c.get("kycRequired")
        out.append(Bounty(
            source="cantina",
            name=str(c.get("name", "?")),
            kind="contest",
            status=status,
            max_reward_usd=_parse_usd(c.get("totalRewardPot")),
            languages=_infer_languages(c.get("name"), c.get("instructions")),
            ecosystems=[],
            kyc=kyc if isinstance(kyc, bool) else None,
            starts_at=tf.get("start"),
            ends_at=tf.get("end"),
            url=c.get("url") or "https://cantina.xyz/competitions",
        ))
    return out


def from_sherlock(raw: Any) -> list[Bounty]:
    items = (raw or {}).get("items", raw) if isinstance(raw, dict) else raw
    out: list[Bounty] = []
    for s in (items or []):
        starts = _epoch_to_iso(s.get("starts_at"))
        ends = _epoch_to_iso(s.get("ends_at"))
        # Sherlock statuses: CREATED (upcoming), RUNNING (live),
        # ESCALATING/FINISHED (ended). Fall back to the time window.
        raw_status = str(s.get("status", "")).upper()
        status = {
            "RUNNING": "live",
            "CREATED": "upcoming",
            "ESCALATING": "ended",
            "FINISHED": "ended",
        }.get(raw_status) or _window_status(starts, ends)
        out.append(Bounty(
            source="sherlock",
            name=str(s.get("title", "?")),
            kind="contest",
            status=status,
            max_reward_usd=_parse_usd(s.get("rewards") or s.get("prize_pool")),
            languages=_infer_languages(s.get("title"), s.get("short_description")),
            ecosystems=[],
            kyc=None,
            starts_at=starts,
            ends_at=ends,
            url="https://audits.sherlock.xyz/contests",
        ))
    return out


_ADAPTERS = {
    "immunefi": from_immunefi,
    "code4rena": from_code4rena,
    "cantina": from_cantina,
    "sherlock": from_sherlock,
}


def fetch_source(name: str, timeout: int = DEFAULT_TIMEOUT) -> list[Bounty]:
    """Fetch and normalise a single source. Raises on network/parse failure."""
    if name not in ENDPOINTS:
        raise ValueError(f"unknown source: {name!r}")
    raw = _fetch_json(ENDPOINTS[name], timeout=timeout)
    return _ADAPTERS[name](raw)


def fetch_all(
    sources: Optional[Iterable[str]] = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> tuple[list[Bounty], dict[str, str]]:
    """Fetch every requested source.

    Returns ``(bounties, errors)`` where ``errors`` maps a failed source name
    to its error string. A single dead endpoint never kills the whole run.
    """
    names = list(sources) if sources else list(ENDPOINTS)
    results: list[Bounty] = []
    errors: dict[str, str] = {}
    for name in names:
        try:
            results.extend(fetch_source(name, timeout=timeout))
        except (urllib.error.URLError, urllib.error.HTTPError, ValueError,
                json.JSONDecodeError, TimeoutError) as exc:
            errors[name] = str(exc)
    return results, errors
