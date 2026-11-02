# Top 100 authors by citation count: owner review (M6)

Generated 2026-11-02 by `uv run burton authors --review`. Counts are from the rules-only
citation layer (`data/layers/citations/`, method `rules/abbrev-v1`). Everything below is a draft until you
check it: the identification of Burton's form, the Wikidata match, and the model-drafted identification
and "why Burton cites them" (labelled `machine-draft`). Wikidata shows the QID when exactly one
candidate matched by rule, else `ambiguous`/`none`, or `—` where the lookup has not run yet.

To record your check, edit `data/authors/<id>.yaml`: set `review.state` to `agreed` or `corrected`
(with `review.note`), and `status: checked`. Corrections to a form go in `data/abbreviations.yaml`.

| # | Author | id | Burton's forms | Citations | Sidenotes | Units | Wikidata | Draft | Doubt stated |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Horace | `horace` | Hor, Horat, Horatius, Horace | 188 | 184 | 58 | Q6197 | high | — |
| 2 | Ovid | `ovid` | Ovid, Ovidius, Naso | 125 | 124 | 46 | Q7198 | high | — |
| 3 | Seneca the Younger | `seneca-younger` | Seneca (ambiguous), Senec (ambiguous), Sen (ambiguous) | 107 | 103 | 42 | Q2054 | medium | The input gives no Burton name forms, and a bare citation such as 'Senec. lib. 1 cap. 18.' could in principle refer to Seneca the Elder, whom early modern writers sometimes confused with his son. |
| 4 | Virgil | `virgil` | Virg, Virgil, Virgilius, Maro | 99 | 81 | 38 | Q1398 | high | — |
| 5 | Terence | `terence` | Ter, Terent, Terence, Terentius | 85 | 61 | 26 | Q172048 | high | Most forms clearly mean the playwright, but the example 'Ter. sanctae.' does not fit Terence and may be a different author or a garbled reference. |
| 6 | Plutarch | `plutarch` | Plutarch, Plut, Plutarchus | 77 | 75 | 41 | Q41523 | high | Some works cited under his name, such as On the Opinions of the Philosophers (De placitis philosophorum) and On the Education of Children, are now thought to be by other writers. |
| 7 | Juvenal | `juvenal` | Juven, Juv, Juvenal, Juvenalis | 68 | 68 | 35 | ambiguous | high | — |
| 8 | Plautus | `plautus` | Plautus, Plaut | 57 | 52 | 27 | none | high | — |
| 9 | Girolamo Cardano | `cardano` | Cardan, Cardanus, Card | 54 | 54 | 25 | Q184530 | high | — |
| 10 | Lucian | `lucian` | Lucian, Lucianus | 53 | 51 | 22 | Q177847 | high | Some pieces Burton cites under Lucian's name, possibly including the Podagra pieces, have been doubted as his work. |
| 11 | Augustine of Hippo | `augustine` | Austin, Aug, August, Augustinus, Augustine | 52 | 51 | 32 | Q8018 | high | Some works cited under his name were not written by him. De ecclesiasticis dogmatibus, for example, is now credited to Gennadius of Marseilles. |
| 12 | Cicero | `cicero` | Tully, Tullius, Tul, Cic, Cicero | 47 | 45 | 25 | Q1541 | high | — |
| 13 | Justus Lipsius | `lipsius` | Lipsius, Lips | 41 | 41 | 27 | Q315871 | high | — |
| 14 | Petronius | `petronius` | Petronius, Petron | 38 | 37 | 17 | ambiguous | medium | The 'Catalecta' poems were attributed to Petronius in Renaissance collections, but their authorship is uncertain. The example 'Fol. 5.' cannot be checked from the information given. |
| 15 | Martial | `martial` | Mart, Martial, Martialis | 35 | 35 | 21 | Q2098 | medium | Not all 'Mart.' citations belong to the poet. 'Mart. in Apol. pro Christianis' points to Justin Martyr's Apology, and 'Mart. in Sam.' probably points to Peter Martyr Vermigli's commentary on Samuel. |
| 16 | Apuleius | `apuleius` | Apuleius, Apul | 34 | 34 | 18 | Q170512 | high | — |
| 17 | Aristotle | `aristotle` | Arist, Aristot, Aristotle, Aristoteles | 34 | 34 | 16 | none | high | — |
| 18 | Plato | `plato` | Plato, Platonis | 34 | 33 | 16 | Q859 | high | — |
| 19 | André du Laurens (Laurentius) | `laurentius` | Laurentius | 33 | 33 | 26 | Q426294 | high | The bare form 'Laurentius' could occasionally refer to another writer of that name, although all the examples given fit du Laurens. |
| 20 | John Chrysostom | `chrysostom` | Chrys, Chrysost, Chrysostom, Chrysostomus | 31 | 31 | 17 | Q43706 | high | — |
| 21 | Levinus Lemnius | `lemnius` | Lemnius, Lemn | 29 | 29 | 21 | none | high | — |
| 22 | Rhazes | `rhazes` | Rhasis, Rhazes, Rasis | 29 | 27 | 24 | Q169234 | high | — |
| 23 | Galen | `galen` | Galen, Galenus, Galeni, Gal | 28 | 28 | 22 | Q8778 | high | — |
| 24 | Desiderius Erasmus | `erasmus` | Erasmus, Erasm, Eras | 27 | 26 | 14 | Q43499 | high | — |
| 25 | Pliny the Elder | `pliny-elder` | Plin (ambiguous), Plinius (ambiguous), Pliny (ambiguous) | 27 | 26 | 16 | Q82778 | medium | The bare 'Plin.' could sometimes mean Pliny the Younger, whose letters Burton also uses. 'lib. 57' cannot refer to the 37-book Natural History and is probably a misprint. |
| 26 | Aeneas Silvius Piccolomini (Pius II) | `aeneas-silvius` | Aeneas Silvius, Aeneas Silv, Aeneas Sylvius, Aen Silvius | 24 | 24 | 14 | Q101437 | high | — |
| 27 | Catullus | `catullus` | Catullus, Catul, Catull | 24 | 24 | 14 | none | high | — |
| 28 | Aristaenetus | `aristaenetus` | Aristaenetus | 23 | 23 | 8 | ambiguous | high | — |
| 29 | Cyprian | `cyprian` | Cyprian, Cyprianus, Cyp, Cypr | 23 | 22 | 11 | ambiguous | high | Some works printed under Cyprian's name in Burton's time are now thought to be spurious, so the reference to a prologue to sermons in tome 2 may be to a work wrongly attributed to him. |
| 30 | Homer | `homer` | Homer, Homerus | 23 | 20 | 17 | Q6691 | high | — |
| 31 | Nicolas Le Pois (Piso) | `piso` | Piso | 23 | 23 | 19 | none | medium | The bare form 'Piso' could in a few sidenotes refer to one of the Roman Pisos. The medical company it keeps in the examples points to Le Pois. |
| 32 | Franz Hildesheim | `hildesheim` | Hildesheim, Hildesheimius | 21 | 21 | 18 | Q1447238 | high | — |
| 33 | Hippocrates | `hippocrates` | Hippocrates, Hippocr, Hippoc, Hipp | 21 | 20 | 16 | none | high | — |
| 34 | Johannes Crato von Krafftheim | `crato` | Crato | 20 | 20 | 14 | Q87688 | high | — |
| 35 | Daniel Heinsius | `heinsius` | Heinsius | 20 | 20 | 13 | none | medium | The work Burton cites as 'Austriacus' and the letter 'to Primerius' have not been checked against Heinsius's bibliography, so the editor should confirm them. |
| 36 | Livy | `livy` | Livy, Livius, Liv | 20 | 20 | 14 | none | high | — |
| 37 | Philipp Melanchthon | `melanchthon` | Melancthon, Melanchthon, Melanct | 20 | 20 | 17 | ambiguous | high | — |
| 38 | Heinrich Cornelius Agrippa | `agrippa` | Agrippa, Corn Agrippa | 18 | 18 | 10 | Q76568 | high | — |
| 39 | Giovanni Botero (Boterus) | `boterus` | Boterus, Botero | 18 | 18 | 8 | Q963339 | high | — |
| 40 | Paolo Giovio (Jovius) | `jovius` | Jovius, Paulus Jovius | 18 | 18 | 15 | ambiguous | high | — |
| 41 | Matteo Ricci (Riccius) | `ricci` | Riccius, Matth Riccius | 18 | 17 | 11 | Q233340 | high | The Expeditio was compiled and translated by Trigault, so some editors index it under Trigault rather than Ricci. |
| 42 | Donato Antonio Altomari (Altomarus) | `altomari` | Altomarus, Altomar | 17 | 16 | 13 | none | medium | — |
| 43 | Strozzi Cicogna | `cicogna` | Cicogna, Strozzius Cicogna | 17 | 17 | 6 | Q55226727 | medium | — |
| 44 | Jerome | `jerome` | Hierom, Hieron, Hieronymus, Jerome | 17 | 14 | 13 | Q44248 | high | — |
| 45 | Filotheo Elião de Montalto (Montaltus) | `montalto` | Montaltus, Aelianus Montaltus | 17 | 17 | 14 | none | high | — |
| 46 | George Buchanan | `buchanan` | Buchanan, Buchananus | 16 | 16 | 12 | Q715169 | high | — |
| 47 | Quintus Curtius Rufus | `curtius` | Curtius, Q Curtius | 16 | 16 | 11 | ambiguous | high | — |
| 48 | Lucan | `lucan` | Lucan, Lucanus | 16 | 16 | 11 | ambiguous | high | — |
| 49 | Baptista Mantuanus | `mantuan` | Mantuan, Mantuanus, Mant | 16 | 16 | 9 | Q810973 | high | — |
| 50 | Persius | `persius` | Persius, Pers | 16 | 16 | 13 | ambiguous | high | — |
| 51 | Antonio Guainerio (Guianerius) | `guainerio` | Guainerius, Guainer, Guianerius | 15 | 15 | 12 | Q110217312 | medium | One example ('lib. 2 cap. 8. vit. M. Aurelii') points to a life of Marcus Aurelius, which suggests Antonio de Guevara rather than Guainerio and may come from a confusion of names in the source or the data. |
| 52 | Ercole Sassonia (Hercules de Saxonia) | `hercules-saxonia` | Hercules de Saxonia, Herc de Saxonia | 15 | 15 | 10 | — | high | — |
| 53 | Propertius | `propertius` | Propertius, Propert | 15 | 14 | 10 | — | high | — |
| 54 | Suetonius | `suetonius` | Suetonius, Sueton, Suet | 15 | 15 | 12 | — | high | — |
| 55 | Athenaeus | `athenaeus` | Athenaeus | 14 | 14 | 11 | — | high | — |
| 56 | Caspar Barth (Barthius) | `barth` | Barthius, Barthio | 14 | 14 | 10 | — | high | — |
| 57 | Geoffrey Chaucer | `chaucer` | Chaucer | 14 | 14 | 11 | — | high | — |
| 58 | Euripides | `euripides` | Euripides, Eurip | 14 | 14 | 11 | — | high | — |
| 59 | Johannes Heurnius | `heurnius` | Heurnius | 14 | 13 | 10 | — | high | — |
| 60 | Leo Africanus | `leo-africanus` | Leo Afer, Leo Africanus | 14 | 14 | 10 | — | high | — |
| 61 | Sebastian Münster | `munster` | Munster, Munsterus | 14 | 14 | 8 | — | high | — |
| 62 | Valerius Maximus | `valerius-maximus` | Valerius, Valer, Val Max, Valerius Maximus | 14 | 14 | 10 | — | high | — |
| 63 | Ludovico Ariosto | `ariosto` | Ariosto, Ariostus | 13 | 13 | 5 | — | high | — |
| 64 | William Camden | `camden` | Camden, Camdenus | 13 | 13 | 6 | — | high | — |
| 65 | Aulus Gellius | `gellius` | Gellius, Gell, A Gellius, Agellius | 13 | 13 | 11 | — | high | — |
| 66 | Lucretius | `lucretius` | Lucretius, Lucret | 13 | 13 | 10 | — | high | — |
| 67 | Girolamo Mercuriale | `mercuriale` | Mercurialis, Mercurial | 13 | 13 | 12 | — | high | — |
| 68 | Pausanias | `pausanias` | Pausanias | 13 | 12 | 11 | — | high | — |
| 69 | Felix Platter (Platerus) | `platter` | Platerus, Plater | 13 | 13 | 10 | — | high | — |
| 70 | Juan Luis Vives | `vives` | Vives, Lod Vives, Ludovicus Vives | 13 | 13 | 12 | — | high | — |
| 71 | Bernard of Clairvaux | `bernard-clairvaux` | Bernard, Bernardus, Bern | 12 | 12 | 11 | — | medium | Some works Burton cites under Bernard's name, such as the treatise 'de interiori domo', were attributed to him in the period but are thought not to be his. |
| 72 | Jean Fernel | `fernel` | Fernelius, Fernel | 12 | 12 | 12 | — | high | — |
| 73 | Girolamo Fracastoro (Fracastorius) | `fracastoro` | Fracastorius | 12 | 12 | 10 | — | high | — |
| 74 | Herodotus | `herodotus` | Herodotus, Herod (ambiguous) | 12 | 11 | 9 | — | high | — |
| 75 | Thomas More | `more` | Morus, Th Morus, Thomas Morus | 12 | 11 | 2 | — | high | — |
| 76 | Johann Schenck von Grafenberg (Schenkius) | `schenck` | Schenkius, Skenkius, Schenckius, Schenkium | 12 | 12 | 7 | — | medium | The citation 'observ. med. cen. 5 obser. 86' refers to 'centuries', which does not match the division of Schenck's Observationes into books, so this sidenote may point to another collection or be a slip; his son Johann Georg Schenck also published medical observations. |
| 77 | Girolamo Zanchi (Zanchius) | `zanchi` | Zanchius, Zanch | 12 | 12 | 7 | — | high | — |
| 78 | Achilles Tatius | `achilles-tatius` | Tatius, Achilles Tatius, Ach Tatius | 11 | 11 | 6 | — | high | — |
| 79 | Leonhart Fuchs (Fuchsius) | `fuchs` | Fuchsius, Fuchs, Fuch | 11 | 11 | 10 | — | high | — |
| 80 | Bernard de Gordon (Gordonius) | `gordon` | Gordonius, Gordon, Gord | 11 | 11 | 9 | — | high | — |
| 81 | John of Salisbury | `john-salisbury` | Sarisburiensis, Joh Sarisburiensis | 11 | 11 | 7 | — | high | — |
| 82 | John Leech (Leochaeus) | `leech-john` | Leochaeus, Joh Leochaeus | 11 | 11 | 6 | — | medium | — |
| 83 | Giovanni Antonio Magini (Maginus) | `maginus` | Maginus, Magin | 11 | 11 | 6 | — | high | — |
| 84 | Giovanni Battista da Monte (Montanus) | `montanus` | Montanus | 11 | 11 | 10 | — | high | — |
| 85 | Tibullus | `tibullus` | Tibullus, Tibul | 11 | 11 | 5 | — | high | Several of the poems Burton cites from books 3 and 4, including the Sulpicia poems, are now thought to be by other poets in the Tibullan collection, although Burton attributes them to Tibullus. |
| 86 | Aetius of Amida | `aetius` | Aetius | 10 | 9 | 7 | — | high | — |
| 87 | Ausonius | `ausonius` | Ausonius, Auson, Aus | 10 | 10 | 8 | — | high | — |
| 88 | Jean Bodin | `bodin` | Bodin, Bodine, Bodinus | 10 | 10 | 8 | — | high | — |
| 89 | Johann Boemus (Bohemus) | `boemus` | Bohemus, Boemus | 10 | 10 | 7 | — | high | — |
| 90 | Celio Calcagnini (Calcagninus) | `calcagnini` | Calcagninus | 10 | 10 | 7 | — | medium | — |
| 91 | Joannes de Laet | `laet` | Laet, Laetius | 10 | 10 | 8 | — | high | — |
| 92 | Abraham Ortelius | `ortelius` | Ortelius | 10 | 9 | 6 | — | high | — |
| 93 | George Sandys | `sandys` | Sandys | 10 | 10 | 8 | — | high | The citations that give only the bare name 'Sandys' could refer to his brother Sir Edwin Sandys, whose survey of religion in Europe Burton also knew, although the book-and-folio references fit George's 'Relation'. |
| 94 | Johann Weyer (Wierus) | `weyer` | Wierus, Wier | 10 | 9 | 4 | — | high | — |
| 95 | Aretaeus of Cappadocia | `aretaeus` | Aretaeus | 9 | 9 | 8 | — | high | — |
| 96 | Ogier Ghiselin de Busbecq (Busbequius) | `busbecq` | Busbequius | 9 | 9 | 8 | — | high | — |
| 97 | Baldassare Castiglione (Castilio) | `castiglione` | Castilio | 9 | 9 | 6 | — | high | — |
| 98 | David Chytraeus | `chytraeus` | Chytraeus | 9 | 9 | 6 | — | low | Every example cites the 'Deliciae Europae', which was compiled by Nathan Chytraeus, not David, so the person Burton means is probably Nathan. |
| 99 | Marsilio Ficino (Ficinus) | `ficino` | Ficinus, Ficin, Marsilius Ficinus, Mars Ficinus | 9 | 9 | 9 | — | high | — |
| 100 | Heliodorus of Emesa | `heliodorus` | Heliodorus, Heliodor | 9 | 9 | 6 | — | high | — |

