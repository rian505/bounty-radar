"""CLI-level tests using monkeypatched fetch (no network)."""

from bounty_radar import cli
from bounty_radar.sources import Bounty


SAMPLE = [
    Bounty("immunefi", "Sky", "bounty", "live", 10000000, ["Solidity"],
           ["ETH"], False, None, None, "https://immunefi.com/bug-bounty/sky/"),
    Bounty("immunefi", "Chainlink", "bounty", "live", 3000000,
           ["Go", "Rust"], ["multi"], True, None, None,
           "https://immunefi.com/bug-bounty/chainlink/"),
    Bounty("cantina", "Morpho", "contest", "live", 400000, [], [], None,
           "2026-05-29T12:00:00Z", "2026-06-12T20:00:00Z",
           "https://cantina.xyz/competitions/abc"),
    Bounty("code4rena", "OldThing", "contest", "ended", 22000, [], [], None,
           None, "2026-05-04T20:00:00Z", "https://code4rena.com/audits/old"),
]


def _patch(monkeypatch):
    monkeypatch.setattr(cli, "fetch_all", lambda *a, **k: (SAMPLE, {}))


def test_default_excludes_ended(monkeypatch, capsys):
    _patch(monkeypatch)
    rc = cli.main([])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Sky" in out
    assert "OldThing" not in out  # ended filtered by default


def test_min_reward_filter(monkeypatch, capsys):
    _patch(monkeypatch)
    cli.main(["--min", "5000000"])
    out = capsys.readouterr().out
    assert "Sky" in out
    assert "Chainlink" not in out  # 3M < 5M
    assert "Morpho" not in out


def test_no_kyc_filter(monkeypatch, capsys):
    _patch(monkeypatch)
    cli.main(["--no-kyc"])
    out = capsys.readouterr().out
    assert "Sky" in out
    assert "Chainlink" not in out  # KYC required


def test_lang_filter(monkeypatch, capsys):
    _patch(monkeypatch)
    cli.main(["--lang", "rust"])
    out = capsys.readouterr().out
    assert "Chainlink" in out
    assert "Sky" not in out


def test_kind_filter(monkeypatch, capsys):
    _patch(monkeypatch)
    cli.main(["--kind", "contest"])
    out = capsys.readouterr().out
    assert "Morpho" in out
    assert "Sky" not in out


def test_json_output(monkeypatch, capsys):
    _patch(monkeypatch)
    cli.main(["--json"])
    out = capsys.readouterr().out
    assert '"source": "immunefi"' in out
    assert out.lstrip().startswith("[")


def test_all_sources_dead_returns_1(monkeypatch, capsys):
    monkeypatch.setattr(cli, "fetch_all",
                        lambda *a, **k: ([], {"immunefi": "boom"}))
    rc = cli.main([])
    assert rc == 1
