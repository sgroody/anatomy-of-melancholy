"""Permanent id registry (data/ids/registry.tsv).

Ids are minted once and reused on every re-ingest. A row is matched by (unit, kind, locator,
fingerprint). Rows that no longer match anything are marked retired, never deleted, and their
numbers are never reused.
"""

import csv
from dataclasses import dataclass

from . import paths

FIELDS = ["id", "unit", "kind", "locator", "fingerprint", "status"]


@dataclass
class Row:
    id: str
    unit: str
    kind: str
    locator: str
    fingerprint: str
    status: str = "active"


class Registry:
    def __init__(self, path=paths.IDS):
        self.path = path
        self.rows: list[Row] = []
        if path.exists():
            with path.open(encoding="utf-8", newline="") as f:
                for r in csv.DictReader(f, delimiter="\t"):
                    self.rows.append(Row(**r))
        self._seen: set[str] = set()

    def _next_n(self, unit: str, kind: str) -> int:
        prefix = f"{unit}-{kind}"
        ns = [int(r.id[len(prefix):]) for r in self.rows
              if r.unit == unit and r.kind == kind and r.id[len(prefix):].isdigit()]
        return max(ns, default=0) + 1

    def assign(self, unit: str, kind: str, locator: str, fingerprint: str = "") -> str:
        for r in self.rows:
            if (r.unit, r.kind, r.locator, r.fingerprint) == (unit, kind, locator, fingerprint):
                if r.id in self._seen:
                    raise ValueError(f"locator matched twice in one ingest: {locator}")
                r.status = "active"
                self._seen.add(r.id)
                return r.id
        # Re-identification: the same text in the same container keeps its id even when the locator
        # scheme or the passages around it changed (e.g. better detection inserted a passage before it).
        if fingerprint:
            base = locator.split("|", 1)[0]
            for r in self.rows:
                same = (r.unit, r.kind, r.fingerprint) == (unit, kind, fingerprint)
                if same and r.id not in self._seen and r.locator.split("|", 1)[0] == base:
                    r.locator, r.status = locator, "active"
                    self._seen.add(r.id)
                    return r.id
        new = Row(f"{unit}-{kind}{self._next_n(unit, kind)}", unit, kind, locator, fingerprint)
        self.rows.append(new)
        self._seen.add(new.id)
        return new.id

    def finish_unit(self, unit: str, kinds: tuple[str, ...] | None = None) -> int:
        """Retire rows of this unit that were not matched in this run. Returns how many. `kinds` limits it to
        the kinds the run assigns (an ingest never sees the layers' own ids, such as glosses, `g`)."""
        n = 0
        for r in self.rows:
            if kinds is not None and r.kind not in kinds:
                continue
            if r.unit == unit and r.id not in self._seen and r.status != "retired":
                r.status = "retired"
                n += 1
        return n

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS, delimiter="\t", lineterminator="\n")
            w.writeheader()
            for r in self.rows:
                w.writerow(r.__dict__)
        tmp.replace(self.path)