## Examples of each author's citations

**1. Horace** (`horace`): Hor. (1.1.1.1-n33); Hor. lib. 3 Od. 6. (1.1.1.1-n47); Horat. (1.1.1.2-n5); Hor. Ser. 1 Sat. 3. (1.2.2.6-n10)
> Draft (claude-opus-5-5, authors-v1, 2026-11-02; high): Quintus Horatius Flaccus (65–8 BC) was a Roman poet from Venusia in southern Italy. His works are the Odes, the Satires (Sermones), the Epistles and the Ars Poetica. *Why cited:* Burton quotes him often, mostly from the Satires, Odes and Epistles, for moral comments on greed, discontent, folly and how to live calmly.

**2. Ovid** (`ovid`): Ovid de Trist. lib. 5 Eleg. 7. (1.1.1.1-n43); Ovid. (1.1.2.11-n8); Ovid. 4 Met. (1.1.2.9-n14); Ovid. met. 15. (1.1.2.9-n6)
> Draft (claude-opus-5-5, authors-v1, 2026-11-02; high): Publius Ovidius Naso (43 BC–AD 17 or 18) was a Roman poet from Sulmo. Augustus exiled him to Tomis on the Black Sea. His works include the Metamorphoses, the Fasti, the love poems (Amores, Ars Amatoria, Remedia Amoris) and the Tristia, written in exile. *Why cited:* Burton quotes his verses on love, change and grief. He uses the Metamorphoses for myths and the Tristia for the misery of exile.

**3. Seneca the Younger** (`seneca-younger`): Seneca (1.1.2.11-n9); Senec. lib. 1 cap. 18. (1.2.1.2-n36); Seneca. (1.2.2.2-n16); Seneca consol. ad Helviam. (1.2.2.2-n17)
> Draft (claude-opus-5-5, authors-v1, 2026-11-02; medium): Lucius Annaeus Seneca (c. 4 BC–AD 65) was a Roman Stoic philosopher and statesman from Corduba in Spain, and tutor to Nero. He wrote moral essays and consolations, including the Consolation to Helvia, the Letters to Lucilius and a set of tragedies. *Why cited:* Burton draws on him for Stoic advice and consolation against grief, fear and discontent. He also quotes the tragedies, such as Hercules Oetaeus, whose authorship is disputed.

**4. Virgil** (`virgil`): Virg. (1.1.2.11-n5); Virg. 8 ecl. (1.2.1.2-n46); Aen. 4. (1.2.1.2-n47); Aeneid. 4 (1.2.1.3-n23)
> Draft (claude-opus-5-5, authors-v1, 2026-11-02; high): Publius Vergilius Maro (70–19 BC) was a Roman poet born near Mantua. His works are the Eclogues, the Georgics and the Aeneid. *Why cited:* Burton quotes his verses often, especially Aeneid 4 on Dido's love and despair, as well as the Eclogues and Georgics.

**5. Terence** (`terence`): Ter. sanctae. (1.2.2.5-n16); Terence. (1.2.3.9-n6); Ter. (1.2.4.2-n6); Adel. 3. 4. (1.2.4.2-n6)
> Draft (claude-opus-5-5, authors-v1, 2026-11-02; high): Publius Terentius Afer (d. 159 BC) was a Roman comic playwright, said to have been born in Carthage and brought to Rome as a slave. Six of his comedies survive, including the Eunuchus and the Adelphoe. *Why cited:* Burton quotes lines from the comedies, especially the Eunuchus and Adelphoe, as proverbial wisdom on love, lovers' folly and everyday life.

**6. Plutarch** (`plutarch`): Plutarch. de placit. philos. (1.1.2.5-n10); Plutarch. in Grillo. (1.1.2.5-n9); De pract. Philos. 4. (1.1.2.6-n3); Plutarch. de defect. oraculum. (1.2.1.2-n21)
> Draft (claude-opus-5-5, authors-v1, 2026-11-02; high): Plutarch of Chaeronea (c. AD 46–after 119) was a Greek philosopher and biographer. He wrote the Parallel Lives and many essays collected as the Moralia, including On Isis and Osiris, On the Obsolescence of Oracles and Gryllus. *Why cited:* Burton uses the Moralia for moral and philosophical points, for opinions about the soul, spirits and oracles, and for stories and anecdotes.

**7. Juvenal** (`juvenal`): Juvenal. (1.2.2.2-n10); Juv. Sat. 1. (1.2.2.2-n5); Juv. Sat. 14. (1.2.3.12-n31); Juven. Sat. 1. (1.2.3.13-n13)
> Draft (claude-opus-5-5, authors-v1, 2026-11-02; high): Decimus Iunius Iuvenalis was a Roman satirist active in the late first and early second centuries AD. He wrote sixteen verse Satires. *Why cited:* Burton quotes the Satires, especially 1, 10 and 14, for attacks on vice, greed and the vanity of human wishes.

