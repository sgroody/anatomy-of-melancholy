# Period design exemplars for an early modern reading edition (frontispiece + brace synopses)

Research notes, 2026-11-18. Scope: digital editions, exhibits and designed books that (a) make engraved title pages or frontispieces interactive, (b) present early modern diagrams, tables or synopses while keeping the printed look, and (c) pair an image-led front page with navigation into a long text.

Method note: several primary project pages refused automated fetching (c82.net returned HTTP 403 for the Byrne's Euclid making-of post, the Iconographic Encyclopaedia "about" page and the work pages; fastcompany.com returned 403; the UCSB Telar Leviathan page and ARTFL's frontispiece page returned 404 when fetched). Where that happened, the findings below rest on search-engine extracts of those pages or on press coverage, and are marked as such. I could not view screenshots directly, so "what it looks like" descriptions come from the projects' own text and from press write-ups, not from my own inspection.

## Which exemplars best combine period fidelity (engraving, rules, braces, rubrication, compartments) with modern interaction?

### Takeaway
Nicholas Rougeux's c82.net editions (Byrne's Euclid, Werner's Nomenclature of Colours, Heck's Iconographic Encyclopaedia) are the strongest exemplars: they redraw the printed originals as SVG in the period typeface and layout, then add a small number of conveniences (clickable hotspots on plates, thumbnail jump menus, cross-links). The ARTFL Encyclopédie's frontispiece paired with Diderot's "Explication du Frontispice" is the closest structural analogue to Burton's frontispiece plus his "Argument of the Frontispiece". No interactive treatment of Burton's own frontispiece or synopses was found.

### Cited Findings

