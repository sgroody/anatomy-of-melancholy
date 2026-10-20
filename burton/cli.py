"""Single entry point: `uv run burton <command>`."""

import argparse
import sys
from pathlib import Path

from . import paths


def _units(args) -> list[str]:
    if getattr(args, "all", False):
        from .ingest.epub import all_units

        return all_units()
    return args.unit or ["1.1.1.2"]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="burton", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("unpack", help="copy and pin the EPUB, unzip it to work/")
    s.add_argument("epub", nargs="?", type=Path, default=paths.DEFAULT_EPUB)

    sub.add_parser("counts", help="print whole-book counts from the independent EPUB counter")
    sub.add_parser("lexicon", help="rebuild the book's Latin/English lexicon from a rules-only ingest")

    for name, text in (
        ("ingest", "EPUB -> data/text/<unit>.xml"),
        ("verify", "run text checks (V1-V4, V7) for units"),
    ):
        s = sub.add_parser(name, help=text)
        s.add_argument("--unit", action="append", help="unit id, e.g. 1.1.1.2 (repeatable)")
        s.add_argument("--all", action="store_true", help="every unit in the book")

    s = sub.add_parser("translate", help="resumable claude -p translation runner")
    s.add_argument("--unit", action="append")
    s.add_argument("--all", action="store_true")
    s.add_argument("--model", default="claude-opus-5-5")
    s.add_argument("--packet-size", type=int, default=20)
    s.add_argument("--max-packets", type=int, default=None)
    s.add_argument("--dry-run", action="store_true", help="write packets to state/ without calling the model")

    s = sub.add_parser("xrefs", help="Burton's explicit cross-references -> data/layers/xrefs/")
    s.add_argument("--unit", action="append")

    s = sub.add_parser("adjudicate", help="model rules on language runs the rules left undecided")
    s.add_argument("--unit", action="append")
    s.add_argument("--all", action="store_true")
    s.add_argument("--model", default="claude-opus-5-5")
    s.add_argument("--max-packets", type=int, default=None)
    s.add_argument("--dry-run", action="store_true", help="only count and show candidates")
    s.add_argument("--refresh-vernacular", action="store_true", help="re-rule single-word vernacular rulings")

    s = sub.add_parser("fonts", help="fetch the pinned OFL fonts into data/source/fonts")

    s = sub.add_parser("build", help="generate the site")
    s.add_argument("--unit", action="append")
    s.add_argument("--all", action="store_true")
    s.add_argument("--profile", choices=["private", "public"], default="private")

    s = sub.add_parser("serve", help="serve the built site on 127.0.0.1")
    s.add_argument("--profile", choices=["private", "public"], default="private")
    s.add_argument("--port", type=int, default=8765)

    s = sub.add_parser("check", help="ingest, verify, build both profiles and verify the site")
    s.add_argument("--unit", action="append")
    s.add_argument("--all", action="store_true")
    s.add_argument("--no-browser", action="store_true", help="skip the browser checks (reported as FAIL)")

    args = p.parse_args(argv)
    for stream in (sys.stdout, sys.stderr):  # problems quote Greek; a cp1252 console must not crash
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="backslashreplace")

    if args.cmd == "unpack":
        from .source import unpack

        unpack(args.epub)
    elif args.cmd == "counts":
        from .verify import epub_counts

        epub_counts.print_book_counts(paths.XHTML)
    elif args.cmd == "lexicon":
        import shutil

        from .ingest import lexicon, run
        from .ingest.epub import all_units

        if lexicon.DIR.exists():  # learn from a rules-only ingest, never from the lexicon's own output
            shutil.rmtree(lexicon.DIR)
            lexicon.load.cache_clear()
        units = all_units()
        run.ingest(units, quiet=True)
        print(lexicon.build(units))
        print("now re-run `burton ingest --all` to apply it")
    elif args.cmd == "ingest":
        from .ingest import endnotes, run

        run.ingest(_units(args))
        if args.all:
            print("gowland endnotes:", dict(endnotes.ingest()))
    elif args.cmd == "verify":
        from .verify import checks

        return checks.verify_text(_units(args))
    elif args.cmd == "translate":
        from .translate import runner

        return runner.run(
            _units(args), model=args.model, packet_size=args.packet_size,
            max_packets=args.max_packets, dry_run=args.dry_run,
        )
    elif args.cmd == "xrefs":
        from .layers import xrefs

        print(dict(xrefs.build(_units(args) if args.unit else None)))
    elif args.cmd == "adjudicate":
        from .translate import adjudicate

        if args.dry_run:
            cands = adjudicate.candidates(_units(args))
            print(len(cands), "candidates")
            for c in cands[:15]:
                print(" ", c["unit"], "|", c["run"][:60], "||", c["context"][:100])
            return 0
        return adjudicate.run(_units(args), model=args.model, max_packets=args.max_packets,
                              refresh_vernacular=args.refresh_vernacular)
    elif args.cmd == "fonts":
        from .site import fonts

        fonts.fetch()
    elif args.cmd == "build":
        from .site import build

        build.build(None if args.all else _units(args), profile=args.profile)
    elif args.cmd == "serve":
        from .site import serve

        serve.serve(args.profile, args.port)
    elif args.cmd == "check":
        from .pipeline import check_all

        return check_all(_units(args), browser_checks=not args.no_browser)
    return 0


if __name__ == "__main__":
    sys.exit(main())