**8. Plautus** (`plautus`): Pseudolus, act. 3 scen. 2. (1.2.2.1-n17); Plautus (1.2.2.1-n18); ibid. (1.2.2.1-n18); Plautus. (1.2.2.2-n19)
> Draft (claude-opus-5-5, authors-v1, 2026-11-02; high): Titus Maccius Plautus (d. c. 184 BC) was a Roman comic playwright. About twenty of his comedies survive, including the Pseudolus, the Mostellaria and the Curculio. *Why cited:* Burton quotes lines from the comedies on lovers, misers, servants and human folly, often as proverbial sayings.

**9. Girolamo Cardano** (`cardano`): Lib. 2 contradic. cap. 11. (1.1.3.3-n10); De rerum var. lib. 16 cap. 93. (1.2.1.2-n103); Lib. 16 de rerum varietat. (1.2.1.2-n69); De rerum varietat. (1.2.2.1-n25)
> Draft (claude-opus-5-5, authors-v1, 2026-11-02; high): Girolamo Cardano (1501–1576) was an Italian physician, mathematician and astrologer from Pavia who worked in Milan. His works include De subtilitate, De rerum varietate, De consolatione and Contradicentium medicorum libri. *Why cited:* Burton cites him on medicine, natural wonders and the occult, mainly from De rerum varietate and the Contradicentia. He also uses De consolatione for comfort in misfortune.

**10. Lucian** (`lucian`): Lucian. Podag. (1.2.3.10-n4); Lucian. (1.4.1.1-n25); Necyomantia. Tom. 2. (2.2.6.4-n38); Tom. 1 Tract. de luctu. (2.3.5.1-n50)
> Draft (claude-opus-5-5, authors-v1, 2026-11-02; high): Lucian of Samosata (c. AD 120–after 180) was a Greek satirist and rhetorician. He wrote many comic dialogues and essays, including Timon, Toxaris, Menippus or Necyomantia, On Mourning and the mock-tragedy Podagra (on gout). *Why cited:* Burton uses him for satire on human folly, wealth, mourning and the vanity of life, and enjoys his comic dialogues.

**11. Augustine of Hippo** (`augustine`): August. in psal. 85. (1.1.1.5-n1); De eccles. dog. cap. 16. (1.1.2.9-n13); Austin de vit. Beat. (1.2.1.2-n104); Lib. 3 de Trinit. cap. 1. (1.2.1.2-n2)
> Draft (claude-opus-5-5, authors-v1, 2026-11-02; high): Augustine (354–430) was a Church Father and bishop of Hippo in North Africa. His works include the Confessions, The City of God, On the Trinity, The Literal Meaning of Genesis, De beata vita and the Expositions on the Psalms. *Why cited:* Burton cites him as a theological authority on the soul, spirits and divine matters, and on the happy life and the comfort of religion.

**12. Cicero** (`cicero`): Offic. 3. (1.2.2.6-n24); Offic. (1.2.3.10-n49); Tullius. (1.2.3.14-n21); Tul. som. Scip. (1.2.3.14-n35)
> Draft (claude-opus-5-5, authors-v1, 2026-11-02; high): Marcus Tullius Cicero (106–43 BC) was a Roman statesman, orator and philosopher. His philosophical works include De officiis, the Tusculan Disputations and the Dream of Scipio, which closes his De re publica. *Why cited:* Burton, who calls him 'Tully', draws on his moral philosophy. He uses the Tusculan Disputations on grief and disturbances of the mind, De officiis on duty and the Dream of Scipio on the soul and the heavens.

**13. Justus Lipsius** (`lipsius`): Lipsius cent. 3 ep. 45. (1.1.1.5-n6); Lips. Cent. 1 epist. 50. (1.1.2.5-n9); Lips. (1.2.1.2-n102); Lipsius Physiol. (1.2.1.2-n91)
> Draft (claude-opus-5-5, authors-v1, 2026-11-02; high): Justus Lipsius (1547–1606) was a Flemish humanist and classical scholar who revived Stoic philosophy. His works include De constantia, the Physiologia Stoicorum and several published centuries of letters. *Why cited:* Burton cites his letters and his Physiologia Stoicorum for learned opinions, anecdotes and Stoic ideas about nature and fortune.

**14. Petronius** (`petronius`): Petron. (1.2.3.10-n39); Petronius. (1.2.3.15-n20); Petronius Arbiter. (1.2.3.15-n41); Petronius Catalec. (2.3.3.1-n100)
> Draft (claude-opus-5-5, authors-v1, 2026-11-02; medium): Petronius Arbiter was the Roman author of the Satyricon, a comic novel in prose and verse. He is traditionally identified with the courtier of Nero who died in AD 66. *Why cited:* Burton quotes the Satyricon and short poems from the 'Catalecta' attributed to Petronius, mostly on love, lust and luxury.

**15. Martial** (`martial`): Mart. (1.2.1.2-n38); Mart. in Apol. pro Christianis. (1.2.1.2-n55); Mart. in Sam. (1.2.1.2-n88); Mart. lib. 5. 52. (1.2.3.14-n32)
> Draft (claude-opus-5-5, authors-v1, 2026-11-02; medium): Marcus Valerius Martialis (c. AD 40–c. 104) was a Latin poet from Bilbilis in Spain. He wrote twelve books of Epigrams and some smaller collections. *Why cited:* Burton quotes his epigrams for witty, satirical comments on vice, love and everyday life in Rome.

**16. Apuleius** (`apuleius`): Apuleius 4 florid. (1.1.1.5-n10); De Deo Socratis. (1.2.1.2-n32); Apuleius: (1.2.1.2-n8); Lib. 2. (1.2.4.4-n9)
> Draft (claude-opus-5-5, authors-v1, 2026-11-02; high): Apuleius (c. 124–after 170 CE) was a Latin writer and Platonist philosopher from Madauros in North Africa. He wrote the Metamorphoses (the Golden Ass), the Florida (a collection of extracts from his speeches), the treatise De Deo Socratis on daemons, and the Apologia. *Why cited:* Burton uses De Deo Socratis as an authority on the nature of spirits and daemons. He draws on the Metamorphoses (the 'Milesian' tales) and the Florida for stories and sayings.

**17. Aristotle** (`aristotle`): cap. 1. (1.1.2.5-n1); Aristot. (1.1.2.5-n6); Arist. in physiognomia. (1.1.3.2-n16); Arist. lib. 3 polit. cap. ult. Keckerm. (1.1.3.4-n16)
> Draft (claude-opus-5-5, authors-v1, 2026-11-02; high): Aristotle (384–322 BCE), from Stagira, was a Greek philosopher and a pupil of Plato. His works relevant to Burton include De anima and the Politics. The Problemata and the Physiognomonica were attributed to him in Burton's time, but modern scholars regard them as works of his school. *Why cited:* Burton cites him on the soul and its faculties, on physiognomy and on politics. He also cites the Problemata, which includes the well-known discussion of why exceptional men are melancholic.

**18. Plato** (`plato`): Plato. (1.2.1.2-n32); Plato lib. 13 de legibus. (1.2.4.4-n4); Plato 9 de legibus (1.4.1.1-n57); De Legibus. (2.2.1.1-n17)
> Draft (claude-opus-5-5, authors-v1, 2026-11-02; high): Plato (c. 428–348/347 BCE) was an Athenian philosopher and a pupil of Socrates. His dialogues include the Laws, the Republic and the Charmides. *Why cited:* Burton cites the Laws on government, education and conduct, and the Charmides, where Socrates argues that the body cannot be cured without the soul. In 'lib. 13 de legibus' Burton apparently refers to the Epinomis, which was traditionally treated as a thirteenth book of the Laws.

**19. André du Laurens (Laurentius)** (`laurentius`): Cap. 2 de Melanchol. (1.1.1.3-n3); Cap. 4 de mel. (1.1.1.4-n1); Anat. lib. 1 cap. 18. (1.1.2.2-n1); Laurentius cap. 20 lib. 1 Anat. (1.1.2.3-n1)
> Draft (claude-opus-5-5, authors-v1, 2026-11-02; high): André du Laurens (1558–1609) was a French physician who taught medicine at Montpellier and was later chief physician to Henri IV. He wrote a discourse on diseases of the sight, melancholy, catarrhs and old age, which circulated widely in Latin and English translations, and the Historia anatomica humani corporis. *Why cited:* He is one of Burton's main medical authorities on melancholy: its causes, symptoms and kinds. Burton also cites his anatomy on the parts and faculties of the body.

**20. John Chrysostom** (`chrysostom`): Chrys. 23 Gen. (1.1.1.1-n10); Hom. 5 ad populum Antioch. (1.1.1.1-n15); Chrys. hom. 53 in 19 Genes. Greg. in 1 cap. Job. (1.2.1.2-n88); Hom. 10. (1.2.3.10-n12)
> Draft (claude-opus-5-5, authors-v1, 2026-11-02; high): John Chrysostom (c. 349–407) was a Greek Church Father and preacher at Antioch who later became archbishop of Constantinople. He is known for his many homilies, including those on Genesis, the Homilies on the Statues to the people of Antioch, and his homilies on Paul's Epistle to the Romans. *Why cited:* Burton quotes his homilies on moral and spiritual matters, such as sin, the vanity of the world, and patience in affliction. These passages are often grouped with other patristic authorities.

**21. Levinus Lemnius** (`lemnius`): Lemn. lib. 2 cap. 29 de occult. nat. mir. (1.1.1.1-n28); Lemnius (1.1.2.9-n2); De occult. nat. mir. (1.2.1.6-n16); Lib. 2 cap. 8 de occult. nat. mir. (1.2.1.6-n18)
> Draft (claude-opus-5-5, authors-v1, 2026-11-02; high): Levinus Lemnius (1505–1568) was a Dutch physician from Zierikzee in Zeeland. His best-known work is De occultis naturae miraculis (On the Hidden Wonders of Nature). He also wrote on bodily constitution and the complexions. *Why cited:* Burton draws often on De occultis naturae miraculis, using it on the effects of the passions, imagination, diet and humours on body and mind.

**22. Rhazes** (`rhazes`): Lib. 1 cont. Tract. 9. (1.1.3.2-n21); Rhasis, cap. 15, cap. 16 in 9 (1.1.3.3-n5); Rhasis. (1.1.3.3-n5); Rhasis ad Almansor cap. 16. (1.2.5.2-n1)
> Draft (claude-opus-5-5, authors-v1, 2026-11-02; high): Abu Bakr Muhammad ibn Zakariya al-Razi (died c. 925), known in Latin as Rhazes, was a Persian physician and philosopher. His medical works were known in Latin as the Continens (al-Hawi) and the Liber ad Almansorem. *Why cited:* Burton cites him as one of the Arabic medical authorities on melancholy, its causes and its cure, mainly from the Continens and the book addressed to Almansor.

**23. Galen** (`galen`): De usu partium. (1.1.2.1-n3); Galen and others. (1.1.2.4-n2); Galen lib. 1 de san. tuend. (1.2.2.1-n37); Lib. de bonitate aquae. (1.2.2.1-n38)
> Draft (claude-opus-5-5, authors-v1, 2026-11-02; high): Galen of Pergamum (129–c. 216 CE) was a Greek physician who practised in Rome. His works became the basis of learned medicine. Those cited by Burton include De usu partium, De sanitate tuenda, De locis affectis and the treatise on the thinning diet. *Why cited:* Burton cites him as the chief classical medical authority on anatomy, the preservation of health, diet, and the seat and causes of melancholy.

