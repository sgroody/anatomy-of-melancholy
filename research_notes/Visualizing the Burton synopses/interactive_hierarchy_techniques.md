# Interactive visualization techniques for deep, wide, text-heavy hierarchies (candidates for Burton's synopses)

Scope: Burton's synopses are brace trees of 4–8 levels with about 150–250 nodes each. Nodes are phrases or whole sentences, and some link to chapters. The target is an offline, static HTML/JS edition. These notes survey candidate techniques, the HCI evidence for them, libraries, and implementation details. Claims marked "Inference" are my reasoning or general web-platform knowledge and are not sourced here.

Three papers were downloaded as PDFs and read in full (SpaceTree 2002, Kobsa 2004, DOITrees Revisited 2004). They were added to the Claude Downloads calibre library as books #17–#19. For the other studies only abstracts or summaries were seen, and this is noted where it applies.

---

## Q1. Which techniques suit long text labels and moderate size (~200 nodes) best, per HCI evidence?

### Takeaway
For long labels, the evidence points to **aligned, left-to-right text layouts**: the indented outline (Explorer-style tree) or a horizontal node-link tree with labels in vertical columns (SpaceTree/DOITree style). The indented outline is the most robust baseline. In head-to-head studies it is rarely beaten on speed or satisfaction and wins at lookup and returning to a known place. A horizontal node-link view does better at showing the path to a node and the overall topology, which matches the brace-diagram reading of the synopses. Radial, hyperbolic and space-filling techniques (sunburst, treemap, icicle) handle labels poorly: text is rotated, unaligned or squeezed into cells. They are a poor fit when every node is a sentence. Evidence is thin for exactly this case (≈200 sentence-length nodes, reading rather than search). No study found tests sentence-length labels directly.

### Cited Findings

