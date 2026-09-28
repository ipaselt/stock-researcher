import argparse
import re
import sys
from pathlib import Path

from . import __version__
from .providers import TickerNotFound, get_provider
from .snapshot import build_snapshot, to_json

TICKER_COMMANDS = ["run", "snapshot", "score", "assemble", "verify-citations"]
TICKER_RE = re.compile(r"^[A-Z][A-Z.\-]{0,5}$")
# Windows device names: data/CON.json would resolve to the console, not a file.
RESERVED_NAMES = {"CON", "PRN", "AUX", "NUL"} | {f"{p}{n}" for p in ("COM", "LPT") for n in range(1, 10)}


def cmd_snapshot(ticker: str) -> int:
    ticker = ticker.upper()
    if not TICKER_RE.fullmatch(ticker):
        print(f"invalid ticker {ticker!r}", file=sys.stderr)
        return 2
    if ticker.split(".")[0] in RESERVED_NAMES:
        print(f"ticker {ticker!r} is a reserved Windows device name and cannot be written to data/", file=sys.stderr)
        return 2
    try:
        snapshot = build_snapshot(get_provider(), ticker)
    except TickerNotFound:
        print(f"ticker not found: {ticker}", file=sys.stderr)
        return 2
    out = Path("data") / f"{ticker}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(to_json(snapshot), encoding="utf-8")
    meta = snapshot.meta
    print(f"wrote {out.as_posix()} ({len(meta.fields_missing)} fields missing, {len(meta.warnings)} warnings)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="stock_researcher")
    parser.add_argument("--version", action="store_true", help="print version and exit")
    sub = parser.add_subparsers(dest="command")
    for name in TICKER_COMMANDS:
        sub.add_parser(name).add_argument("ticker")
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
    print(f"{args.command}: not implemented yet (slice S1-S3)", file=sys.stderr)
    return 2
