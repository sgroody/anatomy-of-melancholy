# M6 independent checks (owner, 2026-11-02: "Run independent checkers for these")

Each checker is a fresh `claude -p` call with its own versioned prompt and no shared context with the
first pass; it is the same model family, so a shared systematic error could escape both. Answers:
`data/eval/m6-audit-<kind>.jsonl`. Nothing here changes a layer.

## Author drafts (254, prompt `author-audit-v1`)

Identity: {'ok': 250, 'doubtful': 4}. Facts: {'ok': 251, 'minor': 3}. Wikidata match: {'none': 222, 'ok': 32}.

| Author | Identity | Facts | Wikidata | Problems | Reason |
|---|---|---|---|---|---|
| `busbecq` | ok | minor | none | When Busbecq was sent to Suleiman in 1554, Ferdinand was King of the Romans; he only became emperor in 1556/58. | The citations are to Busbecq's Turkish letters and the entry is accurate apart from Ferdinand's title. |
| `cesalpino` | doubtful | ok | none | — | The biography is broadly right, though some sources give his birth as 1524/25, but 'hist. lib. 1' matches no known Cesalpino title, so the attribution needs checking. |
| `freitag` | doubtful | ok | none | — | With no work named, 'Freitagius' could be the physician Johann Freitag or Arnold Freitag of the Mythologia ethica; the draft's doubt is justified. |
| `gordon` | ok | minor | none | Gordon is usually thought to have died around 1320, so 'fl. c. 1270–1330' runs slightly late. | The citations by particula and the de conservatione vitae humanae citation are Bernard de Gordon's; the only issue is a slightly imprecise date range. |
| `peter-martyr-vermigli` | doubtful | ok | none | — | 'Pet. Mart. in Sam.' is Vermigli's Samuel commentary, but the bare 'P. Mart.' could be d'Anghiera, as the draft notes; the biographical facts are correct. |
| `quintilian` | doubtful | ok | none | — | The biography is correct, but the example 'Lib. 1 cap. 11.' has no author name, so identification depends on unseen context. |
| `zanchi` | ok | minor | none | The work's title is 'De operibus Dei intra spatium sex dierum creatis', not 'creatorum'. | The 'de malis angelis' citations are Zanchi's treatise on angels; the only problem is a small slip in the title. |

## Relative cross-references (83, blind second rater, prompt `xref-audit-v1`)

Targets: {'neither': 46, 'same target': 29, 'second only': 5, 'different targets': 1, 'first only': 2}. Second rater's kinds: {'same-place': 14, 'too-vague': 14, 'reference': 47, 'not-a-reference': 8}.

| Item | Phrase | First proposal | Second rater | Second rater's reason |
|---|---|---|---|---|
| `1.1.3.3-p2-r3232` | in their place | — | 1.1.3.4 (reference) | The kinds of madness and dotage that come from different melancholy matter are treated in the next subsection, on the kinds of melancholy. |
| `1.2.3.2-p1-r2175` | formerly said | — | 1.2.1.3 (reference) | Witches' journeys and transformations put down to imagination and the Devil's illusions are discussed in the subsection on witches. |
| `1.3.1.1-p4-r1008` | in the following discourse | — | 1.3.1.2 (reference) | 'The following discourse' on troubled senses and imaginations is the next subsection, symptoms in the mind. |
| `1.3.1.1-p4-r989` | as shall be proved | — | 1.3.1.2 (reference) | The false perceptions of the senses are set out next, in the symptoms of the mind. |
| `2.5.1.3-p7-r61` | before mentioned | 2.4.1.5 | 2.4.1.3 (reference) | Borage and borage wine were discussed among the herb alteratives. |
| `3.2.5.1-p11-r463` | formerly handled | 2.4.1.1 | — (reference) | This points to the cures of melancholy by physic in Partition 2, which run across 2.4 and 2.5, so no single unit can be named. |
| `3.2.5.1-p11-r480` | in the precedent partition | 2.4.1.1 | — (reference) | The 'precedent partition' is Partition 2, whose physic cures span several members (2.4, 2.5), so no single unit id applies. |
| `3.4.1.1-p2-r2516` | in its place | — | 3.4.1.3 (reference) | The furies of Sibyls, Enthusiasts, Pseudoprophets, Heretics and Schismatics are treated in the Symptoms of Religious Melancholy, whose title lists Heretics, Schismatics, Prophets and Enthusiasts. |

## Source conflicts (17, prompt `source-audit-v1`)

Verdicts: {'match-is-source': 12, 'claim-quoted-in-match': 5}.

