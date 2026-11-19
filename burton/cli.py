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
    s.add_argument("--select", type=Path, help="translate only the items in a selection file (data/eval/m4-pilot.yaml)")
    s.add_argument("--budget-usd", type=float, default=None,
                   help="stop before the next packet once this much list-equivalent cost is spent in this run")
    s.add_argument("--wait-on-limit", action="store_true",
                   help="at a usage limit, wait and try again instead of stopping")
    s.add_argument("--redo", action="store_true",
                   help="with --select: translate the selected items again even if their records are current")

    s = sub.add_parser("align-djs", help="align Dell & Jordan-Smith (1927) to selected passages -> data/layers/djs/")
    s.add_argument("--select", type=Path, help="selection file, e.g. data/eval/m4-pilot.yaml")
    s.add_argument("--unit", action="append")
    s.add_argument("--all", action="store_true", help="every unit in the book")

    s = sub.add_parser("djs-audit", help="second rater (model, blind) for a Dell & Jordan-Smith held-out round")
    s.add_argument("--round", default="h2")
    s.add_argument("--compare-only", action="store_true")

    s = sub.add_parser("tr-audit", help="M5 spot-check: blind second rater (model) for data/eval/m5-spotcheck.yaml")
    s.add_argument("--compare-only", action="store_true")

    s = sub.add_parser("pilot-report", help="M4 pilot: counts -> verify/reports/m4-pilot.json, review page")
    s.add_argument("--select", type=Path, default=Path("data/eval/m4-pilot.yaml"))

    s = sub.add_parser("xrefs", help="Burton's explicit cross-references -> data/layers/xrefs/")
    s.add_argument("--unit", action="append")

    s = sub.add_parser("citations", help="parse Burton's sidenote citations (rules only) -> data/layers/citations/")
    s.add_argument("--unit", action="append")

    s = sub.add_parser("citations-inline", help="citations in Burton's running text (rules only) -> "
                                                "data/layers/citations-inline/")
    s.add_argument("--unit", action="append")

    s = sub.add_parser("expand-citations", help="model expansion of the citations the rules leave unidentified or "
                                                "partial -> data/layers/citation-expansions/")
    s.add_argument("--unit", action="append")
    s.add_argument("--model", default="claude-opus-5-5")
    s.add_argument("--packet-size", type=int, default=25)
    s.add_argument("--max-packets", type=int, default=None)
    s.add_argument("--budget-usd", type=float, default=None,
                   help="stop before the next packet once this much list-equivalent cost is spent in this run")
    s.add_argument("--dry-run", action="store_true", help="count the items and run the leak test, no model")

    s = sub.add_parser("psalm-check", help="which KJV verse each Psalm citation means (model, ledgered, private-only) "
                                           "-> data/layers/psalm-check/")
    s.add_argument("--model", default="claude-opus-5-5")
    s.add_argument("--budget-usd", type=float, default=None)
    s.add_argument("--dry-run", action="store_true", help="count the citations, no model")
    s = sub.add_parser("names-sweep", help="obscure names identified for the reader (model, ledgered) "
                                           "-> data/layers/names/forms.json")
    s.add_argument("--model", default="claude-opus-5-5")
    s.add_argument("--budget-usd", type=float, default=None)
    s.add_argument("--limit", type=int, default=None, help="ask about the first N forms only (a spot check)")
    s.add_argument("--dry-run", action="store_true", help="count the forms, no model")
    s = sub.add_parser("restored-read", help="restored notes: tie to Burton's English, translate the rest, expand "
                                             "citations, kind (model, ledgered) -> data/layers/restored-read/")
    s.add_argument("--model", default="claude-opus-5-5")
    s.add_argument("--budget-usd", type=float, default=None)
    s.add_argument("--limit", type=int, default=None, help="read the first N notes only (a spot check)")
    s.add_argument("--dry-run", action="store_true", help="count the notes, no model")
    s = sub.add_parser("cite-sweep", help="citations in the running text the rules missed (model, ledgered) "
                                          "-> data/layers/citations-inline-model/")
    s.add_argument("--model", default="claude-opus-5-5")
    s.add_argument("--budget-usd", type=float, default=None)
    s.add_argument("--limit", type=int, default=None, help="read the first N candidates only (a spot check)")
    s.add_argument("--dry-run", action="store_true", help="count the candidates, no model")
    s = sub.add_parser("sweep-audit", help="blind check of what the stage-14 sweeps would show (model, ledgered)")
    s.add_argument("--draw", action="store_true", help="draw the samples (once)")
    s.add_argument("--run", action="store_true", help="judge the samples")
    s.add_argument("--report", action="store_true", help="counts and the rule's outcome -> data/eval/sweep-audit.yaml")
    s.add_argument("--model", default="claude-opus-5-5")
    s = sub.add_parser("note-rate", help="the translation passes' notes: spot check, blind audit, rating for the "
                                         "margin (model, ledgered) -> data/layers/note-ratings/")
    s.add_argument("--draw", action="store_true", help="draw the spot-check sample (once)")
    s.add_argument("--audit", action="store_true", help="blind second rater on the spot-check sample")
    s.add_argument("--compare", action="store_true", help="first rater against the second; the rules' outcome")
    s.add_argument("--all", action="store_true", help="rate every note")
    s.add_argument("--sample", action="store_true", help="rate the spot-check sample's notes only")
    s.add_argument("--model", default="claude-opus-5-5")
    s.add_argument("--budget-usd", type=float, default=None)
    s = sub.add_parser("cite-audit", help="held-out check of the citation expansions, with Gowland's notes as "
                                          "evidence (private-only)")
    s.add_argument("--model", default="claude-opus-5-5")
    s.add_argument("--budget-usd", type=float, default=None)
    s.add_argument("--report", action="store_true", help="compare -> state/review/cite-audit.md")
    s.add_argument("--dry-run", action="store_true", help="draw the sample and count, no model")

    s = sub.add_parser("authors", help="author registry skeletons (data/authors/) and the owner's top-100 list")
    s.add_argument("--review", action="store_true", help="also write state/review/authors-top100.md")
    s.add_argument("--wikidata", action="store_true", help="match cited authors to Wikidata (rules, network)")

    sub.add_parser("restore-notes", help="Burton's sidenotes missing from Gowland's edition, from Project Gutenberg "
                                         "#10800 (rules) -> data/layers/restored-notes/")

    s = sub.add_parser("gold-audit", help="D7: blind second rater on the language-ID gold labels")
    s.add_argument("--model", default="claude-opus-5-5")
    s.add_argument("--budget-usd", type=float, default=None)
    s.add_argument("--report", action="store_true", help="compare the raters -> state/review/d7-gold-audit.md")
    s.add_argument("--label-round", help="label a drawn hold-out round that has no gold yet (e.g. h3)")
    s.add_argument("--dry-run", action="store_true", help="count the items and run the leak test, no model")

    s = sub.add_parser("obsolete", help="obsolete-word glosses: Webster 1913 candidates, model ruling -> "
                                        "data/layers/obsolete/")
    s.add_argument("--model", default="claude-opus-5-5")
    s.add_argument("--packet-size", type=int, default=40)
    s.add_argument("--max-packets", type=int, default=None)
    s.add_argument("--budget-usd", type=float, default=None,
                   help="stop before the next packet once this much list-equivalent cost is spent in this run")
    s.add_argument("--dry-run", action="store_true", help="count the candidates, without calling the model")

    s = sub.add_parser("author-drafts", help="model-drafted author entries (machine-draft) -> data/authors/")
    s.add_argument("--top", type=int, default=None, help="only the N most-cited authors")
    s.add_argument("--model", default="claude-opus-5-5")
    s.add_argument("--packet-size", type=int, default=15)
    s.add_argument("--max-packets", type=int, default=None)
    s.add_argument("--budget-usd", type=float, default=None,
                   help="stop before the next packet once this much list-equivalent cost is spent in this run")
    s.add_argument("--dry-run", action="store_true", help="count what would be sent, without calling the model")

    s = sub.add_parser("xrefs-relative", help="relative cross-references: model proposals for the owner's review")
    s.add_argument("--model", default="claude-opus-5-5")
    s.add_argument("--packet-size", type=int, default=15)
    s.add_argument("--budget-usd", type=float, default=None,
                   help="stop before the next packet once this much list-equivalent cost is spent in this run")
    s.add_argument("--dry-run", action="store_true", help="only count the candidates")

    sub.add_parser("corpora", help="convert downloaded corpora to data/source/corpora/ for verify-sources")

    s = sub.add_parser("syn-audit", help="M7: blind model reading of the sampled synopsis strings' parents "
                                         "(images + hidden text only); --report compares with the trees")
    s.add_argument("--model", default="claude-opus-5-5")
    s.add_argument("--report", action="store_true")
    s.add_argument("--dry-run", action="store_true")

    s = sub.add_parser("m6-audit", help="independent model checkers for the M6 review items")
    s.add_argument("kind", choices=["authors", "xrefs", "sources", "report"])
    s.add_argument("--model", default="claude-opus-5-5")
    s.add_argument("--packet-size", type=int, default=15)
    s.add_argument("--budget-usd", type=float, default=None,
                   help="stop before the next packet once this much list-equivalent cost is spent in this run")
    s.add_argument("--dry-run", action="store_true")

    s = sub.add_parser("synopses", help="M7 synopses: structure + hidden text -> data/synopses/<pN>.json "
                                        "(--checklist writes the word-level checklists to state/m7/)")
    s.add_argument("--checklist", action="store_true")
    s.add_argument("--part", action="append", choices=["p1", "p2", "p3"])

    s = sub.add_parser("verify-sources", help="verify quotation sources against local corpora (rules)")
    s.add_argument("--unit", action="append")

    s = sub.add_parser("selftrans", help="self-translation signals per foreign passage -> data/layers/selftrans/")
    s.add_argument("--unit", action="append")
    s.add_argument("--all", action="store_true", help="every unit in the book (the default without --unit)")

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
    s.add_argument("--open", action="store_true", help="open the edition in the default browser")

    s = sub.add_parser("export-artifact", help="adjust a built site for hosting as a claude.ai Artifact")
    s.add_argument("--profile", choices=["private", "public"], default="private")

    s = sub.add_parser("axe", help="axe-core on every page of a built site, both themes (M8: full-site V10)")
    s.add_argument("--profile", choices=["private", "public"], default="private")
    s.add_argument("--all", action="store_true", help="every page (the default is the 22-page sample)")

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
            max_packets=args.max_packets, dry_run=args.dry_run, select=args.select,
            budget_usd=args.budget_usd, wait_on_limit=args.wait_on_limit, redo=args.redo,
        )
    elif args.cmd == "align-djs":
        from .layers import djs

        if not (args.select or args.unit or args.all):
            p.error("align-djs needs --select, --unit or --all")
        print(djs.run(args.select, _units(args) if (args.unit or args.all) else None))
    elif args.cmd == "djs-audit":
        import json

        from .layers import djs_audit

        rep = djs_audit.compare(args.round) if args.compare_only else djs_audit.run(args.round)
        print(json.dumps(rep, ensure_ascii=False, indent=2))
    elif args.cmd == "tr-audit":
        import json

        from .translate import audit

        print(json.dumps(audit.compare() if args.compare_only else audit.run(), ensure_ascii=False, indent=2))
    elif args.cmd == "pilot-report":
        import json

        from .fsutil import atomic_write_text
        from .layers import djs
        from .translate import pilot

        rep = pilot.report(args.select)
        rep["djs_sidenotes"] = {k: v for k, v in djs.sidenote_study().items() if k != "rows"}
        out = paths.ROOT / "verify" / "reports"
        atomic_write_text(out / "m4-pilot.json", json.dumps(rep, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
        pilot.review_page(args.select, out / "m4-review.html")
        for m, v in rep["verdicts"].items():
            print(m, {k: x for k, x in v.items() if k != "wrong"}, rep["honesty"][m]["source_status"])
        print("djs:", rep["djs"], "sidenotes:", rep["djs_sidenotes"]["counts"])
        print("wrote verify/reports/m4-pilot.json and verify/reports/m4-review.html")
    elif args.cmd == "xrefs":
        from .layers import xrefs

        print(dict(xrefs.build(_units(args) if args.unit else None)))
    elif args.cmd == "citations":
        from .layers import citations

        stats = citations.build(args.unit)
        for k in sorted(stats):
            print(f"  {k}: {stats[k]}")
    elif args.cmd == "citations-inline":
        from .layers import citations_inline

        stats = citations_inline.build(args.unit)
        for k in sorted(stats):
            print(f"  {k}: {stats[k]}")
    elif args.cmd == "psalm-check":
        from .layers import psalm_check

        stats = psalm_check.run(model=args.model, budget_usd=args.budget_usd, dry_run=args.dry_run)
        for k in sorted(stats):
            print(f"  {k}: {stats[k]}")
    elif args.cmd == "names-sweep":
        from .layers import names_sweep

        stats = names_sweep.run(model=args.model, budget_usd=args.budget_usd, dry_run=args.dry_run, limit=args.limit)
        for k in sorted(stats):
            print(f"  {k}: {stats[k]}")
    elif args.cmd == "restored-read":
        from .layers import restored_read

        stats = restored_read.run(model=args.model, budget_usd=args.budget_usd, dry_run=args.dry_run,
                                  limit=args.limit)
        for k in sorted(stats):
            print(f"  {k}: {stats[k]}")
    elif args.cmd == "cite-sweep":
        from .layers import cite_sweep

        stats = cite_sweep.run(model=args.model, budget_usd=args.budget_usd, dry_run=args.dry_run, limit=args.limit)
        for k in sorted(stats):
            print(f"  {k}: {stats[k]}")
    elif args.cmd == "sweep-audit":
        import json

        from .layers import sweep_audit

        if args.draw:
            print(sweep_audit.draw())
        if args.run:
            print(sweep_audit.run(model=args.model))
        if args.report:
            print(json.dumps(sweep_audit.report(), ensure_ascii=False, indent=1))
    elif args.cmd == "note-rate":
        import json

        from .translate import notes_rate

        if args.draw:
            print(notes_rate.draw())
        if args.audit:
            print(notes_rate.run_audit(model=args.model))
        if args.all or args.sample:
            print(notes_rate.run_rate(model=args.model, budget_usd=args.budget_usd,
                                      which=notes_rate.sample_ids() if args.sample else None))
        if args.compare:
            print(json.dumps(notes_rate.compare(), ensure_ascii=False, indent=1))
    elif args.cmd == "cite-audit":
        from .layers import cite_audit

        stats = cite_audit.report(args.model) if args.report else \
            cite_audit.run(model=args.model, budget_usd=args.budget_usd, dry_run=args.dry_run)
        for k in sorted(stats):
            print(f"  {k}: {stats[k]}")
    elif args.cmd == "expand-citations":
        from .layers import cite_expand

        stats = cite_expand.run(model=args.model, packet_size=args.packet_size, budget_usd=args.budget_usd,
                                max_packets=args.max_packets, dry_run=args.dry_run, units=args.unit)
        for k in sorted(stats):
            print(f"  {k}: {stats[k]}")
    elif args.cmd == "authors":
        from .layers import authors

        print(dict(authors.build()))
        if args.wikidata:
            from .layers import wikidata

            print("wikidata:", dict(wikidata.run()))
        if args.review:
            print(dict(authors.review_list()))
    elif args.cmd == "restore-notes":
        from .layers import restored_notes

        print(dict(restored_notes.run()))
    elif args.cmd == "gold-audit":
        from .layers import gold_audit

        if args.label_round:
            print(gold_audit.label_round(args.label_round, model=args.model))
        elif args.report:
            print(gold_audit.report())
        elif args.dry_run:
            its = gold_audit.items()
            bad = [i["id"] for i in its if gold_audit.leaks(i["unit"], i["text"] + " " + i["context"])]
            print(f"{len(its)} items; leak test: {len(bad)} with Gowland text {bad[:5]}")
        else:
            print(gold_audit.run(model=args.model, budget_usd=args.budget_usd))
    elif args.cmd == "obsolete":
        from .layers import obsolete

        print(dict(obsolete.run(model=args.model, packet_size=args.packet_size, budget_usd=args.budget_usd,
                                max_packets=args.max_packets, dry_run=args.dry_run)))
    elif args.cmd == "author-drafts":
        from .layers import author_drafts

        if args.dry_run:
            items = author_drafts.todo(args.top, args.model)
            print(len(items), "authors to draft; first:", [i["id"] for i in items[:10]])
            return 0
        print(dict(author_drafts.run(top=args.top, model=args.model, packet_size=args.packet_size,
                                     budget_usd=args.budget_usd, max_packets=args.max_packets)))
    elif args.cmd == "xrefs-relative":
        from .layers import xrefs_relative

        print(dict(xrefs_relative.run(model=args.model, packet_size=args.packet_size, budget_usd=args.budget_usd,
                                      dry_run=args.dry_run)))
    elif args.cmd == "corpora":
        from .layers import corpora

        print(corpora.convert())
    elif args.cmd == "syn-audit":
        import json

        from .layers import syn_audit

        if args.report:
            print(json.dumps(syn_audit.report(), indent=1))
        else:
            print(syn_audit.run(args.model, dry_run=args.dry_run))
    elif args.cmd == "m6-audit":
        from .layers import m6_audit

        if args.kind == "report":
            import json

            print(json.dumps(m6_audit.report(), indent=1))
            return 0
        print(dict(m6_audit.run(args.kind, model=args.model, packet_size=args.packet_size,
                                budget_usd=args.budget_usd, dry_run=args.dry_run)))
    elif args.cmd == "synopses":
        import json

        from .ingest import synopses

        if args.checklist:
            print(json.dumps(synopses.checklist(), indent=1))
        else:
            print(json.dumps(synopses.run(args.part), ensure_ascii=False, indent=1))
    elif args.cmd == "verify-sources":
        from .layers import sources

        print(dict(sources.run(args.unit)))
    elif args.cmd == "selftrans":
        from .layers import selftrans

        stats = selftrans.build(args.unit if args.unit and not args.all else None)
        for k in sorted(stats):
            print(f"  {k}: {stats[k]}")
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

        serve.serve(args.profile, args.port, open_browser=args.open)
    elif args.cmd == "export-artifact":
        from .site import export

        print(export.export(args.profile))
    elif args.cmd == "axe":
        from .verify import browser, checks

        res = browser.axe_check(args.profile, full=args.all)
        return 0 if checks.report([res], name=f"axe-{args.profile}{'-all' if args.all else ''}") else 1
    elif args.cmd == "check":
        from .pipeline import check_all

        return check_all(_units(args), browser_checks=not args.no_browser)
    return 0


if __name__ == "__main__":
    sys.exit(main())
