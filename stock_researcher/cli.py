import argparse
import dataclasses
import datetime as dt
import json
import re
import sys
from pathlib import Path

from . import __version__, ledger, report
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


def cmd_run(ticker: str) -> int:
    """snapshot -> score -> data/<T>/skeleton.md, always regenerated; clears the previous run's data/<T>/*.md."""
    ticker = _checked(ticker)
    if not ticker or not _write_snapshot(ticker):
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
        return cmd_run(args.ticker)
    if args.command == "assemble":
        return cmd_assemble(args.ticker, args.date)
    if args.command == "ledger":
        return cmd_ledger()
    print(f"{args.command}: not implemented yet (slice S5)", file=sys.stderr)
    return 2