| Passage | Verdict | Source named | Confidence | Reason |
|---|---|---|---|---|
| `1.2.4.6-f7` | match-is-source | Seneca the Younger, Epistulae morales 115.14 | medium | Seneca gives this Latin line in a series of sayings he says come from the Greek tragedians. The Latin wording reaches Burton through Seneca, and the line itself has no secure source in Euripides, so Burton's sidenote is at best loose. |
| `1.3.3.1-f9` | match-is-source | Seneca the Younger, De tranquillitate animi 17.10 | high | The Latin wording is Seneca's. He credits the idea to Aristotle, which reflects Problemata 30.1, and Burton's 'Aristotle' follows Seneca. |
| `1.4.1.1-f131` | match-is-source | Quintilian, Institutio oratoria 6.pr.14 | high | 'Fabius' is Marcus Fabius Quintilianus, so the claim and the match are the same author. The words appear exactly in the preface to Book 6, not Book 7 as Burton has it. |
| `1.4.1.1-f68` | match-is-source | Martial, Epigrammata 10.47.13 | high | This is the closing line of Martial's epigram on the happy life. Burton's 'Hor.' is a mistake. |
| `2.2.5.1-f18` | match-is-source | Petronius, Fragment on dreams ('Somnia quae mentes ludunt volitantibus umbris') | high | The line closes Petronius's poem on dreams; Claudian's preface to VI Cons. Hon. treats the same theme but does not contain this verse. The corpus has the variant 'lustrat' for 'latrat'. |
| `2.3.3.1-f165` | claim-quoted-in-match | Ennius, Annales (Pyrrhus's speech) | high | Cicero, De officiis 1.38, quotes Ennius's verses giving Pyrrhus's reply about the prisoners. |
| `2.3.3.1-f35` | claim-quoted-in-match | Horace, Satires 1.2.114-115 | high | These are Horace's lines, and Seneca, Epistulae 119.13, quotes them. |
| `2.3.7.1-f24` | match-is-source | Ovid, Ars Amatoria 2.179-180 | high | The couplet is Ovid's; Camerarius's emblem book, which Burton cites, merely reuses it as a motto. |
| `3.2.1.1-f15` | claim-quoted-in-match | Caecilius Statius, Fragment (comedy), quoted in Cicero, Tusculan Disputations 4.68 | high | Cicero explicitly introduces the lines as Caecilius's verses on the god Love; Burton took them via Selden. |
| `3.2.2.2-f193` | match-is-source | Quintus Curtius Rufus, Historiae Alexandri Magni 6.5.29 | high | The claim and the match are the same author. Burton slightly condenses the wording ('donare natura dignata est') and gives 'Lib. 5' where the passage is in Book 6. |
| `3.2.2.2-f196` | match-is-source | Ovid, Metamorphoses 6.515 | high | The Latin is Ovid's line on Tereus gazing at Philomela; Burton applies it loosely to Musaeus's Leander, but the words are not Musaeus's. |
| `3.2.2.4-f129` | match-is-source | Tibullus, Elegiae 1.5.60 | high | The line is in Tibullus 1.5. Burton's 'Catullus lib. 1 eleg. 5' confuses Catullus with Tibullus, though the book and elegy numbers are right. |
| `3.2.3.1-f106` | match-is-source | Ovid, Heroides 16.101 (Paris to Helen) | medium | The line is Ovid's ('te vigilans oculis, animo te nocte videbam'), adapted by Burton with 'requiro'; it is not a known Petronian verse. |
| `3.2.3.1-f186` | claim-quoted-in-match | Quintus Lutatius Catulus, epigram on Roscius | high | Cicero, De natura deorum 1.79, quotes this epigram by Catulus on the actor Roscius. |
| `3.3.1.2-f105` | match-is-source | Propertius, Elegies 2.33.34 | high | The pentameter belongs to Propertius's elegy against wine; Burton's attribution to Tibullus is a misattribution. |
| `djr-f728` | claim-quoted-in-match | Virgil, Georgics 1.53 | high | The line is Virgil, Georgics 1.53 ('et quid quaeque ferat regio et quid quaeque recuset'). Columella builds it into his own prose in Res Rustica, Book 5. |
| `djr-f826` | match-is-source | Seneca the Younger, De tranquillitate animi 17.10 | medium | The Latin sentence is Seneca's own; he credits the idea to Aristotle (cf. Problemata 30.1), who wrote nothing like it in Greek. Burton's 'that of Aristotle' passes on Seneca's attribution. |