**24. Desiderius Erasmus** (`erasmus`): Erasm. (1.1.3.2-n22); Fol. 129 mor. (1.2.1.6-n23); Erasm. Adag. chil. 3 cen. 7 pro. 72. (1.2.3.12-n23); Erasm. in Proverb. (1.2.3.13-n29)
> Draft (claude-opus-5-5, authors-v1, 2026-11-02; high): Desiderius Erasmus (c. 1466–1536), of Rotterdam, was a humanist scholar and theologian. His works include the Adagia, a large annotated collection of proverbs, the Moriae encomium (Praise of Folly), and an extensive correspondence. *Why cited:* Burton draws on the Adagia for proverbs and their explanations, and on the Praise of Folly for satire on human folly. He also cites Erasmus's letters.

**25. Pliny the Elder** (`pliny-elder`): Plinius. (1.2.3.10-n58); Plin. (1.2.3.12-n27); Plinius (2.1.1.1-n9); Plin. lib. 36. 15. (2.2.1.1-n21)
> Draft (claude-opus-5-5, authors-v1, 2026-11-02; medium): Pliny the Elder (23/24–79 CE) was a Roman writer, naturalist and official. He died during the eruption of Vesuvius. His Naturalis historia, in 37 books, is an encyclopaedia of the natural world, medicine and the arts. *Why cited:* Burton uses the Naturalis historia as a source of facts and marvels about nature, human beings, remedies and curious anecdotes.

**26. Aeneas Silvius Piccolomini (Pius II)** (`aeneas-silvius`): Aeneas Silvius de miser. curial. (1.2.2.2-n18); De miser. curial. (2.3.2.1-n35); Aeneas Silvius. (2.3.2.1-n36); Aeneas Silvius lib. 2 cap. 29. (2.3.2.1-n50)
> Draft (claude-opus-5-5, authors-v1, 2026-11-02; high): Enea Silvio Piccolomini (1405–1464) was an Italian humanist and diplomat who became Pope Pius II in 1458. His writings include De miseriis curialium (On the Miseries of Courtiers) and the love story of Euryalus and Lucretia. *Why cited:* Burton cites De miseriis curialium on the hardships and servility of court life. He uses other writings by Aeneas Silvius for stories and observations, especially on love.

**27. Catullus** (`catullus`): Catullus. (1.2.3.15-n87); Catullus ad Lesbiam. (3.2.2.1-n20); Catul. (3.2.2.4-n101); Catullus ad Lesbiam: da mihi basia mille (3.2.2.4-n41)
> Draft (claude-opus-5-5, authors-v1, 2026-11-02; high): Gaius Valerius Catullus (c. 84–c. 54 BCE) was a Roman lyric poet from Verona. He is best known for his poems to his beloved 'Lesbia'. *Why cited:* Burton quotes him for verses on love, especially the poem to Lesbia asking for a thousand kisses (poem 5, which Burton cites by the book-and-elegy numbering of older editions).

**28. Aristaenetus** (`aristaenetus`): Epist. 27. (3.2.2.2-n109); Aristaenetus epist. 10. (3.2.2.2-n65); Aristaenetus, ep. 17. (3.2.2.2-n88); Epist. 7 Lib. 2. (3.2.2.3-n26)
> Draft (claude-opus-5-5, authors-v1, 2026-11-02; high): Aristaenetus was a Greek writer of fictional love letters, probably of the late fifth or early sixth century CE. His letters survive in two books. *Why cited:* Burton quotes the love letters in his treatment of love melancholy, for scenes and descriptions of lovers, beauty and courtship.

**29. Cyprian** (`cyprian`): Cypr. (1.1.1.1-n18); Cyprianus in Epist. (1.2.1.2-n10); Cypr. prolog. ad ser. To. 2. (1.2.3.11-n12); Ep. 2 lib. 2. (1.2.3.12-n16)
> Draft (claude-opus-5-5, authors-v1, 2026-11-02; high): Cyprian (Thascius Caecilius Cyprianus, c. 200–258) was bishop of Carthage and died a martyr. He was a Latin Church Father whose works include the letter Ad Donatum, many other letters, and moral and pastoral treatises. *Why cited:* Burton quotes him on the miseries and corruption of the world, notably from Ad Donatum, and uses his letters on moral and spiritual matters.

**30. Homer** (`homer`): Homer. (1.1.1.1-n53); Iliad. (1.1.1.1-n53); Homerus (1.2.1.2-n31); Odyss. 17. (1.2.4.6-n71)
> Draft (claude-opus-5-5, authors-v1, 2026-11-02; high): Homer is the name traditionally given to the Greek epic poet of the Iliad and the Odyssey, probably composed in the eighth or seventh century BCE. *Why cited:* Burton quotes the Iliad and Odyssey for verses and examples. The references to Iliad 6 and Odyssey 4 (δ) probably point to Bellerophon's solitary wandering and to the grief-easing drug nepenthe, both themes Burton treats.

**31. Nicolas Le Pois (Piso)** (`piso`): Piso. (1.1.3.2-n18); Piso, (1.2.2.6-n20); Piso. Herc. de Saxon. (1.4.1.1-n5); Piso. Bruele. (2.5.3.2-n2)
> Draft (claude-opus-5-5, authors-v1, 2026-11-02; medium): Nicolas Le Pois (Nicolaus Piso, c.1527–1587) was a French physician of Nancy in Lorraine. He wrote a general handbook on recognising and treating internal diseases, De cognoscendis et curandis praecipue internis humani corporis morbis (1580). *Why cited:* Burton cites him as a medical authority on the causes, symptoms and cure of melancholy, often in lists of physicians with others such as Hercules de Saxonia and Bruele.

**32. Franz Hildesheim** (`hildesheim`): Hildesheim (1.1.1.3-n2); Spicil. 2. (1.1.1.4-n21); Hildesheim fol. 130. (1.1.1.5-n18); Hildesheim spicil. 2 de Melanc. fol. 217 et fol. 127. (1.1.3.2-n14)
> Draft (claude-opus-5-5, authors-v1, 2026-11-02; high): Franz Hildesheim (1551–1614) was a German physician. He wrote Spicilegia, a collection of short treatises on diseases of the head and brain; the second spicilegium deals with melancholy. *Why cited:* Burton cites his spicilegium on melancholy, by folio number, for the causes, symptoms and remedies of the disease.

**33. Hippocrates** (`hippocrates`): Hippocrates lib. de insania. (1.1.1.4-n13); Hipp. (1.1.2.11-n9); Sect. 7 de mor. vulgar. lib. 6. (1.1.3.2-n2); Lib. 1 cap. 5 prog. (1.2.1.1-n19)
> Draft (claude-opus-5-5, authors-v1, 2026-11-02; high): Hippocrates (c.460–c.370 BC) was a Greek physician of Cos and the founder figure of Greek medicine. The Hippocratic writings include the Aphorisms, the Prognostics and the Epidemics (cited as 'de morbis vulgaribus'). *Why cited:* Burton cites him as the foundational medical authority, using the Aphorisms, the Prognostics and the Epidemics. 'Lib. de insania' most likely refers to the pseudo-Hippocratic letters about the supposed madness of Democritus, which matter to Burton's persona of 'Democritus Junior'.

**34. Johannes Crato von Krafftheim** (`crato`): Crato. (1.1.1.1-n54); Epist. 173 in Scholtz. (1.2.1.6-n7); Crato consil. 21. (1.2.2.6-n5); Crato consil. 21 lib. 2. (1.2.3.4-n8)
> Draft (claude-opus-5-5, authors-v1, 2026-11-02; high): Johannes Crato von Krafftheim (1519–1585) was a physician from Breslau who served the emperors Ferdinand I, Maximilian II and Rudolf II. His medical consilia and letters were published in collections edited by Lorenz Scholz. *Why cited:* Burton cites his consilia and letters, including those in Scholz's collection, for case advice on treating melancholy and related complaints.

**35. Daniel Heinsius** (`heinsius`): Heinsius orat. funeb. de Scal. (1.2.3.14-n22); Heinsius. (1.2.3.15-n103); Heinsius praefat Poematum. (1.2.3.15-n80); Heinsius Austriac. (1.2.4.7-n38)
> Draft (claude-opus-5-5, authors-v1, 2026-11-02; medium): Daniel Heinsius (1580–1655) was a Dutch classical scholar and Latin poet who taught at Leiden. Among his works are Latin poems and orations, including a funeral oration for Joseph Scaliger. *Why cited:* Burton draws on his orations, poems, prefaces and letters for literary and moral material, such as praise of scholarship and the scholar's life.

**36. Livy** (`livy`): Livius lib. 38. (1.2.1.1-n10); Liv. (1.2.1.2-n52); Livius. (1.2.3.14-n45); Livius lib. 2. (1.2.3.14-n54)
> Draft (claude-opus-5-5, authors-v1, 2026-11-02; high): Livy (Titus Livius, 59 BC–AD 17) was a Roman historian from Padua. He wrote the history of Rome from its foundation (Ab urbe condita), which survives in part and is cited by book and by decade. *Why cited:* Burton uses him as a source of examples and anecdotes from Roman history.

**37. Philipp Melanchthon** (`melanchthon`): De Anima. (1.1.2.1-n2); Melanchthon. (1.1.2.10-n1); De anima. (1.1.2.4-n3); Melanct. (1.1.2.8-n3)
> Draft (claude-opus-5-5, authors-v1, 2026-11-02; high): Philipp Melanchthon (1497–1560) was a German humanist and Protestant reformer at Wittenberg, and Luther's close colleague. His Liber de anima is a textbook of natural philosophy on the soul and the body. *Why cited:* Burton cites De anima for the physiology of the humours, the faculties of the soul and the anatomy underlying melancholy.

**38. Heinrich Cornelius Agrippa** (`agrippa`): Agrippa, lib. 3 cap. 18 de occul. Philos. (1.2.1.2-n10); Lib. 1 cap. 6 occult. Philos. (1.2.1.2-n108); Agrippa de occult. Philos. lib. 3 cap. 18. (1.2.1.2-n11); Agrippa lib. 3 de occul. ph. cap. 18, (1.2.1.2-n33)
> Draft (claude-opus-5-5, authors-v1, 2026-11-02; high): Heinrich Cornelius Agrippa von Nettesheim (1486–1535) was a German humanist, physician and writer on the occult. His works include De occulta philosophia, De incertitudine et vanitate scientiarum and a collection of letters. *Why cited:* Burton cites De occulta philosophia, especially book 3, chapter 18, on spirits, demons and magic, and De vanitate for its satire on learning and the professions.

**39. Giovanni Botero (Boterus)** (`boterus`): Boterus de In. urbium. (1.1.1.1-n35); Boterus lib. 1 polit. cap. 4. (1.2.4.5-n8); De increm. urb. lib. 3 cap. 3. (1.2.4.7-n54); Boterus lib. 3 polit. cap. 1. (2.2.4.1-n56)
> Draft (claude-opus-5-5, authors-v1, 2026-11-02; high): Giovanni Botero (c.1544–1617) was a Piedmontese priest and political writer. He wrote Della ragion di Stato and a treatise on the causes of the greatness of cities; both circulated in Latin translation. *Why cited:* Burton cites his political works and his treatise on the growth of cities in discussing the state of commonwealths, population and good government.

