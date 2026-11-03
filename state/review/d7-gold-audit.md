# D7: second rater on the language-ID gold labels

Second rater: gold-audit-v1, blind (text and context only; no first labels, detector output or stratum). Same model family as the first rater, so agreement is not independent proof; the disagreements are the ones worth your eye.

**Agreement 1092/1127 (96.9 %).** By round: tuning 648/677, h1 148/150, h2 296/300

| first → second | n |
|---|---|
| name → en | 15 |
| citation → name | 12 |
| mixed → la | 3 |
| name → citation | 2 |
| en → name | 1 |
| citation → en | 1 |
| en → mixed | 1 |

## Disagreements

| item | unit | text | first | second | second rater's reason |
|---|---|---|---|---|---|
| tuning:m1-016 | 1.1.1.2 | Smallpox | name | en | English name of a disease |
| tuning:m1-041 | 1.1.1.2 | Acute | name | en | English word used as a classification label |
| tuning:m1-042 | 1.1.1.2 | Chronic | name | en | English word used as a classification label |
| tuning:m1-043 | 1.1.1.2 | First | name | en | English word |
| tuning:m1-044 | 1.1.1.2 | Secondary | name | en | English word |
| tuning:m1-047 | 1.1.1.2 | Errant | name | en | English word |
| tuning:m1-048 | 1.1.1.2 | Fixed | name | en | English word |
| tuning:m1-049 | 1.1.1.2 | Simple | name | en | English word |
| tuning:m1-050 | 1.1.1.2 | Compound | name | en | English word |
| tuning:m1-051 | 1.1.1.2 | Connexed | name | en | Early Modern English word |
| tuning:m1-052 | 1.1.1.2 | Consequent | name | en | English word |
| tuning:m1-054 | 1.1.1.2 | Habit | name | en | English word |
| tuning:m1-055 | 1.1.1.2 | Disposition | name | en | English word |
| tuning:italic-030 | 1.2.1.4 | Sun | en | name | Heavenly body in an astrological context |
| tuning:italic-042 | 2.5.1.5 | Tubing | name | citation | Abbreviated place of publication (Tübingen) in a reference |
| tuning:italic-139 | 2.5.1.5 | China | name | en | China root, a drug name borrowed into English |
| tuning:italic-174 | 1.2.3.12 | Aulularia | name | citation | Title of Plautus' play cited as source |
| tuning:italic-259 | 2.5.1.5 | Alkermes | name | en | A cordial whose name was borrowed into English |
| tuning:roman-before-bracket-062 | 1.2.1.2 | 211, quos inquit arcere si volunt viatores, clara voce Deum appellare aut pronam facie ter… | mixed | la | Latin quotation from Bodin after a folio number |
| tuning:roman-before-bracket-083 | 3.4.2.6 | 15. 24. Si cadentem intuetur, clementiae manum protendit | mixed | la | Verse numbers from a citation, then a Latin sentence. |
| tuning:sidenote-012 | 3.2.3.1 | Ovid | citation | name | Author's name given in full as a reference |
| tuning:sidenote-020 | 3.2.3.1 | Gaulmino | citation | name | Name of the translator Gaulmin |
| tuning:sidenote-025 | 2.3.1.1 | Sallust | citation | name | Author's name on its own as a reference |
| tuning:sidenote-030 | 2.3.7.1 | Plutarch | citation | name | Author's name on its own as a reference |
| tuning:sidenote-035 | 3.4.1.3 | Crassi | citation | name | Personal name Crassus, in the genitive |
| tuning:sidenote-053 | 3.2.2.4 | Ovid | citation | name | An author's name given in full as a reference. |
| tuning:sidenote-076 | 2.3.3.1 | Ovid | citation | name | An author's name given in full as a reference. |
| tuning:sidenote-091 | 3.2.3.1 | Lucian | citation | name | Author's full name standing as a reference |
| tuning:sidenote-094 | djr | Eobanus Hessus | citation | name | Author's full name |
| h1:h-sidenote-007 | 3.4.2.2 | Zanchius | citation | name | Bare author's name used as a reference |
| h1:h-sidenote-016 | 3.3.4.2 | Arnisaeus | citation | name | Bare author's name used as a reference |
| h2:h2-italic-015 | 3.2.5.5 | comment | citation | en | English word set in italics |
| h2:h2-roman-before-bracket-003 | 3.4.1.1 | 1, atque etiam post saevit de futuro | mixed | la | Latin phrase after a locator number |
| h2:h2-sidenote-015 | 1.2.3.15 | Crassi | citation | name | Crassus, a personal name, in the title Vit. Crassi |
| h2:h2-english-014 | 2.3.2.1 | & Cabinet du Roy, their own writer distinctly of the rest; | en | mixed | English sentence containing a French title. |
