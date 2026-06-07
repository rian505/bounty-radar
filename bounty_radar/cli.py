"""Command-line interface for bounty-radar."""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
from typing import Optional

from . import __version__
from .sources import Bounty, ENDPOINTS, fetch_all
from .state import DEFAULT_STATE, split_new, save_seen


def _fmt_usd(amount: Optional[int]) -> str:
    if amount is None:
        return "?"
    if amount >= 1_000_000:
        return f"${amount / 1_000_000:.1f}M".replace(".0M", "M")
    if amount >= 1_000:
        return f"${amount // 1000}k"
    return f"${amount}"


def _fmt_date(iso: Optional[str]) -> str:
    return iso[:10] if iso else "-"


def _matches(b: Bounty, args: argparse.Namespace) -> bool:
    if args.status and b.status not in args.status:
        return False
    if args.min and (b.max_reward_usd or 0) < args.min:
        return False
    if args.no_kyc and b.kyc is True:
        return False
    if args.lang:
        hay = " ".join(b.languages).lower()
        if args.lang.lower() not in hay:
            return False
    if args.kind and b.kind != args.kind:
        return False
    if args.ending_soon is not None:
        if not b.ends_at:
            return False
        try:
            end = _dt.datetime.fromisoformat(b.ends_at.replace("Z", "+00:00"))
        except ValueError:
            return False
        days_left = (end - _dt.datetime.now(tz=_dt.timezone.utc)).total_seconds() / 86400
        if days_left < 0 or days_left > args.ending_soon:
            return False
    return True


def _render_table(rows: list[Bounty]) -> str:
    if not rows:
        return "(no matching bounties)"
    headers = ["SOURCE", "NAME", "KIND", "STATUS", "MAX", "KYC", "ENDS", "LANG"]
    table = []
    for b in rows:
        table.append([
            b.source,
            b.name[:34],
            b.kind,
            b.status,
            _fmt_usd(b.max_reward_usd),
            {True: "yes", False: "no", None: "-"}[b.kyc],
            _fmt_date(b.ends_at),
            (",".join(b.languages)[:18] or "-"),
        ])
    widths = [
        max(len(headers[i]), max((len(r[i]) for r in table), default=0))
        for i in range(len(headers))
    ]
    line = "  ".join(h.ljust(widths[i]) for i, h in enumerate(headers))
    out = [line, "  ".join("-" * widths[i] for i in range(len(headers)))]
    for r in table:
        out.append("  ".join(r[i].ljust(widths[i]) for i in range(len(headers))))
    return "\n".join(out)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="bounty-radar",
        description="Aggregate live crypto bug-bounty & audit-contest targets "
                    "from Immunefi, Code4rena, Cantina, and Sherlock.",
    )
    p.add_argument("--version", action="version",
                   version=f"bounty-radar {__version__}")
    p.add_argument("--source", action="append", choices=sorted(ENDPOINTS),
                   help="limit to specific source(s); repeatable. Default: all")
    p.add_argument("--status", action="append",
                   choices=["live", "upcoming", "ended", "unknown"],
                   help="filter by status; repeatable. Default: live + upcoming")
    p.add_argument("--min", type=int, default=0, metavar="USD",
                   help="minimum max-reward in USD")
    p.add_argument("--lang", metavar="LANG",
                   help="substring match on language (e.g. solidity, rust)")
    p.add_argument("--kind", choices=["bounty", "contest"],
                   help="only ongoing bounties or time-boxed contests")
    p.add_argument("--ending-soon", type=float, metavar="DAYS",
                   help="only targets ending within DAYS days (contests)")
    p.add_argument("--no-kyc", action="store_true",
                   help="exclude programs that require KYC")
    p.add_argument("--sort", choices=["reward", "ends", "name"],
                   default="reward", help="sort key (default: reward desc)")
    p.add_argument("--limit", type=int, default=30,
                   help="max rows to show (default 30, 0 = all)")
    p.add_argument("--json", action="store_true",
                   help="emit JSON instead of a table")
    p.add_argument("--timeout", type=int, default=30,
                   help="per-request timeout in seconds")
    p.add_argument("--new-only", action="store_true",
                   help="show only targets not seen on a previous run "
                        "(compares against the state file)")
    p.add_argument("--save-state", action="store_true",
                   help="persist the current target set as 'seen' "
                        "(use with --new-only in a cron job)")
    p.add_argument("--state-file", metavar="PATH", default=str(DEFAULT_STATE),
                   help=f"state file for --new-only (default: {DEFAULT_STATE})")
    return p


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.status:
        args.status = ["live", "upcoming"]

    bounties, errors = fetch_all(args.source, timeout=args.timeout)
    for src, err in errors.items():
        print(f"warning: {src} failed: {err}", file=sys.stderr)

    rows = [b for b in bounties if _matches(b, args)]

    # Change-detection: keep only targets not seen on a previous run.
    from pathlib import Path as _Path
    state_path = _Path(args.state_file)
    if args.new_only:
        rows, all_ids = split_new(rows, state_path)
    if args.save_state:
        # Persist the *currently matching* set so the next run diffs against it.
        from .state import identity, load_seen
        ids = {identity(b) for b in [b for b in bounties if _matches(b, args)]}
        save_seen(ids | load_seen(state_path), state_path)

    if args.sort == "reward":
        rows.sort(key=lambda b: b.max_reward_usd or -1, reverse=True)
    elif args.sort == "ends":
        rows.sort(key=lambda b: b.ends_at or "9999")
    else:
        rows.sort(key=lambda b: b.name.lower())

    if args.limit and args.limit > 0:
        rows = rows[: args.limit]

    if args.json:
        print(json.dumps([b.to_dict() for b in rows], indent=2))
    else:
        print(_render_table(rows))
        print(f"\n{len(rows)} target(s) shown.", file=sys.stderr)

    # Exit non-zero only if every source failed (nothing usable).
    if errors and not bounties:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