**40. Paolo Giovio (Jovius)** (`jovius`): Jovius descrip. Britonum. (1.2.2.3-n7); Jovius vita ejus. (1.2.3.10-n36); Jovius hist. 1 lib. (1.2.3.11-n15); Tom. 2 de vitis illustrium, lib. 4 de vit. Leon. 10. (1.2.3.13-n11)
> Draft (claude-opus-5-5, authors-v1, 2026-11-02; high): Paolo Giovio (Paulus Jovius, 1483–1552) was an Italian historian and physician from Como, and later bishop of Nocera. He wrote a history of his own times, lives of famous men including Pope Leo X, and a description of Britain. *Why cited:* Burton uses him for historical anecdotes, biographies of notable men and his description of the British Isles.

**41. Matteo Ricci (Riccius)** (`ricci`): Expedit. in Sinas lib. 1 cap. 3. (1.2.2.3-n9); Riccius, lib. 5 cap. 12. (1.2.2.3-n9); Expedit. in Sinas, lib. 1 cap. 9. (1.2.3.2-n15); Riccius expedit. in Sinas lib. 1 cap. 3. (1.2.4.6-n79)
> Draft (claude-opus-5-5, authors-v1, 2026-11-02; high): Matteo Ricci (1552–1610) was an Italian Jesuit missionary in China. His account of the mission was edited and published in Latin by Nicolas Trigault as De Christiana expeditione apud Sinas (1615). *Why cited:* Burton cites the Expeditio for Chinese customs and especially for the Chinese system of government by learned officials, which he holds up as a model.

**42. Donato Antonio Altomari (Altomarus)** (`altomari`): Cap. 9 art. Hydrophobia. (1.1.1.4-n17); Altomar. (1.1.3.2-n8); Altomarus, (1.2.5.5-n1); Altomarus (1.3.1.1-n7)
> Draft (claude-opus-5-5, authors-v1, 2026-11-02; medium): Donato Antonio Altomari was a sixteenth-century physician of Naples who wrote a general medical work on the treatment of diseases. *Why cited:* Burton cites him by chapter as a medical authority on melancholy and on related conditions such as hydrophobia.

**43. Strozzi Cicogna** (`cicogna`): Strozzius Cicogna: lib. 3 cap. 4 omnif. mag. (1.2.1.2-n10); Cicogna 1 part. lib. 2 cap. 3. (1.2.1.2-n20); Cicogna omnif. mag. lib. 2 cap. 3. (1.2.1.2-n24); Lib. 3 omnif. mag. cap. 2. (1.2.1.2-n27)
> Draft (claude-opus-5-5, authors-v1, 2026-11-02; medium): Strozzi Cicogna was an Italian cleric of the early seventeenth century. He wrote a large treatise on magic, spirits and enchantments, which was published in Latin as Magiae omnifariae theatrum. *Why cited:* Burton cites his 'Omnifaria magia' for the nature, kinds and powers of spirits and devils, in the digression on spirits.

**44. Jerome** (`jerome`): Hierom. in 3 Ephes. (1.2.1.2-n85); Idem (1.2.1.2-n85); Hieronymus ep. 72 (1.2.2.6-n23); Hieron. ad Paulin. (1.2.3.12-n17)
> Draft (claude-opus-5-5, authors-v1, 2026-11-02; high): Jerome (Eusebius Hieronymus, c.347–420) was a Latin Church Father and biblical scholar, best known for the Vulgate translation of the Bible. He also wrote many letters and biblical commentaries, including one on Ephesians. *Why cited:* Burton quotes his letters and commentaries for moral and ascetic teaching, for example on solitude, the dangers of idleness and religious life.

**45. Filotheo Elião de Montalto (Montaltus)** (`montalto`): Montaltus, (1.1.1.3-n2); Cap. 3 de mel. (1.1.3.2-n4); Montaltus cap. 22. (1.2.1.4-n11); Montaltus cap. 22 (1.2.1.4-n12)
> Draft (claude-opus-5-5, authors-v1, 2026-11-02; high): Filotheo Elião de Montalto (Philotheus Elianus Montaltus, c.1567–1616) was a Portuguese Jewish physician who became physician to Marie de' Medici in France. His Archipathologia (1614) deals with diseases of the head, including melancholy. *Why cited:* Burton cites the chapters of the Archipathologia on melancholy as a leading recent authority on its causes, symptoms and cure.

**46. George Buchanan** (`buchanan`): Buchanan. Baptist. (1.1.1.1-n41); Buchanan. eleg. lib. (1.2.3.15-n39); Buchanan. Eleg. lib. (1.4.1.1-n60); Buchanan. (3.2.2.3-n11)
> Draft (claude-opus-5-5, authors-v1, 2026-11-02; high): George Buchanan (1506–1582) was a Scottish humanist, Latin poet and historian, and tutor to the young James VI. His works include the Latin tragedy Baptistes, books of elegies, silvae and hendecasyllables, Latin paraphrases of the Psalms, and a history of Scotland (Rerum Scoticarum historia). *Why cited:* Burton quotes Buchanan's Latin verse from the Baptistes, the elegies, the silvae and the hendecasyllables, using a modern poet's lines to illustrate his points much as he uses the classical poets.

**47. Quintus Curtius Rufus** (`curtius`): Lib. 8. (1.2.4.5-n6); Curtius lib. 8. (1.4.1.1-n51); Curtius (2.2.1.1-n21); Curtius. (2.3.2.1-n48)
> Draft (claude-opus-5-5, authors-v1, 2026-11-02; high): Quintus Curtius Rufus was a Roman historian, probably of the first century AD, whose life is little known. His history of Alexander the Great survives in ten books, of which the first two are lost. *Why cited:* Burton uses Curtius as a source of stories about Alexander and his campaigns, citing individual books (for example books 5, 6 and 8).

**48. Lucan** (`lucan`): Lucan. (1.2.3.10-n2); Lucan. lib. 8. (1.2.3.15-n76); Lucan. lib. 1. (1.2.4.6-n4); Lucan lib. 8. (2.2.4.1-n44)
> Draft (claude-opus-5-5, authors-v1, 2026-11-02; high): Marcus Annaeus Lucanus (AD 39–65) was a Latin poet born at Corduba in Spain and a nephew of the philosopher Seneca. He was forced to take his own life after the Pisonian conspiracy against Nero. His epic on the civil war between Caesar and Pompey (Bellum civile, also called Pharsalia) survives in ten books. *Why cited:* Burton quotes lines from the books of the Pharsalia; book 6, which contains the Thessalian witch Erictho, is a classical source on witchcraft and necromancy.

**49. Baptista Mantuanus** (`mantuan`): Mant. (1.2.3.10-n2); Mantuan. (1.2.4.6-n73); Mant. ecl. 2. (3.2.3.1-n104); Ecl. 1. (3.2.3.1-n115)
> Draft (claude-opus-5-5, authors-v1, 2026-11-02; high): Baptista Mantuanus (Battista Spagnoli, 1447–1516) was a Carmelite friar of Mantua and a prolific Latin poet, who became prior general of his order. His best-known works are the ten eclogues of the Adulescentia, which were widely read in schools, and the Fasti, a verse calendar of saints' feasts. *Why cited:* Burton quotes Mantuan's eclogues, which deal with love and include attacks on women, and in one example the Fasti on St George.

**50. Persius** (`persius`): Pers. (1.2.2.5-n10); Persius Sat. 5. (1.2.3.13-n28); Pers. 1 Sat. (1.2.3.14-n10); Pers. Sat. 2. (1.2.3.15-n115)
> Draft (claude-opus-5-5, authors-v1, 2026-11-02; high): Aulus Persius Flaccus (AD 34–62) was a Roman satirist from Etruria who wrote under Stoic influence. He left a single book of six satires. *Why cited:* Burton quotes Persius's satires, cited by number, for short moral lines on human folly, vice and the state of the mind.

**51. Antonio Guainerio (Guianerius)** (`guainerio`): De feb. tract. 3 diff. 2 cap. 1. (1.1.3.3-n11); Guainerius diff. 2 cap. 7. (1.1.3.3-n16); cap. 5. Tract. 15 cap. 2. (1.2.2.2-n34); Guainer. tract. 15 cap. 17. (1.2.3.12-n19)
> Draft (claude-opus-5-5, authors-v1, 2026-11-02; medium): Antonio Guainerio was a fifteenth-century Italian physician who taught medicine at Pavia. His medical writings include practical treatises on diseases of the head and on fevers (De febribus). *Why cited:* Burton cites Guainerio as a medical authority on melancholy and related disorders, giving his references by tractate and chapter (for example tract. 15).

**52. Ercole Sassonia (Hercules de Saxonia)** (`hercules-saxonia`): Cap. 16 lib. 1. (1.1.3.1-n2); Cap. 13 tract. posth. de melan. (1.1.3.4-n14); Tract. de Mel. cap. 7. (1.1.3.4-n5); lib. 1 cap. 16. (1.2.2.5-n11)
> Draft (claude-opus-5-5, authors-v1, 2026-11-02; high): Ercole Sassonia (Hercules de Saxonia, 1551–1607) was an Italian physician and professor of medicine at Padua. His works include the Pantheum medicinae selectum and a treatise on melancholy that was published after his death (Tractatus posthumus de melancholia). *Why cited:* Burton relies on Sassonia's posthumous treatise on melancholy as a specialist authority on the causes, signs and cure of the disease, citing it by chapter.

**53. Propertius** (`propertius`): Propertius. (3.2.1.1-n26); Propert. (3.2.1.2-n38); Propertius lib. 2. (3.2.1.2-n42); Propert. lib. 1. (3.2.2.2-n120)
> Draft (claude-opus-5-5, authors-v1, 2026-11-02; high): Sextus Propertius (born c. 50 BC, died after 16 BC) was a Latin elegiac poet from Umbria. His four books of elegies are largely about his love for a woman he calls Cynthia. *Why cited:* Burton quotes Propertius's elegies, mainly from books 1 and 2, for verses on love and the sufferings of lovers.

**54. Suetonius** (`suetonius`): Sueton. cap. 69 in Caligula. (1.2.1.2-n74); Idem cap. 18. (1.2.1.2-n75); Sueton. lib. de gram. (1.2.3.14-n29); Sueton. cap. 12 in Domitiano. (1.2.3.14-n49)
> Draft (claude-opus-5-5, authors-v1, 2026-11-02; high): Gaius Suetonius Tranquillus (c. AD 70–after 122) was a Roman biographer and imperial official. His main surviving works are the Lives of the Caesars, from Julius Caesar to Domitian, and part of a work on grammarians and rhetoricians (De grammaticis et rhetoribus). *Why cited:* Burton uses Suetonius's Lives, cited by chapter for emperors such as Caligula and Domitian, for anecdotes about their behaviour, and also cites the book on grammarians.

