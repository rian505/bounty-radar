# bounty-radar

[![CI](https://github.com/rian505/bounty-radar/actions/workflows/ci.yml/badge.svg)](https://github.com/rian505/bounty-radar/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/bounty-radar.svg)](https://pypi.org/project/bounty-radar/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

One command to see every live crypto bug-bounty and audit contest worth your time — pulled straight from the platforms that actually pay.

`bounty-radar` aggregates the public feeds of **Immunefi**, **Code4rena**, **Cantina**, and **Sherlock**, normalises them into a single schema, and lets you filter by status, payout, language, and KYC requirement. Zero runtime dependencies (Python stdlib only), no API keys, no scraping.

## Why

Bug-bounty and audit opportunities are scattered across four sites with four different UIs, four different status models, and four different ways of expressing a payout. Worse, plenty of "bounty" repos on GitHub are honeypots that have never paid anyone. `bounty-radar` skips all of that and shows you only the platforms with real, verifiable payouts — ranked by reward, in one table.

## Install

```bash
git clone https://github.com/rian505/bounty-radar.git
cd bounty-radar
pip install .
```

That's it. (Requires Python 3.9+.)

## Usage

```bash
# Everything live or upcoming, ranked by reward
bounty-radar

# Big no-KYC bounties only (easiest to actually collect on)
bounty-radar --kind bounty --no-kyc --min 2000000

# Open audit contests, soonest deadline first
bounty-radar --kind contest --status live --sort ends

# Only Solidity targets
bounty-radar --lang solidity

# Machine-readable output for piping into other tools
bounty-radar --json | jq '.[] | select(.max_reward_usd > 5000000)'
```

### Options

| Flag | Description |
|------|-------------|
| `--source NAME` | Limit to specific source(s): `immunefi`, `code4rena`, `cantina`, `sherlock`. Repeatable. |
| `--status S` | `live`, `upcoming`, `ended`, `unknown`. Repeatable. Default: live + upcoming. |
| `--min USD` | Minimum max-reward in USD. |
| `--lang LANG` | Substring match on language (e.g. `solidity`, `rust`). |
| `--kind K` | `bounty` (ongoing) or `contest` (time-boxed). |
| `--no-kyc` | Exclude programs that require KYC. |
| `--sort KEY` | `reward` (default), `ends`, or `name`. |
| `--limit N` | Max rows (default 30, `0` = all). |
| `--json` | Emit JSON instead of a table. |

### Watch mode (change detection)

Track which targets you've already seen and surface only new ones — ideal for a cron alert:

```bash
# First run: record the current set as "seen"
bounty-radar --new-only --save-state

# Later runs: only print targets that appeared since
bounty-radar --new-only --save-state
```

State lives at `~/.bounty-radar-seen.json` (override with `--state-file` or the `BOUNTY_RADAR_STATE` env var). Combine with `--json` to feed a notifier.

## Sample output

```
SOURCE    NAME       KIND    STATUS  MAX    KYC  ENDS  LANG
--------  ---------  ------  ------  -----  ---  ----  --------------
immunefi  Sky        bounty  live    $10M   no   -     Solidity
immunefi  Spark      bounty  live    $5M    no   -     Solidity
immunefi  GMX        bounty  live    $5M    no   -     JavaScript,Sol
immunefi  Olympus    bounty  live    $3.3M  no   -     Solidity
immunefi  Lido       bounty  live    $2M    no   -     Solidity,Vyper
```

## Data sources

All four feeds are public and require no authentication:

| Platform | Endpoint |
|----------|----------|
| Immunefi | `https://immunefi.com/public-api/bounties.json` |
| Code4rena | `https://code4rena.com/api/v1/audits` |
| Cantina | `https://cantina.xyz/api/v0/competitions` |
| Sherlock | `https://audits.sherlock.xyz/api/contests` |

If a feed is down or changes shape, that source is skipped with a warning — the rest still work.

## Development

```bash
pip install -e ".[dev]"
pytest          # 15 offline tests, no network needed
```

Tests run against captured fixtures, so they're fast and deterministic.

## Disclaimer

Reward figures and statuses are reported as-is from each platform's feed. Always confirm scope, rules, and payout terms on the official program page (linked in each row's `url`) before doing any work. This tool finds targets; it does not vouch for them.

## License

MIT — see [LICENSE](LICENSE).
