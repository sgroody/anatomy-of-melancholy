"""`burton check`: the definition of "done" for a unit (CLAUDE.md). Orchestration only.

Runs the pipeline (ingest, build both profiles) and then the verifiers. The verifiers themselves
live in burton.verify and never import the code they check.
"""

from .ingest import run as ingest_run
from .site import build
from .verify import checks, site_checks


def check_all(units: list[str]) -> int:
    ingest_run.ingest(units)
    results = checks.text_results(units)
    for profile in ("private", "public"):
        build.build(units, profile=profile)
    results += site_checks.site_results(units)
    return 0 if checks.report(results) else 1