**55. Athenaeus** (`athenaeus`): Dipnosophist. lib. 12. (1.2.4.6-n77); Dipnosophist. lib. (1.3.1.4-n3); Athenaeus dipnoso. (2.2.4.1-n57); Dipnosop. lib. 10. (2.2.6.4-n14)
> Draft (claude-opus-5-5, authors-v1, 2026-11-02; high): Athenaeus of Naucratis in Egypt was a Greek writer active around AD 200. His Deipnosophistae ('The Learned Banqueters') presents a long series of conversations at dinner and survives in fifteen books, full of quotations and anecdotes. *Why cited:* Burton draws on the Deipnosophistae for anecdotes and quotations about luxury, feasting, drinking and love, citing books such as 10, 12, 13 and 14.

**56. Caspar Barth (Barthius)** (`barth`): Barthius praefat. pronodid. (1.2.4.4-n2); Barthius (3.1.1.1-n26); Barthio interprete. (3.1.1.1-n28); Barthio (3.2.1.2-n45)
> Draft (claude-opus-5-5, authors-v1, 2026-11-02; high): Caspar von Barth (1587–1658) was a German classical scholar and Latin poet, known for his large Adversaria and his editions of Latin authors. He also made a Latin translation of the Spanish Celestina under the title Pornoboscodidascalus. *Why cited:* Burton cites Barth mainly as translator ('Barthio interprete'), quoting the Celestina in his Latin version and referring to the preface of the Pornoboscodidascalus, a text about bawds and lovers.

**57. Geoffrey Chaucer** (`chaucer`): Chaucer. (1.2.4.7-n7); Chaucer in the wife of (3.2.2.5-n12); Chaucer in the Knight’s tale. (3.2.3.1-n10); Chaucer in the Knight’s Tale. (3.2.3.1-n150)
> Draft (claude-opus-5-5, authors-v1, 2026-11-02; high): Geoffrey Chaucer (c. 1343–1400) was an English poet and royal servant in London. His works include The Canterbury Tales, The Parliament of Fowls, Troilus and Criseyde, and an English version of the Romance of the Rose. *Why cited:* Burton quotes Chaucer's English verse, including the Knight's Tale, the Wife of Bath, the Romance of the Rose and the Parliament ('assembly') of Fowls, mostly on love and women.

**58. Euripides** (`euripides`): Euripides. (1.2.3.10-n18); Euripides Menalip. (2.3.3.1-n67); Euripides Andromach. (3.2.5.3-n71)
> Draft (claude-opus-5-5, authors-v1, 2026-11-02; high): Euripides (c. 480–406 BC) was an Athenian tragic poet, one of the three great tragedians. Some eighteen of his plays survive, including the Andromache, and many fragments of lost plays, such as those on Melanippe. *Why cited:* Burton quotes Euripides for sententious lines, including passages from the Andromache and from the fragments of the Melanippe plays.

**59. Johannes Heurnius** (`heurnius`): Heurnius, (1.1.1.3-n2); Heurnius (1.1.2.9-n2); Heurnius lib. 3 cap. 19 prax. med. (1.2.2.3-n22); lib. 3 cap. 1 (2.1.4.1-n7)
> Draft (claude-opus-5-5, authors-v1, 2026-11-02; high): Johannes Heurnius (Jan van Heurne, 1543–1601) was a Dutch physician and professor of medicine at Leiden. His main work is a textbook of practical medicine, the Praxis medicinae nova ratio. *Why cited:* Burton cites Heurnius's Praxis medicinae, including its preface, as a recent medical authority on melancholy and its treatment.

**60. Leo Africanus** (`leo-africanus`): Leo Afer lib. 1. (1.2.2.3-n4); Leo Afer cap. ult. lib. 1. (1.2.4.6-n43); Lib. 1 cap. ult. (1.2.4.6-n47); Leo Afer. (1.2.4.6-n50)
> Draft (claude-opus-5-5, authors-v1, 2026-11-02; high): Leo Africanus (al-Hasan al-Wazzan) was born in Granada in the late fifteenth century and brought up in Fez. He was captured at sea and taken to Rome, where he was baptised, and there he wrote a description of Africa, which was published in Italian by Ramusio in 1550 and later in Latin as De Africa. *Why cited:* Burton uses Leo's Description of Africa, especially the last chapter of book 1, as a source on the customs, character and way of life of the peoples of North Africa.

**61. Sebastian Münster** (`munster`): Munster lib. 3 Cos. cap. 462. (1.1.1.1-n40); Munster cosmog. lib. 4 cap. 43. (1.2.1.1-n9); Cosmog. lib. 3 cap. 36. (1.2.2.1-n40); Munster de rusticis Germaniae Cosmog. cap. 27 lib. 3. (1.2.4.6-n44)
> Draft (claude-opus-5-5, authors-v1, 2026-11-02; high): Sebastian Münster (1488–1552) was a German Hebraist and cosmographer who taught at Basel. His main work is the Cosmographia (first edition 1544), a large illustrated description of the world, with particular attention to the German lands. *Why cited:* Burton cites the Cosmographia by book and chapter as a source for the customs, regions and peoples of Europe and beyond, including the German peasantry.

**62. Valerius Maximus** (`valerius-maximus`): Valerius lib. 6 cap. 11. (1.1.1.5-n11); Lib. 7 cap. 1. (1.1.1.5-n3); Valer. lib. 7 cap. 3. (1.2.3.10-n45); Lib. 9 cap. 4. (1.2.3.12-n11)
> Draft (claude-opus-5-5, authors-v1, 2026-11-02; high): Valerius Maximus was a Roman writer of the reign of Tiberius (early 1st century CE). He compiled the Facta et dicta memorabilia, nine books of memorable deeds and sayings arranged by theme for use by orators. *Why cited:* Burton cites him by book and chapter for moral anecdotes and historical examples from Roman and foreign history.

**63. Ludovico Ariosto** (`ariosto`): Ariosto. (3.2.3.1-n156); Ariosto, lib. 29 hist. 8. (3.2.3.1-n160); Ariosto lib. 1 cant. 1 staff. 5. (3.2.3.1-n187); Ariosto lib. 25 st. 70. (3.2.5.3-n51)
> Draft (claude-opus-5-5, authors-v1, 2026-11-02; high): Ludovico Ariosto (1474–1533) was an Italian poet from the court of Ferrara. His chief work is the chivalric romance Orlando Furioso, whose hero goes mad for love. *Why cited:* Burton draws on Orlando Furioso, citing it by book or canto and stanza, for stories and verses about love, jealousy and love-madness.

**64. William Camden** (`camden`): Camden in Wiltsh. (1.2.4.5-n15); Camden in Staffordshire. (2.2.4.1-n16); Camden. (2.3.3.1-n128); Camden in Glouc. (2.3.7.1-n25)
> Draft (claude-opus-5-5, authors-v1, 2026-11-02; high): William Camden (1551–1623) was an English antiquary and historian, and headmaster of Westminster School. His main works are the Britannia (1586), a county-by-county survey of Britain, and the Annales of the reign of Elizabeth I. *Why cited:* Burton cites the Britannia by county (Wiltshire, Staffordshire, Gloucestershire) for English places, and the Annales for events of Elizabeth's reign.

**65. Aulus Gellius** (`gellius`): Lib. 19 cap. 2. (1.1.2.6-n6); Lib. 19 cap. 10. (1.2.2.6-n18); Gellius lib. 3 cap. 1. (1.2.3.12-n25); Lib. 7. 16. (2.3.3.1-n66)
> Draft (claude-opus-5-5, authors-v1, 2026-11-02; high): Aulus Gellius was a Roman writer of the 2nd century CE. His Noctes Atticae (Attic Nights) is a miscellany in twenty books of notes on language, philosophy, law and anecdote. *Why cited:* Burton cites the Attic Nights by book and chapter for anecdotes, sayings of philosophers and points of ancient learning.

**66. Lucretius** (`lucretius`): Lucretius lib. 4, 1134. (1.1.1.5-n7); Lucret. (1.2.4.3-n8); Lucret. lib. 3. (1.4.1.1-n14); Lucretius. (3.2.1.1-n30)
> Draft (claude-opus-5-5, authors-v1, 2026-11-02; high): Titus Lucretius Carus (c. 99–c. 55 BCE) was a Roman poet and Epicurean. His one work is De rerum natura, a philosophical poem in six books setting out Epicurean physics and ethics. *Why cited:* Burton quotes De rerum natura mainly from Book 4, which attacks the passion of love (including the line on the bitterness that rises from pleasure, 4.1134), and from Book 3, on the soul and the fear of death.

**67. Girolamo Mercuriale** (`mercuriale`): Mercurialis, de affect. lib. 1 cap. 10 (1.2.2.1-n11); Mercurialis (1.2.2.6-n20); Mercurialis de affect. capitis lib. 1 cap. 10 de Melanc. (1.2.5.1-n8); Mercurialis consil. 86, (1.3.1.1-n15)
> Draft (claude-opus-5-5, authors-v1, 2026-11-02; high): Girolamo Mercuriale (1530–1606) was an Italian physician from Forlì who taught medicine at Padua, Bologna and Pisa. He wrote widely on medicine, including De arte gymnastica, works on diseases, and collections of medical consultations. *Why cited:* Burton uses him as a medical authority on melancholy, citing his treatment of diseases of the head and his consilia (case opinions) on particular patients.

**68. Pausanias** (`pausanias`): Pausanias, (1.2.1.2-n25); Lib. 8 in Acad. (1.2.4.3-n7); Pausanias in Achaicis lib. 7. (1.2.4.7-n36); Pausanias. (2.5.1.5-n5)
> Draft (claude-opus-5-5, authors-v1, 2026-11-02; high): Pausanias was a Greek traveller and geographer of the 2nd century CE. His Description of Greece, in ten books named after regions (such as Laconica, Achaica and Arcadica), records monuments, cults and local legends. *Why cited:* Burton cites the Description of Greece by regional book for Greek legends, religious customs and local history.

**69. Felix Platter (Platerus)** (`platter`): Plater cap. 3 de mentis alienatione. (1.1.1.4-n7); Plater lib. 3 de mentis alien. (1.2.3.11-n21); De mentis alienat. cap. 3. (1.2.3.14-n53); Platerus. (1.2.4.3-n10)
> Draft (claude-opus-5-5, authors-v1, 2026-11-02; high): Felix Platter (1536–1614) was a Swiss physician and professor of medicine at Basel. His main works are the Praxis medica (1602) and the Observationes (1614), both of which give much attention to mental disorders. *Why cited:* Burton relies on Platter's chapter 'de mentis alienatione' as an authority on the causes, kinds and symptoms of madness and melancholy.

**70. Juan Luis Vives** (`vives`): Lib. 1 de verit. Fidei. (1.2.1.2-n14); Lod. Vives. (1.2.3.14-n57); Vives 3 de anima (1.2.3.4-n12); Vives (2.2.4.1-n87)
> Draft (claude-opus-5-5, authors-v1, 2026-11-02; high): Juan Luis Vives (1493–1540) was a Spanish humanist, born in Valencia, who worked mainly in the Low Countries and for a time in England. His works include De anima et vita (1538), De disciplinis (1531), which contains De causis corruptarum artium, and De veritate fidei Christianae. *Why cited:* Burton cites De anima, especially Book 3 on the passions, for the psychology of the emotions, and his other works on learning and religion.

