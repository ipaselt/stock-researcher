import argparse
import sys

from . import __version__

TICKER_COMMANDS = ["run", "snapshot", "score", "assemble", "verify-citations"]


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
    print(f"{args.command}: not implemented yet (slice S1-S3)", file=sys.stderr)
    return 2