**Byrne's Euclid (Nicholas Rougeux, December 2018), https://www.c82.net/euclid/**
- Rougeux redrew each of Byrne's 1847 diagrams in Illustrator from Internet Archive scans, then exported the SVG code for the web — summary of his "Making of Byrne's Euclid" post as quoted in search extracts — [c82.net blog, "Making of Byrne's Euclid"](https://www.c82.net/blog/?id=79) (page itself returned 403 to fetch; content via search extract); [Colossal](https://www.thisiscolossal.com/2019/02/byrnes-euclid/)
- The diagrams were traced so that dimensions and relationships stayed true to Euclid's geometry — [My Modern Met (search extract)](https://mymodernmet.com/byrnes-euclid-nicholas-rougeux)
- Fidelity choices reported: original spelling including the long s, Caslon type, styled initial capitals, and Byrne's own alternative designs for mathematical symbols. Rougeux's stated goal was to stay "as true as possible to its design" while adding "just a few conveniences" for modern readers — [My Modern Met (search extract)](https://mymodernmet.com/byrnes-euclid-nicholas-rougeux); [Open Culture](https://www.openculture.com/2018/12/a-beautifully-designed-edition-of-euclids-elements.html)
- Interaction: diagrams are clickable; each of Euclid's books has its own page; a dropdown lists every proof with a miniature diagram as its thumbnail, so readers jump to a proof by picture rather than by number — [Open Culture / search extract](https://www.openculture.com/2018/12/a-beautifully-designed-edition-of-euclids-elements.html); [FlowingData](https://flowingdata.com/2018/12/18/modern-reproduction-of-1847-geometry-books)
- Took about two months; a companion poster shows all 269 diagrams at once — [My Modern Met (search extract)](https://mymodernmet.com/byrnes-euclid-nicholas-rougeux)
- Press framing: "an interactive version of one of the first multicolor books" — [Hyperallergic](https://hyperallergic.com/483863/byrnes-euclid-nicholas-rougeux/)

**Werner's Nomenclature of Colours (Rougeux, September 2018), https://www.c82.net/werner**
- Built from free Internet Archive scans of the 1821 edition; readers can jump to any colour, see the other colours each description refers to, and view photographs of the animals, plants and minerals Werner cited — [Mental Floss](https://www.mentalfloss.com/science/interactive-version-classic-color-manual-used-charles-darwin-now-available-online); [Open Culture](https://www.openculture.com/2018/09/an-interactive-online-version-of-werners-nomenclature-of-colours.html)
- A long-scrolling page with an accordion per colour; added data visualisations of the colours. Sources disagree on the count (100 vs 110 colours) — [My Modern Met](https://mymodernmet.com/nomenclature-of-colours-online); [Fast Company](https://www.fastcompany.com/90239248/a-200-year-old-guide-to-color-redesigned-for-the-internet-age) (403 on fetch; via search extract)
- Fast Company described it as reframing the old nomenclature "with contemporary data visualization and web design" — [Fast Company (search extract)](https://www.fastcompany.com/90239248/a-200-year-old-guide-to-color-redesigned-for-the-internet-age)

**Iconographic Encyclopaedia (Rougeux, restoration of J. G. Heck's plates), https://www.c82.net/iconography/**
- The project's about page states that an overlay of hotspots was made for each plate, so that clicking a figure shows what it is and where it is mentioned in the text — [c82.net, Iconographic Encyclopaedia, about (search extract; 403 on fetch)](https://www.c82.net/iconography/about); [c82.net work page](https://www.c82.net/work?id=388)
- This is the clearest found example of an engraved plate with per-figure hotspots linked back into a long text.

**ARTFL Encyclopédie, frontispiece and "Explication du Frontispice"**
- The ARTFL Project (University of Chicago) presents the Encyclopédie's frontispiece (images from UChicago Special Collections) with Diderot's explanatory text; the explication names figures by position, e.g. the figures below the central group are Optics, Botany, Chemistry and Agriculture — [ARTFL node](https://encyclopedie.uchicago.edu/node/170); [ARTFL "Frontispice: explication" (404 on fetch; search extract)](https://encyclopedie.uchicago.edu/content/frontispice-explication)
- I could not confirm whether the figures in the image are clickable.
- ARTFL also serves its high-resolution images through IIIF (2024); its blog notes that some viewers such as Universal Viewer do not display annotations out of the box — [ARTFL blog](https://artfl.blogspot.com/2024/11/those-familiar-with-artfl-project-and.html)

**Ben Fry, "On the Origin of Species: The Preservation of Favoured Traces" (2009), https://benfry.com/traces/**
- Shows how Darwin's text changed across six editions (about 150,000 words in the first to about 190,000 in the sixth); built in Processing from the Darwin Online dataset; each edition's additions in its own colour; the piece was acquired by Cooper Hewitt in 2017 and later issued as a poster and book — [benfry.com](https://benfry.com/traces/); [Cooper Hewitt](https://www-4.collection.cooperhewitt.org/objects/1108751253); [Creative Applications](https://creativeapplications.net/processing/the-preservation-of-favoured-traces-processing); [FlowingData](https://flowingdata.com/2009/09/07/ben-fry-visualizes-the-evolution-of-darwins-ideas/)
- The project page lists a title graphic followed by six edition sections (1859–1872) and describes an earlier version that "simply depicts all six books in parallel" — [benfry.com](https://benfry.com/traces/)
- A critique (student blog, low authority) says it shows the data without separating trivial from conceptual changes — [Duke course blog](https://sites.duke.edu/lit80s_01_f2014/2014/09/21/partnered-critique/)
- Relevance: an overview-to-detail treatment of a whole long book at once; it is a modern data aesthetic, not a period one.

**British Library "Turning the Pages"**
- Page-turning viewer with "magnify", "text" (curatorial notes) and "audio" buttons per page; zoom, pan, rotate and annotations; maintained by Armadillo Systems and reported to open IIIF manifests. Sources disagree on the launch year (1997 per Wikipedia, 1998 per Wired) — [Wikipedia](https://en.wikipedia.org/wiki/Turning_the_Pages); [Wired 1998](https://wirednews.pages.dev/1998/04/a-new-interface-for-old-books); [AHA Perspectives 2007](https://www.historians.org/perspectives-article/experience-turning-the-pages-at-the-british-library-online-september-2007/); [AAHVRC blog 2009](https://aahvrc.blogspot.com/2009/10/turning-pages-at-british-library.html)
- Relevance: high period fidelity (the whole opening is a photograph), weak as a reading edition (text is not the primary layer).

### Inferences
- The c82 pattern (redraw in vector, period type, a few modern conveniences) suits Burton's synopses: they are typographic diagrams (braces, small caps, italics) and can be re-set as SVG/HTML that keeps the printed look but whose leaves are links. This is a closer fit than photographic page-turning.
- The Encyclopédie's frontispiece + Diderot's explication is the nearest structural twin of Burton's frontispiece + his verse "Argument of the Frontispiece" (ten stanzas, one per compartment). That suggests linking each compartment to its stanza, as ARTFL places the explication beside the image.

### Gaps
- No interactive digital treatment of the Anatomy's frontispiece or synopses was found. The Early Modern Science Omeka exhibit "Curing Melancholy" shows scans of a 1628-era copy (frontispiece, the synopsis before the Third Partition) with prose commentary but no zoom, hotspots or text links; every image links to one item record — [Omeka exhibit](https://earlymodernscience.omeka.net/exhibits/show/curingmelancholy/alookinsidetheanatomyofmelanch). Other static treatments: [NLM "Shakespeare and the Four Humors"](https://www.nlm.nih.gov/exhibition/shakespeare-and-the-four-humors/digitalgallery-nojs-detail023.html), [CRRS Toronto](https://crrs.library.utoronto.ca/exhibits/show/melancholy-and-the-humours/the-humours-and-medicine/the-anatomy-of-melancholy), [Wellcome digitised copy](https://wellcomecollection.org/works/yj9serrk).
- Not researched within the tool budget: Newton Project, Darwin Online's page design, Visible Prices, Map of Early Modern London, Bodleian and Folger digital exhibitions, Andrew Piper, Eric Gill/typographic exemplars, and design-press coverage (Eye, It's Nice That). The suggested "Digital Ramus" project was not found under that name.
- Precise visual details of c82 pages (colours, hover behaviour) could not be verified because the site blocked fetching.

## What design patterns recur (side-by-side image and text, hotspot compartments, rubricated navigation, fold-out reveal, overlay)?

### Takeaway
Five patterns recur: (1) facsimile and text side by side; (2) hotspot overlays on an engraving linking figures to text; (3) guided pan-and-zoom "stories" over one high-resolution image; (4) picture-based navigation (thumbnails of diagrams as the table of contents); (5) the whole work as one overview poster. Typographic re-setting of brace tables exists as a tool (LaTeX `schemata`) but no digital edition was found that makes a brace diagram navigable.

### Cited Findings
- **Side by side.** The Shelley-Godwin Archive's default page view aligns "side by side the page image and transcription", with metadata, colour-coded status and a vertical slider for moving across many pages; built on Shared Canvas and TEI genetic-editing vocabulary — [Using the Shelley-Godwin Archive](https://shelleygodwinarchive.org/using-the-archive/); [S-GA about](https://shelleygodwinarchive.org/about/); design issues in Muñoz & Viglianti, Journal of the TEI (2015) — [DOAJ record](https://doaj.org/article/2dbc144582c94175bc56a64690696fab)
- **Hotspot overlay on a plate.** Heck plates at c82: hotspot overlay per plate, click a figure to see what it is and where it appears in the text — [c82.net Iconography about (search extract)](https://www.c82.net/iconography/about)
- **Region targeting standard.** IIIF annotations follow the W3C annotation model (a Body annotating a Target), and region targeting uses selectors — the mechanism behind clickable regions on an image; an AnnotationList is usually tied to one canvas — [IIIF Presentation 2.1](https://iiif.io/api/presentation/2.1/); [overview](https://www.emergentmind.com/topics/iiif-compliant-annotations)
- **Guided zoom stories.** Exhibit (Mnemoscene with the University of St Andrews) is a IIIF storytelling tool: add text, zoom into images, guide the viewer through details, in scroll or slide format; Cogapp's Storiiies is a similar tool — [St Andrews museum blog](https://museumblog.wp.st-andrews.ac.uk/2022/11/14/a-guide-to-exhibit/); [Exhibit docs](https://exhibit.st-andrews.ac.uk/docs/iiif); [Storiiies at IIIF 2019](https://iiif.io/event/2019/goettingen/program/50)
- **Telar** (UCSB AMPL) has an object page for the Leviathan frontispiece with panels and glossary terms; whether regions are clickable was not confirmed (404 on fetch) — [Telar Leviathan (search result)](https://ampl.clair.ucsb.edu/telar/objects/leviathan)
- **Picture as table of contents.** Byrne's Euclid proof dropdown uses miniature diagrams as thumbnails — [FlowingData](https://flowingdata.com/2018/12/18/modern-reproduction-of-1847-geometry-books)
- **Whole-work overview.** Fry's Traces and Rougeux's Euclid poster (all 269 diagrams) present the entire work in one view — [benfry.com](https://benfry.com/traces/); [My Modern Met (search extract)](https://mymodernmet.com/byrnes-euclid-nicholas-rougeux)
- **Brace tables as a typographic form.** The LaTeX `schemata` package typesets outlines with braces "to illustrate the breakdown of concepts and categories" in scholastic and early modern texts, naming Ramus among its targets — [schemata documentation (PDF)](https://ftp.math.utah.edu/pub/texlive/Contents/live/texmf-dist/doc/generic/schemata/schemata.pdf)
- **Scholarship on the form.** Dichotomous (brace) tables were common in early modern English print across theology, science and philosophy, popularised by Ramus — [utupub.fi (Turku) PDF](https://www.utupub.fi/bitstreams/05077948-7d03-4577-88d3-3488aa1c7fa0/download); the publication history of Ramus's diagrams — [enssib, "Ramifier sa pensée" (PDF)](https://www.enssib.fr/bibliotheque-numerique/documents/71805-ramifier-sa-pensee-l-edition-des-diagrammes-de-pierre-de-la-ramee.pdf). The EModGraL project (Turku, 2021–25) classifies graphic devices in English print 1473–1700 (top level: image, diagram, table, unclear; about 25,300 devices in about 4,300 books by the halfway point) and has an article on braces in progress — [EModGraL project](https://blogit.utu.fi/emodgral/project/); [halfway milestone](https://blogit.utu.fi/emodgral/2023/10/09/halfway-milestone/)
- A 2024 Harvard dissertation (Ashley Gonik) studies how qualitative and quantitative tables were printed and used in Europe 1450–1700 — [Harvard DASH](https://dash.harvard.edu/entities/publication/f285907a-4fd5-4fbf-9415-98e9b8acb66c)

### Inferences
- "Rubricated navigation" and "fold-out reveal" did not appear as named patterns in the sources found. Fold-outs exist in print (Burton's synopses are full-page or folding tables in some editions), but no digital exemplar of a fold-out reveal was found.
- The patterns divide by what is primary: photograph-first (Turning the Pages, Omeka exhibits), text-first with facsimile beside (Shelley-Godwin), or redrawn-first (c82). A reading edition with a synopsis to navigate fits the redrawn-first model; the frontispiece, being an engraving, stays photograph-first with an overlay.

### Gaps
- No found digital edition renders a Ramist/brace synopsis as an interactive, expandable tree that keeps the printed braces. The `schemata` package is print-only.
- Specific Folger Collation posts on braces or tables were not found by search; the closest was a post on brevigraphs — [Folger Collation](https://www.folger.edu/blogs/collation/brevigraphs/).

## What specific ideas could transfer to showing a brace synopsis next to or within the frontispiece's compartments?

### Takeaway
The transferable ideas are: a hotspot overlay on the ten compartments (Heck/c82 model) linked to Burton's "Argument of the Frontispiece" stanzas (ARTFL model), and from each compartment to the synopsis branch it illustrates; the synopses re-set as vector braces whose leaves are links (Byrne model); and a guided zoom tour (Exhibit/Storiiies) as an optional entry. These are inferences from the exemplars; none is attested for Burton.

### Cited Findings
- The frontispiece's small frames show the causes and kinds of melancholy (solitude, love, madness, superstition and others) around a central author portrait, as described in a Burton exhibit — [Curing Melancholy, Omeka](https://earlymodernscience.omeka.net/exhibits/show/curingmelancholy/alookinsidetheanatomyofmelanch)
- Burton's synoptic tables map the three partitions, each with sections, members and subsections; the exhibit describes broad categories on the left and more specific terms running right — [Omeka exhibit](https://earlymodernscience.omeka.net/exhibits/show/curingmelancholy/alookinsidetheanatomyofmelanch); [she-philosopher.com Burton Pt 1](https://she-philosopher.com/library/burton_Pt1.html)
- Hotspot-per-figure linking to where the figure is mentioned in the text — [c82 Iconography (search extract)](https://www.c82.net/iconography/about)
- Image paired with its author's own explanation of the figures — [ARTFL](https://encyclopedie.uchicago.edu/node/170)
- Vector redrawing in the period typeface, plus thumbnail navigation — [Open Culture](https://www.openculture.com/2018/12/a-beautifully-designed-edition-of-euclids-elements.html)

### Inferences
- **Compartment → stanza → synopsis.** Each of the ten compartments gets a region (an SVG polygon over the engraving). Hover/focus shows its name (Zelotypia, Solitudo, …) and the matching stanza of the Argument; click opens the branch of the synopsis it illustrates (for instance Inamorato → the Third Partition's love-melancholy branch; Superstitiosus → religious melancholy; Hypochondriacus → the hypochondriacal species in Partition 1; borage and hellebore → the cures of Partition 2). The mapping must be stated by the edition, not invented by code; where the link between compartment and branch is interpretive, it should be labelled so.
- **Synopsis beside the frontispiece.** With the engraving large on the left, the right column can hold the synopsis re-set as HTML/SVG braces (period small caps and italics, thin rules), collapsed to the first level (the three Partitions). Choosing a compartment expands the relevant brace and highlights it, and the matching compartment outline lights in the engraving: a two-way link like Shelley-Godwin's image/text alignment, but between picture and diagram.
- **Braces as navigation.** Each leaf of the brace is a link to the subsection, as Byrne's thumbnails act as the table of contents. The brace keeps its printed shape at wide widths and falls back to an indented outline on phones.
- **Overview poster.** All three synopses on one long page (as Rougeux's 269-diagram poster or Fry's whole-book view) gives readers the whole structure at once.
- **Optional guided tour.** A short Exhibit/Storiiies-style sequence that pans across the compartments in the Argument's order. This is a secondary entry, not the default.
- **Restraint.** The c82 projects' stated rule ("a few conveniences") supports keeping hotspot outlines invisible until hover or focus, so the engraving reads as an engraving.

### Gaps
- No source confirms how other projects handle accessibility of image hotspots (keyboard focus order, accessible names); the edition will need its own design for this.
- Whether a compartment-to-synopsis mapping is attested in Burton scholarship was not researched here.