**71. Bernard of Clairvaux** (`bernard-clairvaux`): Lib. de transmut. Malac. ep. (1.2.1.2-n90); Tract. de Inter. do. cap. 62. (1.2.3.11-n2); Ser. 35. (1.2.3.3-n3); Bernardus. (1.2.4.4-n1)
> Draft (claude-opus-5-5, authors-v1, 2026-11-02; medium): Bernard of Clairvaux (1090–1153) was a French Cistercian abbot and theologian. His works include many sermons, among them the sermons on the Song of Songs, letters, treatises, and a Life of St Malachy. *Why cited:* Burton quotes Bernard's sermons and devotional writings for spiritual and moral comment on sin, the passions and the soul.

**72. Jean Fernel** (`fernel`): Fernelius Path. lib. 1 cap. 9, 10, 11, 12. (1.1.1.2-n11); Lib. 1 de Abditis rerum causis. (1.2.1.1-n20); Lib. 1 Path. cap. 11. (1.2.1.5-n1); Lib. 1 cap. 11 path. (1.2.1.6-n1)
> Draft (claude-opus-5-5, authors-v1, 2026-11-02; high): Jean Fernel (1497–1558) was a French physician and professor of medicine at Paris. His Universa medicina includes the Pathologia, and he also wrote De abditis rerum causis (1548), on the hidden causes of things. *Why cited:* Burton cites the Pathologia, Book 1, as an authority on the causes of disease, and De abditis rerum causis on occult causes.

**73. Girolamo Fracastoro (Fracastorius)** (`fracastoro`): Lib. 2 de intellectione. (1.1.1.4-n6); Lib. 2 de Intell. (1.3.1.2-n44); De symp. & Antip. cap. 12. (1.3.3.1-n16); Lib. 2 de Intellectione. (1.3.3.1-n5)
> Draft (claude-opus-5-5, authors-v1, 2026-11-02; high): Girolamo Fracastoro (c. 1478–1553) was a physician and poet from Verona. His works include the poem Syphilis, De contagione, De sympathia et antipathia rerum (1546), and a dialogue on the intellect (De intellectione). *Why cited:* Burton cites De intellectione, Book 2, on the mind and the passions, and De sympathia et antipathia on natural attractions and aversions.

**74. Herodotus** (`herodotus`): Herodotus vita ejus. (1.2.4.6-n88); Lib. 2. (2.2.3.1-n15); Euterpe de Aegyptiis. (2.4.1.1-n15); Herodotus lib. 2 (3.2.1.2-n16)
> Draft (claude-opus-5-5, authors-v1, 2026-11-02; high): Herodotus (c. 484–c. 425 BCE) was a Greek historian from Halicarnassus. His Histories, later divided into nine books named after the Muses (Clio, Euterpe and so on), cover the Persian Wars and the peoples of the ancient world. *Why cited:* Burton cites the Histories, especially Book 2 (Euterpe) on the Egyptians, for customs and stories of ancient peoples; 'vita ejus' probably refers to the Life of Homer that was then attributed to Herodotus.

**75. Thomas More** (`more`): Th. Morus Epigram. (3.2.5.3-n14); Morus, (djr-n241); Utop. lib. 2. (djr-n241); Morus Utopia. (djr-n291)
> Draft (claude-opus-5-5, authors-v1, 2026-11-02; high): Sir Thomas More (1478–1535) was an English humanist, statesman and Lord Chancellor, executed under Henry VIII. His works include Utopia (1516) and a collection of Latin epigrams. *Why cited:* Burton cites Utopia, Books 1 and 2, on ideal commonwealths and social ills, and quotes More's Latin epigrams.

**76. Johann Schenck von Grafenberg (Schenkius)** (`schenck`): Lib. 7 de Venenis. (1.1.1.4-n19); Schenkius 7 lib. de Venenis. (1.1.1.4-n22); Lib. 1 cap. de Mania. (1.1.1.4-n27); Lib. 1 de Mania. (1.2.2.4-n5)
> Draft (claude-opus-5-5, authors-v1, 2026-11-02; medium): Johann Schenck von Grafenberg (1530–1598) was a German physician who practised at Freiburg im Breisgau. His main work is a large collection of medical case histories, the Observationes medicae rarae, novae, admirabiles et monstrosae, published in seven books. The first book deals with diseases of the head, including mania, and the seventh deals with poisons. *Why cited:* Burton uses Schenck's Observationes as a source of strange and notable cases, especially on mania and on poisons (Lib. 7 de Venenis), and sometimes pairs him with Mizaldus as a collector of remarkable facts.

**77. Girolamo Zanchi (Zanchius)** (`zanchi`): Zanchius lib. 4 cap. 10 & 11 de malis angelis. (1.2.1.2-n100); Zanch. cap. 10 lib. 4. (1.2.1.2-n101); Zanch. (1.2.1.2-n33); Zanch. lib. 4 cap. 3 de Angel. malis. (1.2.1.2-n48)
> Draft (claude-opus-5-5, authors-v1, 2026-11-02; high): Girolamo Zanchi (1516–1590) was an Italian Protestant theologian who left Italy for the Reformed churches and taught at Strasbourg and Heidelberg. His De operibus Dei intra spatium sex dierum creatorum includes a long treatise on angels, with a book on evil angels (de malis angelis). *Why cited:* Burton cites Zanchi's discussion of evil angels (lib. 4 de malis angelis) as a Protestant authority on the nature, powers and operations of devils, alongside Pererius, Origen and Casmann.

**78. Achilles Tatius** (`achilles-tatius`): Achilles Tatius lib. 2. (3.2.1.2-n10); Lib. 6. (3.2.2.2-n118); Tatius lib. 5. (3.2.2.2-n123); Achilles Tatius lib. 1. (3.2.2.2-n87)
> Draft (claude-opus-5-5, authors-v1, 2026-11-02; high): Achilles Tatius was a Greek novelist of the Roman imperial period, probably of the second century AD, said to have come from Alexandria. His surviving work is the romance Leucippe and Clitophon, in eight books. *Why cited:* Burton quotes the romance, by book number, for its descriptions of love, beauty and the passions and stratagems of lovers in his section on love-melancholy.

**79. Leonhart Fuchs (Fuchsius)** (`fuchs`): Fuchsius instit. lib. 3 sect. 1 cap. 7. (1.1.1.2-n11); Fuch. (1.1.1.2-n2); Cap. 3 de mentis alienatione. (1.1.1.4-n28); Fuchsius lib. 3 sect. 1 cap. 7. (1.1.1.5-n18)
> Draft (claude-opus-5-5, authors-v1, 2026-11-02; high): Leonhart Fuchs (1501–1566) was a German physician and botanist and a professor of medicine at Tübingen. He is known for his illustrated herbal De historia stirpium (1542) and for his textbook of medicine, the Institutiones medicinae. *Why cited:* Burton cites Fuchs's Institutiones (e.g. lib. 3 sect. 1 cap. 7) as a standard medical authority on the causes, symptoms and treatment of melancholy and mental disorder.

**80. Bernard de Gordon (Gordonius)** (`gordon`): Gord. cap. 10 lib. 1 (1.2.2.4-n11); Gordonius de observat. vit. hum. lib. 1. (1.2.2.6-n8); Gordonius: (1.3.1.1-n16); Gordon. (1.3.1.2-n11)
> Draft (claude-opus-5-5, authors-v1, 2026-11-02; high): Bernard de Gordon (fl. c. 1270–1330) was a physician who taught medicine at Montpellier. His main work is the Lilium medicinae, a practical medical handbook divided into parts (particulae). He also wrote a treatise on preserving human life (De conservatione vitae humanae). *Why cited:* Burton uses Gordon as a medieval medical authority on the diseases of the head, melancholy and love-sickness, citing the Lilium by particula and chapter and also his treatise on the preservation of life.

**81. John of Salisbury** (`john-salisbury`): Sarisburiensis Polycrat. lib. 1 cap. 4. (1.2.3.13-n4); Sarisburiensis. (1.2.3.13-n9); Sarisburiensis Polycrat. lib. 5 cap. 10. (1.2.3.15-n98); Policrat. lib. 1 cap. 8. (2.2.4.1-n83)
> Draft (claude-opus-5-5, authors-v1, 2026-11-02; high): John of Salisbury (c. 1115/20–1180) was an English scholar and churchman, secretary to archbishops of Canterbury and from 1176 bishop of Chartres. His main works are the Policraticus, also called De nugis curialium ('on the frivolities of courtiers'), and the Metalogicon. *Why cited:* Burton cites the Policraticus (also by its subtitle De nugis curialium) for moral and political observations, such as the vices of courtiers, hunting and other pastimes, and love.

**82. John Leech (Leochaeus)** (`leech-john`): Leochaeus Anacreon. (2.2.6.4-n37); Leochaeus. (3.2.2.2-n101); Leochaeus Panthea. (3.2.2.2-n127)
> Draft (claude-opus-5-5, authors-v1, 2026-11-02; medium): John Leech (Joannes Leochaeus) was a Scottish poet of the early seventeenth century who wrote in Latin. He published collections of epigrams and amatory verse. *Why cited:* Burton quotes Leech's Latin verses, including poems titled with references to Anacreon and to Panthea, mainly on love and beauty in the section on love-melancholy.

**83. Giovanni Antonio Magini (Maginus)** (`maginus`): Maginus Geog. (1.2.1.6-n9); Maginus (1.2.2.5-n10); Maginus in Persia. (1.2.2.5-n15); Maginus. (2.2.3.1-n142)
> Draft (claude-opus-5-5, authors-v1, 2026-11-02; high): Giovanni Antonio Magini (1555–1617) was an Italian astronomer, mathematician and cartographer who taught at Bologna. He published an edition of Ptolemy's Geography (1596) with commentary and descriptions of the modern regions of the world. *Why cited:* Burton cites Magini's Geography for descriptions of countries and peoples, such as Persia, often alongside other geographers such as Quad.

**84. Giovanni Battista da Monte (Montanus)** (`montanus`): Consil. 26. (1.1.3.3-n9); Montanus (1.2.3.15-n10); Montanus consil. 230, (1.3.1.1-n17); Consil. 230 pro Abbate Italo. (2.1.1.1-n1)
> Draft (claude-opus-5-5, authors-v1, 2026-11-02; high): Giovanni Battista da Monte (1498–1551) was an Italian physician from Verona who taught medicine at Padua. His Consilia medica, a collection of written opinions on particular patients, was published after his death. *Why cited:* Burton cites Montanus's numbered consilia as case histories of melancholy patients and their treatment, for example consilium 230 for an Italian abbot.

**85. Tibullus** (`tibullus`): De Sulpicia lib. 4. (3.2.2.2-n122); Tibul. lib. 3 eleg. 4. (3.2.2.4-n105); Tibul. lib. 3. 6. (3.2.2.4-n99); Tibullus. (3.2.3.1-n161)
> Draft (claude-opus-5-5, authors-v1, 2026-11-02; high): Albius Tibullus (c. 55–19 BC) was a Roman poet who wrote love elegies. The collection that has come down under his name (the Corpus Tibullianum) also includes poems by other writers, among them a group of poems by and about Sulpicia. *Why cited:* Burton quotes the Tibullan elegies, including the Sulpicia poems of the third and fourth books, for verses on love, lovers' complaints and beauty.

