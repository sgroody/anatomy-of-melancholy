# Decisions to revisit

Choices the owner made provisionally and asked to look at again later. Each: what was chosen, when, and where it is
built. Remove an entry only when the owner has revisited it.

| Decision | Chosen | Date | Where |
|---|---|---|---|
| P3 (round 7): the rubric rule on one of Burton's notes in the left margin | B, on the side facing the text (right in the left margin, left in the right) | 2026-11-19 | `edition.css`, `.sidenote.mn-l` |
| H (round 8): how a folded brace of the synopses opens on rest | H2 Grow (the branch opens one brace at a time while the pointer rests on the broader brace), "but it feels a little too chaotic": reworked the same day with the windows' hold indicator drawn along the brace | 2026-11-19 | `edition.js` (the synopses' rest: fill, open, fix, grow) and `edition.css` (`.syn-filling`); in the edition since 2026-11-19, the record in `tools/synopsis_sheets/proto.html`. Pace unconfirmed: 0.65 s to open, 0.9 s to fix, ~0.75 s per inner brace, 0.9 s before an unfixed branch folds; 2026-11-20 the signs of a rest made clearer |
