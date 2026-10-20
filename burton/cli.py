"""Single entry point: `uv run burton <command>`."""

import argparse
import sys
from pathlib import Path

from . import paths


def _units(args) -> list[str]:
    return args.unit or ["1.1.1.2"]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="burton", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("unpack", help="copy and pin the EPUB, unzip it to work/")
    s.add_argument("epub", nargs="?", type=Path, default=paths.DEFAULT_EPUB)

    sub.add_parser("counts", help="print whole-book counts from the independent EPUB counter")

    for name, text in (
        ("ingest", "EPUB -> data/text/<unit>.xml"),
        ("verify", "run text checks (V1-V4, V7) for units"),
    ):
        s = sub.add_parser(name, help=text)
        s.add_argument("--unit", action="append", help="unit id, e.g. 1.1.1.2 (repeatable)")

    s = sub.add_parser("translate", help="resumable claude -p translation runner")
    s.add_argument("--unit", action="append")
    s.add_argument("--model", default="claude-opus-5-5")
    s.add_argument("--packet-size", type=int, default=20)
    s.add_argument("--max-packets", type=int, default=None)
    s.add_argument("--dry-run", action="store_true", help="write packets to state/ without calling the model")

    s = sub.add_parser("fonts", help="fetch the pinned OFL fonts into data/source/fonts")

    s = sub.add_parser("build", help="generate the site")
    s.add_argument("--unit", action="append")
    s.add_argument("--profile", choices=["private", "public"], default="private")

    s = sub.add_parser("serve", help="serve the built site on 127.0.0.1")
    s.add_argument("--profile", choices=["private", "public"], default="private")
    s.add_argument("--port", type=int, default=8765)

    s = sub.add_parser("check", help="ingest, verify, build both profiles and verify the site")
    s.add_argument("--unit", action="append")

    args = p.parse_args(argv)

    if args.cmd == "unpack":
        from .source import unpack

        unpack(args.epub)
    elif args.cmd == "counts":
        from .verify import epub_counts

        epub_counts.print_book_counts(paths.XHTML)
    elif args.cmd == "ingest":
        from .ingest import run

        run.ingest(_units(args))
    elif args.cmd == "verify":
        from .verify import checks

        return checks.verify_text(_units(args))
    elif args.cmd == "translate":
        from .translate import runner

        return runner.run(
            _units(args), model=args.model, packet_size=args.packet_size,
            max_packets=args.max_packets, dry_run=args.dry_run,
        )
    elif args.cmd == "fonts":
        from .site import fonts

        fonts.fetch()
    elif args.cmd == "build":
        from .site import build

        build.build(_units(args), profile=args.profile)
    elif args.cmd == "serve":
        from .site import serve

        serve.serve(args.profile, args.port)
    elif args.cmd == "check":
        from .pipeline import check_all

        return check_all(_units(args))
    return 0


if __name__ == "__main__":
    sys.exit(main())