**86. Aetius of Amida** (`aetius`): Lib. 6 cap. 11. (1.1.1.4-n8); Aetius. (1.2.1.4-n12); Idem (1.2.1.4-n12); Aetius lib. 2 & alii. (1.3.1.2-n16)
> Draft (claude-opus-5-5, authors-v1, 2026-11-02; high): Aetius of Amida was a Greek physician of the sixth century AD who worked in the Byzantine Empire. He compiled a large medical encyclopedia in sixteen books, later arranged as four 'tetrabibloi' (groups of four books), which preserves much material from earlier medical writers. *Why cited:* Burton cites Aetius, by book or by tetrabiblos and sermo, as an ancient medical authority on the diseases of the mind, including melancholy, and on their cures.

**87. Ausonius** (`ausonius`): Auson. sap. (1.2.3.14-n15); Ausonius. (1.2.3.14-n55); Ausonius epig. 28. (3.2.2.3-n24); Ausonius cap. 35. (3.2.3.1-n98)
> Draft (claude-opus-5-5, authors-v1, 2026-11-02; high): Decimus Magnus Ausonius (c. 310–c. 395) was a Latin poet and teacher of rhetoric from Bordeaux. He was tutor to the future emperor Gratian and became consul in 379. His works include epigrams, idylls, the Mosella and the Ludus septem sapientum ('Play of the Seven Sages'). *Why cited:* Burton quotes Ausonius's epigrams, idylls and the sayings of the seven sages for short moral verses and memorable lines.

**88. Jean Bodin** (`bodin`): fol. 535. (1.2.1.2-n9); Bodin de rep. cap. de periodis reip. (1.2.1.6-n11); Lib. 5 de rep. cap. 1. (1.2.3.11-n20); Bodin. (1.3.1.2-n38)
> Draft (claude-opus-5-5, authors-v1, 2026-11-02; high): Jean Bodin (1529/30–1596) was a French jurist and political philosopher. His works include the Methodus ad facilem historiarum cognitionem (1566), Les six livres de la République (1576; Latin version De republica, 1586) and the Démonomanie des sorciers (1580), a treatise on witchcraft. *Why cited:* Burton cites Bodin's Republic and Method for History on the rise and decline of states and their causes, and more generally as an authority on politics, history and the influence of place and climate on peoples.

**89. Johann Boemus (Bohemus)** (`boemus`): Bohemus lib. 3 cap. 3. (1.2.1.6-n27); Bohemus in Saxonia. (1.2.2.2-n31); Bohemus (1.2.3.15-n10); Bohemus de Turcis (1.2.4.6-n23)
> Draft (claude-opus-5-5, authors-v1, 2026-11-02; high): Johann Boemus (c. 1485–1535) was a German humanist and Hebrew scholar and a cleric at Ulm. His Omnium gentium mores, leges et ritus (1520) is a widely read description of the customs of the peoples of the world. *Why cited:* Burton cites Boemus's account of the manners of nations for the customs of peoples such as the Saxons and the Turks.

**90. Celio Calcagnini (Calcagninus)** (`calcagnini`): Calcagninus Apologis. (3.2.2.2-n115); Calcagninus dial. (3.2.2.2-n131); Lib. de calumnia. (3.2.2.2-n14); Calcagninus. (3.2.4.1-n16)
> Draft (claude-opus-5-5, authors-v1, 2026-11-02; medium): Celio Calcagnini (1479–1541) was an Italian humanist from Ferrara who taught there. His Latin writings, collected after his death in Opera aliquot (Basel, 1544), include moral fables (Apologi), dialogues and essays. *Why cited:* Burton cites Calcagnini's fables, dialogues and his piece on calumny for moral sayings and humanist observations on human folly and vice.

**91. Joannes de Laet** (`laet`): Laet. occident. (1.2.2.3-n12); Laet. descript. Americae. (1.2.4.5-n9); Laet. lib. 13 cap. 2 descript. (1.3.3.1-n22); Laet. descrip. occid. Indiae. (2.2.3.1-n136)
> Draft (claude-opus-5-5, authors-v1, 2026-11-02; high): Joannes de Laet (1581–1649) was a geographer from Antwerp who worked in Leiden and was a director of the Dutch West India Company. His description of the Americas came out in Dutch in 1625 and in an enlarged Latin edition, 'Novus Orbis seu Descriptionis Indiae Occidentalis libri XVIII', in 1633. *Why cited:* Burton cites his description of the West Indies for the lands, peoples and customs of the Americas, giving book and chapter references.

**92. Abraham Ortelius** (`ortelius`): Ortelius in Helvetia. (1.2.4.6-n52); Ortelius Itinerario. (1.2.4.7-n18); Ortelius (2.2.3.1-n39); Ortelius in Africa (2.2.3.1-n53)
> Draft (claude-opus-5-5, authors-v1, 2026-11-02; high): Abraham Ortelius (1527–1598) was a cartographer and geographer from Antwerp. His 'Theatrum Orbis Terrarum' (1570) is often called the first modern atlas, and he also wrote an 'Itinerarium' of a journey through parts of Belgic Gaul. *Why cited:* Burton cites his descriptions of individual countries (Switzerland, Africa, Greece) and his 'Itinerarium' for geographical and local detail.

**93. George Sandys** (`sandys`): Sandys lib. 1 (2.2.2.1-n7); Sandys, fol. 73 (2.2.4.1-n4); Sandys lib. 1 fol. 56. (2.3.8.1-n6); Sandys (3.2.2.2-n134)
> Draft (claude-opus-5-5, authors-v1, 2026-11-02; high): George Sandys (1578–1644) was an English traveller, poet and translator. He wrote 'A Relation of a Journey begun An. Dom. 1610' (1615), an account of the Ottoman Empire, Egypt and the Holy Land in four books, and he translated Ovid's 'Metamorphoses'. *Why cited:* Burton cites his travel account, by book and folio, for the customs and places of the Turkish Empire and the Levant.

**94. Johann Weyer (Wierus)** (`weyer`): De praestig. (1.1.1.4-n11); Lib. 3 de Lamiis, cap. 17 et 18. (1.2.1.5-n8); Lib. 3 de Lamiis, cap. 10. (1.2.3.2-n10); Lib. 3 cap. 18 de praestig. (1.2.3.2-n21)
> Draft (claude-opus-5-5, authors-v1, 2026-11-02; high): Johann Weyer (Wierus, 1515/16–1588) was a physician from the Low Countries, a pupil of Cornelius Agrippa and physician to the Duke of Cleves. His 'De praestigiis daemonum' (1563) and 'De lamiis' argue that many people accused of witchcraft are deluded melancholics, not real witches. *Why cited:* Burton uses him as an authority on demons, illusions and witches, and on how melancholy and the devil's deceptions are connected.

**95. Aretaeus of Cappadocia** (`aretaeus`): Lib. 3 cap. 5. (1.1.3.2-n11); Aretaeus lib. 3 cap. 5. (1.1.3.2-n17); Aretaeus. (1.2.3.9-n2); Cap. 7. (2.2.4.1-n29)
> Draft (claude-opus-5-5, authors-v1, 2026-11-02; high): Aretaeus of Cappadocia was a Greek physician, probably of the first or second century AD; his dates are uncertain. His treatises on the causes, signs and treatment of acute and chronic diseases include classic descriptions of melancholy and mania. *Why cited:* Burton cites him as an ancient medical authority on the symptoms and cure of melancholy and madness, referring to book and chapter.

**96. Ogier Ghiselin de Busbecq (Busbequius)** (`busbecq`): Epist. 3. (2.2.2.1-n8); Busbequius ep. 3 Leg. Turciae. (2.2.2.1-n9); Busbequius. (2.3.8.1-n6); Busbequius epist. (3.2.2.4-n14)
> Draft (claude-opus-5-5, authors-v1, 2026-11-02; high): Ogier Ghiselin de Busbecq (1522–1592) was a Flemish diplomat who served the Habsburg emperor Ferdinand I as ambassador to Suleiman the Magnificent. He is best known for his four Latin letters on his Turkish embassy, the 'Legationis Turcicae epistolae quattuor'. *Why cited:* Burton cites his letters from the Turkish embassy as a firsthand source on Ottoman manners, customs and government.

**97. Baldassare Castiglione (Castilio)** (`castiglione`): Castilio lib. 2 de aulico. (1.2.4.4-n13); Castilio de aulic. lib. 1 fol. 72. (2.2.6.3-n5); Castilio de aulico lib. 3 fol. 228. (3.2.2.2-n142); Castilio de aulic. lib. 1. (3.2.2.3-n38)
> Draft (claude-opus-5-5, authors-v1, 2026-11-02; high): Baldassare Castiglione (1478–1529) was an Italian courtier and diplomat. He wrote 'Il Cortegiano' (The Courtier, 1528), which Burton cites in its Latin version, 'De aulico'. *Why cited:* Burton cites 'The Courtier' by book and folio, most likely for its discussions of love, women, courtly behaviour and conversation.

**98. David Chytraeus** (`chytraeus`): Chytraeus delit. Europae. (1.2.3.10-n23); Chytraeus Europ. delitiis. (2.3.2.1-n17); Chytraeus in Europae delitiis. (2.3.3.1-n76); Chytraeus (2.3.3.1-n85)
> Draft (claude-opus-5-5, authors-v1, 2026-11-02; low): David Chytraeus (1530–1600) was a Lutheran theologian and historian at Rostock. However, the work Burton cites, 'Variorum in Europa itinerum deliciae' (1594), a collection of inscriptions and epitaphs gathered on travels in Europe, was compiled by his brother Nathan Chytraeus (1543–1598). *Why cited:* Burton cites the 'Deliciae Europae' for inscriptions, epitaphs and similar curiosities from European towns.

**99. Marsilio Ficino (Ficinus)** (`ficino`): Lib. 1 cap. 6 de sanit. tuenda. (1.1.3.3-n4); Comment. in dial. Plat. de amore cap. 5. (1.2.1.2-n42); Marsilius Ficinus lib. 13 cap. 18 de theolog. Platonica. (1.2.3.2-n23); Lib. 1 cap. 7. (2.2.2.1-n16)
> Draft (claude-opus-5-5, authors-v1, 2026-11-02; high): Marsilio Ficino (1433–1499) was a Florentine Platonist philosopher and physician who translated Plato into Latin. His works include 'De vita libri tres' (1489), whose first book deals with keeping scholars healthy; a commentary on Plato's 'Symposium' on love ('De amore'); and the 'Theologia Platonica'. *Why cited:* Burton uses him as an authority on the melancholy of scholars and how to preserve their health, and on Platonic ideas of love.

**100. Heliodorus of Emesa** (`heliodorus`): Heliodorus. (2.3.7.1-n22); Heliodor. lib. 1. (3.2.2.2-n33); Aethiop. lib. 3. (3.2.2.2-n40); Lib. 3. (3.2.2.2-n44)
> Draft (claude-opus-5-5, authors-v1, 2026-11-02; high): Heliodorus of Emesa was a Greek novelist, probably of the third or fourth century AD. He wrote the 'Aethiopica', a romance about the lovers Theagenes and Chariclea. *Why cited:* Burton cites the 'Aethiopica' by book, most likely for examples of passionate love and its effects.

