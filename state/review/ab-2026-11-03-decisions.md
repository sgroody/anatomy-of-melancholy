# Reader A/B round 1: owner's choices (2026-11-03)

Page: `state/review/ab-2026-11-03.html` (private build, Gowland as base). The owner's choices are recorded verbatim, with what each means for the build.

| Test | Choice | Owner's note | What follows |
|---|---|---|---|
| T1 headings | Neither | "Sending image of the page layout in the print book." | Match the Penguin page: "THE / FIRST PARTITION." in large spaced capitals; "THE FIRST" followed by a brace and "SECTION. / MEMBER. / SUBSECTION." stacked in small capitals; the title in italic, centred. Round 2 confirms it. |
| T2 initials | B (decorated block) | "See https://github.com/azlen/initialis if it's appropriate to make fitting ones." | Check initialis's licence and method (round 2). |
| T3 note kinds | A (small-caps word) | | Margin notes are labelled Burton / trans. / cites / Bible / gloss / note / restored. |
| T4 note span | B (phrase after the marker) | | Hovering a note lights the words from its marker to the next punctuation, and the reverse; a click pins. |
| T5 citations | A (expansion replaces abbreviation) | | Burton's words stay in the data and show on hover. |
| T6 translations | A (margin, in the language's colour) | | |
| T7 language colour | A (coloured) | | Latin green, Greek blue, Middle English brown, matched in the margin. |
| T8 in-line translations | D (out of the line) | "There should be an option to toggle the translations being in the margins like D or in-line, I think if the "in-line" option is on the english translation should be stylized like the latin is now, colored, italicized, etc" | Margin by default; a reading option puts translations in the line, styled like the foreign text. |
| T9 Burton's own English | Neither | "There should be a better way to signal this. Come back with more." | New options in round 2. |
| T10 typefaces | B (GFS Didot, Chaucer in small capitals) | "I'm torn. Lets go with B for now but save this question for later. Perhaps more options?" | B for now; the question stays open (more options later). |
| T11 wide window | B (notes both sides) | "B definitely, but don't hard commit to only having Burton's notes on the left. Gowland's might be appropriate too. Consider what evens out space-use and get back to me." | Round 2: ways to assign notes to sides that balance the space. |
| T12 long passages | B (facing translation) | | |
| T13 front page | A (one column) | ""Enter, gentle Reader" instead of here beggineth. Perhaps the frontispiece should be larger? Is there a way to design around it, or with it at the core? Perhaps give me other A/Bs on it." | Link reads "Enter, gentle Reader". Round 2: layouts built around the frontispiece. |
| T14 frontispiece | A (stanza in the margin) | "Perhaps the stanzas should always be on the main page, but kind of muted? And hovering over them makes them more readable while highlighting (or magnifying?) the relevant portion of the frontispiece" | Round 2: stanzas always shown, muted; hover brings one up and highlights or magnifies its panel. |
| Behaviours | — | "They're all great! I don't love dotted underlines for names though. Give me alternatives." | Keep the cross-reference lock, name windows, Bible verses and synopsis keys. Round 2: other ways to mark names. |

Also decided in this message:
* Gowland comes first in the translation order by default (private build).
* When credits reset at 3:20 PM, run the new rules pass (in-line citations) and expand the abbreviations.

# Round 2: owner's choices (2026-11-03)

Page: `state/review/ab-2026-11-03-r2.html`.

| Test | Choice | Owner's note | What follows |
|---|---|---|---|
| R1 heading | B | | The Penguin layout ("THE / FIRST PARTITION.", "THE FIRST" with a brace over SECTION, MEMBER, SUBSECTION, italic title), followed by the decorated initial. Initials rendered with initialis (approved). |
| R2 Burton's own English | C (A + C) | | His English takes the Latin's colour in the line, and the margin's translation slot says "Burton's own", with what he left out. |
| R3 sides | — | "B with C's rule as the overflow BUT translations should go on the right, commentaries on the left" | Left: commentary (Gowland's glosses and explanatory notes). Right: Burton's notes with every translation. A note crosses to the other side when its own side is full near its words. |
| R4 front page | B | | The engraving held large on the left while the right side scrolls (title, "Enter, gentle Reader", the synopses collapsed, the contents); hovering a panel shows its stanza. |
| R5 names | C | | A hairline underline in the rule colour, red on hover. |
| R6 in-line switch | B | "But remove the LAT, etc in these cases as it's already clear from the style that it's translated" | "Translations in the line" puts the English in place of the Latin, coloured and italic, with no language tag; the Latin on hover. |

Also in this message:
* Burton's in-line citations move to the margin, leaving a placeholder symbol in the text. Options to come.
* Gowland is the base of the private build. Withhold his matter from model input only where that suits the final private product.

# Round 3 and the Gowland rule (2026-11-03)

* C1 in-line citations: **C**. The author's name stays in Burton's sentence, with a raised § after it in the citation colour. The reference moves to the margin, and Burton's own words show on hover. A Bible reference has no name to keep, so only the § stays.
* I1 initials: **red** (IM Fell French Canon, rubric block; `data/source/INITIALS.lock`).
* Gowland's findings: "Academic identification of citations is not copyright protected … It is in fact the most reliable move and the one we should employ. If you are going to keep them independent, just use his findings in the final private product. But yes, employ him in auditing." CLAUDE.md rule 5 is narrowed to match: his wording is never copied into a layer, his findings may be used with credit, and a model may see his matter in private-only audits and identification runs.
* "Make sure Gowland's endnotes are properly sorted by their nature and are interactable in the way the rest of the notes are."