**SpaceTree (Plaisant, Grosjean & Bederson, InfoVis 2002)**: node-link with dynamic expansion. The study is the closest analogue to a "brace tree that opens".
- Design: a conventional node-link tree that "adds dynamic rescaling of branches of the tree to best fit the available screen space, optimized camera movement, and the use of preview icons summarizing the topology of the branches that cannot be expanded". Unexpandable branches show as a triangle: shading = node count, height = depth, base = average width. Navigation is by clicking nodes or with arrow keys (siblings, ancestors, descendants). Search highlights hits, and a "prune" button shows only the paths to matches. Orientation is selectable: "the most space efficient orientation depends on the tree topology and the aspect ratios of the labels and the window." — [Plaisant et al. 2002, PDF](https://obj.umiacs.umd.edu/spacetree/2002-05.pdf)
- Design lessons from about 10 prototype iterations with users:
  - "Semantic zooming is preferred over geometric scaling (i.e. 'Make it readable or don't bother showing the nodes')." Continuous geometric zoom was "rejected bluntly" because only one level was readable at a time.
  - "Maximize the number of levels opened at any time": users resented opening one level at a time.
  - Decompose the animation into **trim, translate, grow**.
  - Maintain landmarks: the focus path is highlighted (blue), and the hovered node and its path are gold.
  - Allow zooming only by clicking nodes ("data-aware" controls). Free zoom left non-experts "rapidly lost in the fog of empty information space." — [Plaisant et al. 2002](https://obj.umiacs.umd.edu/spacetree/2002-05.pdf)
- Experiment design: 18 CS students, a within-subjects 3×7 design comparing Microsoft Explorer, a hyperbolic browser and SpaceTree, on a tree of more than 7,000 nodes at a 1024×768 window. — [Plaisant et al. 2002](https://obj.umiacs.umd.edu/spacetree/2002-05.pdf)
- Results (mean seconds, E/H/S):
  - First-time node finding: mostly not significant. Explorer beat Hyperbolic on task 1 (10.5/13.2/11.1), and SpaceTree beat Explorer on task 3 (11.3/5.6/4.7).
  - Returning to a visited node (long trip): Explorer fastest, SpaceTree faster than Hyperbolic (6.5/22.7/15). Explorer was helped by keeping several branches open. The hyperbolic layout moves nodes between visits, while SpaceTree's relative positions stay consistent.
  - Listing a node's ancestors: SpaceTree significantly faster than Explorer (11.4/9.3/6.8). Two Explorer users made "alignment problems" errors because "the small offset makes it hard to separate siblings from parents."
  - Topology overview (which branch is bigger): 12/18 errors with Explorer, 10 with Hyperbolic, 2 with SpaceTree.
  - Preference: no significant difference in "future use" (5.9/5.1/6.2 on a 9-point scale). Explorer was rated less "cool".
  - Users misread the triangle encoding until it was explained. — [Plaisant et al. 2002](https://obj.umiacs.umd.edu/spacetree/2002-05.pdf)
- On label readability the authors say of the hyperbolic browser that "Labels are hard to browse because they are not aligned and sometimes overlap," and that its constant redrawing "can be distracting". SpaceTree's advantage was hypothesised to come from "the alignment of the labels, allowing faster scanning". — [Plaisant et al. 2002](https://obj.umiacs.umd.edu/spacetree/2002-05.pdf)

**Kobsa, "User Experiments with Tree Visualization Systems" (InfoVis 2004)**: 48 students, between-subjects, five systems plus Windows Explorer, 15 tasks on a directory tree.
- Speed: Windows Explorer and Treemap were fastest (101.2 and 106.5 s per task). BeamTrees was slowest (188.4 s).
- Correctness: Treemap was highest (73.3 %), BeamTrees (40.8 %) and Tree Viewer (41.7 %) lowest. Timeouts were lowest for Treemap (8.1 %) and Explorer (10 %).
- Treemap "does not surpass the baseline system Windows Explorer", and its satisfaction ratings "fell far short of Windows Explorer". Explorer was rated significantly higher than SequoiaView and Tree Viewer on "use system again".
- Star Tree (the hyperbolic browser) was "average". Users "overlooked subtrees and files" when rotating the tree to scan the leaf level, and asked for node counts because the fisheye "made a manual count difficult". — [Kobsa 2004, PDF](https://ics.uci.edu/~kobsa/papers/2004-InfoVis-kobsa.pdf)
- Users of Tree Viewer (3-D botanical tree) kept switching to its Explorer-like side panel, partly because "there was no direct link from the visualization into the Explorer hierarchy but only in the opposite direction". This is direct evidence that visualization and outline must be **linked both ways**. — [Kobsa 2004](https://ics.uci.edu/~kobsa/papers/2004-InfoVis-kobsa.pdf)

**Hyperbolic tree and "information scent" (Pirolli, Card & Van Der Wege, ACM TOCHI 2003)**
- The hyperbolic browser was faster on tasks where labels gave strong cues (high "accuracy of scent"). On weak-scent tasks the Windows file browser was faster. Crowding in the compressed periphery narrows the attention spotlight. *(Abstract and secondary summaries only.)* — [dblp record](https://dblp.uni-trier.de/rec/journals/tochi/PirolliCW03.html); [secondary summary, SIGIA-L](https://asist-archive.ischool.illinois.edu/sigia-l/2007-May/019944.html)
- In the CHI'97 "browse-off", the Explorer TreeView beat hyperbolic and treemap entries for file-management tasks. The hyperbolic browser was better at keeping global/local focus, and the TreeView better at "tracking where you had been". *(Secondary source.)* — [Kobsa 2004 related-work summary as surfaced via search](https://ics.uci.edu/~kobsa/papers/2004-InfoVis-kobsa.pdf)

**Indented list vs node-link (ontology studies)**
- Fu, Noy & Storey, "Indented Tree or Graph?" (ISWC 2013). The indented tree was easier for novices to follow ("more organized and familiar"). The graph was judged more controllable and intuitive, with less visual redundancy, especially under multiple inheritance (not relevant to Burton's strict trees). *(Abstract only.)* — [Springer](https://link.springer.com/doi/10.1007/978-3-642-41335-3_8)
- Eye-tracking follow-up (Fu, Noy, Storey, Semantic Web Journal): "indented lists are more efficient at supporting information searches and graphs are more efficient at supporting information processing." *(Abstract only.)* — [SWJ](https://www.semantic-web-journal.net/content/eye-tracking-user-experience-evaluation-ontology-visualization-techniques-0)
- Indented Pixel Tree Plots (Burch et al. 2010; 30 subjects) were as accurate and fast as node-link diagrams on three typical tasks. *(Abstract only.)* — [Springer Professional](https://www.springerprofessional.de/indented-pixel-tree-plots/3565402)

**Space-filling (sunburst vs treemap)**
- Stasko, Catrambone, Guzdial & McDonald (IJHCS 2000): two studies. Sunburst was as good as or better than Treemap on accuracy and time, especially at first use, and was strongly preferred for conveying structure. But "in large hierarchies, peripheral files are tiny and hard to tell apart". *(Abstract and slides.)* — [paper PDF](https://faculty.cc.gatech.edu/~john.stasko/papers/ijhcs00.pdf); [project page](https://sites.cc.gatech.edu/gvu/ii/sunburst)
- These studies use file trees whose labels are short names and whose tasks concern size and attributes. Kobsa's Treemap advantage came from "rich color coding and filtering", neither of which matters for the synopses. — [Kobsa 2004](https://ics.uci.edu/~kobsa/papers/2004-InfoVis-kobsa.pdf)

**Degree-of-interest trees (Card & Nation, AVI 2002; Heer & Card, AVI 2004)**
- DOITrees combine "logical filtering of nodes, using the estimated degree-of-interest to determine which nodes to display; geometric distortion…; semantic zooming of content based on node size; and aggregate representations of elided subtrees", to fit a bounded space. — [Heer & Card 2004, PDF](https://homes.cs.washington.edu/~jheer/files/2004-DOITree-AVI.pdf)
- The 2004 version is "a top-down node-link representation of the tree, optimized for the display of largely textual data". Orientation can be switched with one keystroke (top-down, bottom-up, left-right or right-left). — [Heer & Card 2004](https://homes.cs.washington.edu/~jheer/files/2004-DOITree-AVI.pdf)
- DOI = a multi-focal version of Furnas's fisheye: focus nodes and their ancestors get maximal interest, which falls off linearly with distance. Nodes below a threshold are elided into an aggregate glyph showing the size of the hidden subtree. — [Heer & Card 2004](https://homes.cs.washington.edu/~jheer/files/2004-DOITree-AVI.pdf)
- No user study is reported in the 2004 paper (it is an algorithms/system paper). The original paper is Card & Nation, "Degree-of-interest trees: a component of an attention-reactive user interface", AVI 2002. Its full text was not retrieved. — [Heer & Card 2003 CHI (cites it)](https://homes.cs.washington.edu/~jheer/files/2003-InterestEstimation-CHI.pdf)

**Miller columns / drill-down / narrow screens**
- Miller columns keep several levels visible so the user "can see where they are". On narrow screens they reduce to a one-column drill-down (iPod-style). — [Wikipedia: Miller columns](https://en.wikipedia.org/wiki/Miller_columns)
- Expandable indexes keep the whole hierarchy in view, while sequential menus "do not display the full hierarchical context as they drop down to deeper levels". (Zaphiris, Shneiderman & Norman, desktop web.) — [Zaphiris et al. 2002 PDF](https://www.cs.umd.edu/users/ben/papers/Zaphiris2002Expandable.pdf)
- Design-system guidance: avoid tree views "in a drawer or section with restricted width, as the nested layers for child tree items require width to expand into". — [UK ICDS tree view](https://design.sis.gov.uk/components/tree-view)
- No controlled study of Miller columns against trees on mobile was found.

**Animation and orientation**
- Bederson & Boltman (InfoVis 1999): animated viewpoint changes in a zoomable UI improved users' ability to reconstruct the information space, with no penalty on task time. *(Abstract.)* — [UMD DRUM](https://drum.lib.umd.edu/handle/1903/984)

### Inferences
- **Fit to the synopses.** Burton's synopses are already left-to-right brace trees: the root is on the left, and each brace opens rightwards into its members. A horizontal node-link tree (d3.tree/flextree, SpaceTree-like) is the closest interactive analogue. An indented outline is the same structure rotated 90° and loses the brace look, but it is the most robust for long text, narrow screens, keyboard, screen reader and print. The evidence (SpaceTree, Kobsa, Fu et al.) does not support choosing one over the other outright. It supports offering **both, linked**.
- **Width at full depth.** At 4–8 levels with sentence labels, a horizontal tree at full depth needs about 8 label columns. Inference: at about 220–300 px per wrapped column that is ~1,800–2,400 px. Desktop needs SpaceTree-style partial expansion (open as many levels as fit) or horizontal pan. Phones cannot show it legibly at all.
- **Long labels change the evidence base.** The studies used short labels (file names, taxa), and sentence labels make the label-alignment argument stronger. Radial, hyperbolic, sunburst, icicle and treemap layouts must rotate, truncate or tiny-ify text. They suit an overview thumbnail or minimap (shape and size of each Partition), not reading.
- **Icicle (a rectangular partition laid left to right)** is the one space-filling layout that keeps horizontal, aligned text and reads like a brace table (a depth column per level, each node a box spanning its descendants' height). It could work as a compact overview where each box shows the first words and the full text appears on focus. It is closer to Burton's printed table than a sunburst is. No study was found on icicles with long labels.
- **Treat SpaceTree's triangle glyph with care.** Users misread it. For Burton a simpler collapsed-branch cue is safer, such as "+12" (descendant count) or a miniature brace.
- **Hyperbolic and fisheye views are contra-indicated** for a reading edition: positions move between visits, which hurts "return to" tasks (22.7 s vs 6.5 s), and labels are unaligned.

### Gaps
- No study found tests **sentence-length node labels**. All the cited studies use short labels.
- Full results of Fu et al. 2013, Pirolli et al. 2003 and Stasko et al. 2000 were not read (abstracts only).
- No NN/g article specifically on tree views was found. A search returned design-system guidance instead (PatternFly, ICDS, Primer, Microsoft).
- No evidence was found on icicle-plot readability, brace-diagram readability, or "sideways" reading trees as such.
- No mobile-specific controlled study of hierarchy browsers was found.

---

## Q2. Which JS libraries or examples suit a dependency-light static site, and what are their size and licence?

### Takeaway
The lightest credible stack is **d3-hierarchy** (ISC, ~5.6 kB gzipped) for layout, or **d3-flextree** (WTFPL, O(n), variable node sizes) when wrapped labels give nodes different heights. Rendering can be plain SVG or absolutely positioned HTML, with no other D3 modules needed. **markmap** (MIT) is a ready-made collapsible left-to-right tree, but it pulls in full d3 v7 and expects Markdown/mind-map semantics. **elkjs** (EPL-2.0) is a heavyweight general graph-layout engine, overkill for strict trees. An indented outline needs no library: nested `<ul>`/`<details>` plus CSS draws the guides and braces.

### Cited Findings
- **d3.tree** implements the Reingold–Tilford "tidy" algorithm, improved by Buchheim et al. to run in linear time. Tidy trees are "typically more compact than dendrograms" (`d3.cluster`). `tree.nodeSize([w,h])` gives every node the **same** fixed spacing, `tree.size()` fits the tree to an extent, and `separation(a,b)` defaults to 1 for siblings and 2 for cousins. The examples are `@d3/tidy-tree` and `@d3/radial-tidy-tree`. — [d3js.org d3-hierarchy/tree](https://d3js.org/d3-hierarchy/tree)
- **d3-hierarchy** v3.1.3: 14.5 kB minified, 5.6 kB minified+gzipped — [Bundlephobia](https://bundlephobia.com/package/d3-hierarchy). License ISC (v3.1.2 package.json) — [jsDelivr package.json](https://cdn.jsdelivr.net/npm/d3-hierarchy@3.1.2/package.json)
- **d3-flextree**: "a more general version of the D3 tree layout module. Unlike tree, this plugin allows for nodes of variable sizes; like tree, the algorithm is fast, running in O(n) time". Node size comes from an accessor (e.g. `nodeSize: node => node.data.slice(0,2)`) with a custom `spacing`. It is based on van der Ploeg, "Drawing non-layered tidy trees in linear time" (Software: Practice and Experience; dated 2013 or 2014 depending on the source). — [d3-flextree README (unpkg)](https://unpkg.com/browse/d3-flextree@2.1.1/README.md); [GitHub Klortho/d3-flextree](https://github.com/Klortho/d3-flextree)
- d3-flextree 2.1.2: license **WTFPL**, single runtime dependency `d3-hierarchy ^1.1.5` (an old major version). — [jsDelivr package.json](https://cdn.jsdelivr.net/npm/d3-flextree@2.1.2/package.json)
- **markmap**: "Headings and list items become branches you can fold, zoom and pan". MIT licence. It is split into scoped packages (`@markmap/parse`, `@markmap/view`, `@markmap/toolbar`, …), with "an SVG renderer for most maps and a canvas renderer for very large ones". — [GitHub markmap/markmap](https://github.com/markmap/markmap)
- markmap-view 0.17.2: MIT. Depends on **d3 ^7.8.5 (the full bundle)** and **d3-flextree ^2.1.2**, which shows flextree is the established way to lay out variable-height text nodes. — [jsDelivr package.json](https://cdn.jsdelivr.net/npm/markmap-view@0.17.2/package.json)
- **elkjs** 0.9.3: license EPL-2.0 (one third-party listing says "EPL-2.0 OR GPL-3.0-or-later"). Browser builds are `lib/elk.bundled.js` or `lib/elk-api.js` plus a worker. Algorithms include layered, mrtree (tree), radial, stress, force and rectpacking. — [jsDelivr package.json](https://cdn.jsdelivr.net/npm/elkjs@0.9.3/package.json); [elkjs README](https://cdn.jsdelivr.net/npm/elkjs@0.12.0/README.md); [Snyk](https://dev.snyk.io/advisor/npm-package/elkjs)
- elkjs bundle size: a reliable minified/gzipped figure was not found. One older package-install figure is 8.14 MB, and users report that "bundle size is very big due to elkjs". *(Anecdotal.)* — [reaflow issue #224](https://www.github.com/reaviz/reaflow/issues/224); [socket.dev](https://socket.dev/npm/package/elkjs)
- **treevis.net** (Hans-Jörg Schulz) is a hand-curated visual bibliography of almost 300 tree-visualization techniques, filterable by dimensionality, edge representation and node alignment. It is the best index for finding further brace- or bracket-like layouts. — [treevis.net](https://treevis.net); [Schulz, IEEE CG&A 2011](https://www.pubmed.gov/24808254/)
- Design systems ship accessible outline-style tree views (PatternFly, Primer, ICDS, Microsoft guidance). — [PatternFly](https://patternfly.org/components/tree-view/design-guidelines); [Primer](https://primer.style/product/components/tree-view/guidelines); [Microsoft Win32 UX guide](https://learn.microsoft.com/en-ie/Windows/Win32/uxguide/ctrl-tree-views)

### Inferences
**Recommended stack for an offline static build (inference)**
- Precompute the layout at **build time** in Python or Node where possible, and ship positions in JSON or inline SVG. The page then needs no layout library at all, and the tree renders with JS disabled, prints, and loads instantly.
- If client-side layout is needed (expand/collapse re-layout), vendor `d3-hierarchy` (ISC, ~6 kB gz), or `d3-flextree` for variable heights.
- d3-flextree pins d3-hierarchy v1. Inference: check that it works with v3, or vendor the ~1 kB algorithm itself. Its WTFPL licence is permissive, but some organisations dislike it. Mention this in the edition's licence notes.
- Animated transitions can be done with CSS transitions on `transform` or with WAAPI, without d3-transition, d3-selection or d3-zoom. If pan/zoom is needed, `d3-zoom` (ISC) is the standard. A native scroll container with `scroll-snap`/`scrollIntoView` gives most of the benefit with better accessibility.

**Wrapped labels (inference, general web-platform knowledge)**
- SVG `<text>` does not wrap. The options are:
  - (a) measure and break into `<tspan>`s at build time;
  - (b) use `<foreignObject>` with HTML (markmap's HTML-in-SVG approach is common, but foreignObject has print and Safari quirks);
  - (c) render nodes as absolutely positioned HTML boxes and draw only the connectors/braces in an SVG underlay.
- Option (c) gives real text: selectable, searchable with Ctrl-F, screen-reader friendly, hyphenation, `lang` attributes for Latin. It fits this project's language-tagging rules (V4), which need `lang` on foreign-script runs. Measure each box's height after fonts load (`document.fonts.ready`), feed the heights to flextree, then position the boxes.

**Library fit (inference)**
- markmap is designed for Markdown mind maps. Its look (coloured curved branches) is not Burton's brace typography, and it costs full d3 (~90 kB gz, figure unverified here). Use it as a reference implementation (its flextree + fold + zoom code), not as the renderer.
- elkjs is not justified for a strict tree of about 200 nodes.
- Graphviz `dot` with `rankdir=LR` and record nodes could produce a **static** brace-like SVG at build time, but it gives no wrapping control. No source was checked here.

### Gaps
- An exact minified/gzipped size for elkjs and for current markmap bundles was not verified.
- It was not verified whether d3-flextree 2.x works with d3-hierarchy v3.
- The Observable `@d3/collapsible-tree` notebook could not be fetched (HTTP 429), so its transition details are unverified here.
- No dedicated library for **brace/bracket diagrams** (curly-brace connectors) was found. They would need to be drawn as custom SVG paths.

---

## Q3. How do good examples show "you are here" in a large hierarchy, and handle expansion without disorientation?

### Takeaway
The documented techniques are:
- keep the **ancestor path visible and highlighted** (SpaceTree's blue path, DOITree's breadcrumb trail);
- keep sibling order and relative positions **stable** between states;
- expand by **click on a node only**, opening as many levels as fit;
- animate in **staged, slow-in/slow-out steps** (SpaceTree: trim, translate, grow; DOITree: new nodes flow out of parents and are briefly highlighted);
- auto-centre on the focus node, and replace hidden subtrees with a **count or aggregate glyph**.

For accessibility the WAI-ARIA tree pattern supplies the keyboard model. For a navigation tree of links, a plain nested list of links is often simpler; that point is my inference and was not sourced.

### Cited Findings
- **Landmarks.** "As the tree is trimmed, expanded or translated it is crucial to maintain landmarks to help users remain oriented." The ancestor path of the current focus is highlighted in blue, and the node under the cursor and its path in gold. "When users click on a node, their eyes are already on the gold node, which remains gold as the tree is animated to a new layout, and then turns blue to reflect the new focus." — [Plaisant et al. 2002](https://obj.umiacs.umd.edu/spacetree/2002-05.pdf)
- **Stable positions.** "The constant relative position of siblings and the overall shape of upper tree help maintain the larger context… (Webbrain.com illustrates how changing the reorientation of siblings can be disorienting)." In the hyperbolic browser the same node ("kangaroo") appeared on the right and later on the left. Return trips took 22.7 s against 15 s for SpaceTree and 6.5 s for Explorer. — [Plaisant et al. 2002](https://obj.umiacs.umd.edu/spacetree/2002-05.pdf)
- **Staged animation.** On a new focus, SpaceTree "1) trims the tree of the branches that would overlap the new branch to be opened; 2) centers the trimmed tree so that the new branch will fit on the window, 3) grows the branch out of the new focus point". This drew "our most positive feedback". — [Plaisant et al. 2002](https://obj.umiacs.umd.edu/spacetree/2002-05.pdf)
- **DOITree transitions.** "a smooth, slow-in slow-out animation between tree configurations. Newly visible nodes flow out from their parents, while other previously visible nodes … [return] to their parents and fad[e] out … replaced by an elision graphic indicating the size of the unexpanded subtree. … newly visible nodes are initially highlighted. After the nodes reach their final positions this highlighting gently fades out." — [Heer & Card 2004](https://homes.cs.washington.edu/~jheer/files/2004-DOITree-AVI.pdf)
- **Breadcrumb for deep trees.** DOITrees support "automatic panning of the tree view, centered on the most recent user-selected focus node. To provide tree context, the visualization presents a 'bread-crumb' trail of ancestor nodes along the periphery… Clicking on such a node causes the view to translate and ancestors to 'fall' from the bread-crumb trail into their proper positions." — [Heer & Card 2004](https://homes.cs.washington.edu/~jheer/files/2004-DOITree-AVI.pdf)
- **Search as focus.** DOITree search hits light up, and aggregates light up if they contain hits. A filter slider runs from full fisheye, to "search results and their ancestors", to "search results and their least common ancestors". In SpaceTree, "prune" shows only the paths to matches. Hits are grayed rather than auto-trimmed, which "avoids constant and wild animation of the tree". — [Heer & Card 2004](https://homes.cs.washington.edu/~jheer/files/2004-DOITree-AVI.pdf); [Plaisant et al. 2002](https://obj.umiacs.umd.edu/spacetree/2002-05.pdf)
- **Curved edges.** "In our experience the use of curved edges helps offset the disorientation that can arise following tree paths through the limited display space." *(Designer opinion, not tested.)* — [Heer & Card 2004](https://homes.cs.washington.edu/~jheer/files/2004-DOITree-AVI.pdf)
- **Animation evidence.** Animated viewpoint transitions improved users' reconstruction of the space at no time cost. *(Bederson & Boltman 1999, abstract.)* — [UMD DRUM](https://drum.lib.umd.edu/handle/1903/984)
- **Keep multiple branches open.** Explorer's advantage on return trips came from "the ability to keep several branches opened". That advantage disappeared when other open branches pushed targets apart, which forced scrolling. — [Plaisant et al. 2002](https://obj.umiacs.umd.edu/spacetree/2002-05.pdf)
- **Two-way linking between views.** Users abandoned Tree Viewer's visualization for its outline panel, partly because there was no link from the visualization back to the outline. — [Kobsa 2004](https://ics.uci.edu/~kobsa/papers/2004-InfoVis-kobsa.pdf)
- **WAI-ARIA tree pattern (APG)**:
  - Keyboard:
    - Right opens a closed node, or moves to the first child if the node is open.
    - Left closes an open node, or moves to the parent.
    - Up/Down move between visible nodes.
    - Home/End go to the first/last node.
    - Enter performs the default action.
    - Type-ahead is recommended, "especially those with more than 7 root nodes".
    - `*` (optional) expands all siblings.
    - In horizontal trees Down acts as Right and Up as Left (`aria-orientation="horizontal"`).
  - Roles and states:
    - `tree`, `treeitem` and `group` roles.
    - `aria-expanded` only on parents.
    - `aria-level`/`aria-setsize`/`aria-posinset` when nodes are loaded dynamically.
    - The tree needs an accessible label.
    - Focus is either moved through the DOM or tracked with `aria-activedescendant`.
    - Focus must be visually distinct from selection.
  - The APG includes a "Navigation Treeview Example" whose items link to pages. — [W3C WAI-ARIA APG Tree View](https://www.w3.org/WAI/ARIA/apg/patterns/treeview/)

### Inferences (implementation notes for the Burton reader)

**Two linked views (inference)**
1. **Outline (default, all widths, print, screen readers).** Nested `<ol>`/`<ul>` where each node is a real text block. Draw the brace or bracket with CSS: a left border with curved end caps, or an inline SVG brace scaled to the group's height via `height:100%`. Indentation should be modest (about 1–1.25 em per level), so that 8 levels stay usable at 360 px. Vertical guide lines per level answer SpaceTree's finding that small offsets make siblings and parents hard to separate.
2. **Brace tree (wide screens).** A horizontal node-link or bracket layout from flextree, nodes as HTML boxes, braces as SVG paths. Open as many levels as fit (SpaceTree's rule) and summarise collapsed branches with a count ("+14"), not a triangle.

**Expansion without disorientation (inference)**
- Keep the clicked node's screen position fixed (anchor), as `scrollIntoView` does with a computed offset, or translate the canvas so the node stays put.
- Animate in stages, and honour `prefers-reduced-motion` (skip the animation and keep the anchor).
- Never reorder siblings.
- Briefly highlight newly revealed nodes, as DOITrees do.

**"You are here" from a chapter page (inference)**
- Show a breadcrumb of the synopsis path at the top of each unit page (e.g. *Partition 1 › Sect. 2 › Memb. 3 › Subs. 4*), each crumb linking to that node in the synopsis.
- On the synopsis page, `#node-id` targets plus `:target` styling highlight the node, open its ancestors, and colour the ancestor path (SpaceTree's blue path).
- A "locate in synopsis" link from every chapter heading gives the round trip that Kobsa's Tree Viewer lacked. Nodes that link to chapters should look like links (underline or arrow), distinct from structural nodes.

**Keyboard and screen reader (inference)**
- If the outline uses `<details>/<summary>` or plain nested lists of links, native semantics may be better than `role="tree"`: ARIA trees change screen-reader mode and are often discouraged for site navigation. This was not sourced in this round; verify against current accessibility guidance (for example Adrian Roselli or WebAIM) before choosing.
- If `role="tree"` is used, implement the full APG keyboard model, including type-ahead and `*`. Use `aria-current="location"` on the node for the current chapter.

**Mobile (inference)**
- Below about 700 px, show only the outline. Possibly offer a "drill-down" mode (one level per screen with a breadcrumb, Miller columns collapsed to one column) for the deepest branches. Avoid pinch-zoom canvases for text.

**Print (inference)**
- The outline prints naturally: expand everything in `@media print`, use `break-inside: avoid` on small groups, and hide the controls.
- A full-depth brace tree will not fit a page legibly. Offer a per-Partition landscape print, or one page per top-level branch.

**Overview or minimap (inference)**
- A small icicle or "shape of the tree" thumbnail without labels can serve as the minimap. Highlight the current branch in it and make each region clickable, as treemaps and sunbursts do for structure, without asking them to carry text.

### Gaps
- No controlled evidence was found on the **anchoring** strategy for expand/collapse (keeping the clicked node fixed against re-centring) beyond SpaceTree's design feedback and DOITree's description.
- No evidence was found on breadcrumbs specifically for deep **document** hierarchies. The DOITree breadcrumb is a design description, not a tested feature.
- Accessibility guidance on `role="tree"` versus nested link lists for navigation was not fetched in this round.
- Print handling of interactive trees is unsourced (inference only).
