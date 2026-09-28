import argparse
import dataclasses
import datetime as dt
import json
import re
import sys
from pathlib import Path

from . import __version__, citations, ledger, report
from .providers import TickerNotFound, get_provider
from .fair_value import compute_fair_value
from .labels import suggest_label
from .scorecard import score_snapshot
from .snapshot import build_snapshot, from_json, to_json

TICKER_COMMANDS = ["run", "snapshot", "score", "assemble", "verify-citations"]
TICKER_RE = re.compile(r"^[A-Z][A-Z.\-]{0,5}$")
# Windows device names: data/CON.json would resolve to the console, not a file.
RESERVED_NAMES = {"CON", "PRN", "AUX", "NUL"} | {f"{p}{n}" for p in ("COM", "LPT") for n in range(1, 10)}


def _ticker_error(ticker: str) -> str | None:
    """Why `ticker` (already upper-cased) cannot be used as a data/ file name, or None if it can."""
    if not TICKER_RE.fullmatch(ticker):
        return f"invalid ticker {ticker!r}"
    if ticker.split(".")[0] in RESERVED_NAMES:
        return f"ticker {ticker!r} is a reserved Windows device name and cannot be written to data/"
    return None


def _checked(ticker: str) -> str | None:
    """The upper-cased ticker, or None after printing why it cannot be used."""
    ticker = ticker.upper()
    if error := _ticker_error(ticker):
        print(error, file=sys.stderr)
        return None
    return ticker


def _write_snapshot(ticker: str) -> bool:
    try:
        snapshot = build_snapshot(get_provider(), ticker)
    except TickerNotFound:
        print(f"ticker not found: {ticker}", file=sys.stderr)
        return False
    out = Path("data") / f"{ticker}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(to_json(snapshot), encoding="utf-8")
    meta = snapshot.meta
    print(f"wrote {out.as_posix()} ({len(meta.fields_missing)} fields missing, {len(meta.warnings)} warnings)")
    return True


def _load_snapshot(ticker: str):
    """The Snapshot read from data/<T>.json, or None after printing why not."""
    src = Path("data") / f"{ticker}.json"
    if not src.exists():
        print(f"no snapshot at {src.as_posix()}; run `snapshot {ticker}` first", file=sys.stderr)
        return None
    try:
        return from_json(src.read_text(encoding="utf-8"))
    except (ValueError, TypeError) as err:
        print(f"unreadable snapshot {src.as_posix()}: {err}", file=sys.stderr)
        return None


def _write_score(ticker: str, snapshot):
    """Score the snapshot, write data/<T>.score.json, print the score line; return (score, fv, label)."""
    score = score_snapshot(snapshot)
    fv = compute_fair_value(snapshot, score.total)
    label = suggest_label(score, fv, snapshot)
    result = {
        "ticker": ticker,
        "as_of": snapshot.meta.as_of,
        "price": snapshot.meta.price,
        "total": score.total,
        "band_word": score.band_word,
        "coverage_pct": score.coverage_pct,
        "categories": {name: dataclasses.asdict(c) for name, c in score.categories.items()},
        "metrics": [dataclasses.asdict(m) for m in score.metrics],
        "fair_value": dataclasses.asdict(fv),
        "label_suggestion": dataclasses.asdict(label),
    }
    out = Path("data") / f"{ticker}.score.json"
    out.write_text(json.dumps(result, indent=2, allow_nan=False), encoding="utf-8")
    total = "n/a" if score.total is None else f"{score.total:.1f} ({score.band_word})"
    entry = "n/a" if label.entry_target is None else f"{label.entry_target:.2f}"
    print(f"{ticker}: score {total}, coverage {score.coverage_pct:.0%}, label {label.label} ({label.rule_id}), entry {entry}")
    return score, fv, label


def cmd_snapshot(ticker: str) -> int:
    ticker = _checked(ticker)
    return 0 if ticker and _write_snapshot(ticker) else 2


def cmd_score(ticker: str) -> int:
    ticker = _checked(ticker)
    snapshot = ticker and _load_snapshot(ticker)
    if not snapshot:
        return 2
    _write_score(ticker, snapshot)
    return 0


def cmd_run(ticker: str, offline: bool = False) -> int:
    """snapshot -> score -> data/<T>/skeleton.md, always regenerated; clears the previous run's data/<T>/*.md.

    --offline reuses today's data/<T>.json instead of fetching (the snapshot file is left untouched).
    """
    ticker = _checked(ticker)
    if not ticker:
        return 2
    if offline:
        snapshot = _load_snapshot(ticker) if (Path("data") / f"{ticker}.json").exists() else None
        if not snapshot or snapshot.meta.as_of != dt.date.today().isoformat():
            print(f"no fresh snapshot for {ticker}; run without --offline", file=sys.stderr)
            return 2
    else:
        if not _write_snapshot(ticker):
            return 2
        snapshot = _load_snapshot(ticker)
        if not snapshot:
            return 2
    score, fv, label = _write_score(ticker, snapshot)
    out = Path("data") / ticker / "skeleton.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    for stale in out.parent.glob("*.md"):  # agent files, verdict, old skeleton: a new run starts clean
        stale.unlink()
    out.write_text(report.render_skeleton(snapshot, score, fv, label), encoding="utf-8")
    print(f"wrote {out.as_posix()}")
    return 0


def cmd_verify_citations(ticker: str) -> int:
    """Check every agent file's citations; 0 all PASS, 1 any FAIL, 2 snapshot/score missing or nothing to check."""
    ticker = _checked(ticker)
    if not ticker:
        return 2
    try:
        results = citations.verify(ticker, Path("data"))
    except (FileNotFoundError, ValueError) as err:
        print(f"verify-citations {ticker}: {err}", file=sys.stderr)
        return 2
    if not results:
        print(f"verify-citations {ticker}: no agent reports in data/{ticker}/", file=sys.stderr)
        return 2
    for agent, result in results.items():
        print(f"{result['status']} {agent}")
        for line in result["failures"]:
            print(f"  {line}")
    print(f"wrote data/{ticker}/citations.json")
    return 1 if any(r["status"] == "FAIL" for r in results.values()) else 0


def cmd_ledger() -> int:
    print(f"ledger: {ledger.rebuild(Path('reports'))} rows")
    return 0


def cmd_assemble(ticker: str, date: str | None) -> int:
    ticker = _checked(ticker)
    if not ticker:
        return 2
    try:
        today = (dt.date.fromisoformat(date) if date else dt.date.today()).isoformat()
    except ValueError:
        print(f"invalid --date {date!r}; expected YYYY-MM-DD", file=sys.stderr)
        return 2
    try:
        out = report.assemble(ticker, Path("data"), Path("reports"), today)
    except (FileNotFoundError, ValueError) as err:
        print(f"assemble {ticker}: {err}", file=sys.stderr)
        return 2
    print(f"wrote {out.as_posix()}")
    return cmd_ledger()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="stock_researcher")
    parser.add_argument("--version", action="store_true", help="print version and exit")
    sub = parser.add_subparsers(dest="command")
    for name in TICKER_COMMANDS:
        cmd = sub.add_parser(name)
        cmd.add_argument("ticker")
        if name == "assemble":
            cmd.add_argument("--date", help="report date YYYY-MM-DD (default: today)")
        if name == "run":
            cmd.add_argument("--offline", action="store_true", help="reuse today's data/<T>.json instead of fetching")
    sub.add_parser("ledger")

    args = parser.parse_args(argv)
    if args.version:
        print(__version__)
        return 0
    if args.command is None:
        parser.print_help()
        return 0
    if args.command == "snapshot":
        return cmd_snapshot(args.ticker)
    if args.command == "score":
        return cmd_score(args.ticker)
    if args.command == "run":
        return cmd_run(args.ticker, args.offline)
    if args.command == "assemble":
        return cmd_assemble(args.ticker, args.date)
    if args.command == "verify-citations":
        return cmd_verify_citations(args.ticker)
    return cmd_ledger()
