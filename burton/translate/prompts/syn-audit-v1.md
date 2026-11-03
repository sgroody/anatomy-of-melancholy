You are checking the structure of a synopsis in Robert Burton's *The Anatomy of Melancholy* (1651) for a scholarly digital edition. A synopsis is a tree drawn with curly braces: a heading on the left, a brace, and the items the brace groups on its right; any item can carry its own brace in turn.

You get one image of a synopsis sheet and the list of every text string printed on that sheet, each with an id. The words of the list match the image; only the order of the list is unreliable.

For each item you are asked about, find it on the image and name its **parent**: the id of the string from which the brace that contains the item hangs (the text just left of that brace's point).
- Answer `root` if the item is itself the leftmost heading of a tree on this sheet (nothing hangs it from the left).
- Answer `elsewhere` if the brace that contains it starts on another sheet (the item continues a brace whose heading is not on this image).
- Some strings are not parents: the connectors "or"/"Or" set between alternatives, a cross-key sign standing alone above a heading (♈, A, B. …), and a column heading such as "Memb." or "Subsect." printed above a list. Name the text the brace hangs from, never these.
- If the item is itself such a column heading or a label printed under another string as part of the same block, name the parent of that block.

Give a one-sentence `reason` that says what you see (e.g. "under the brace beside 'Natural'") and a `confidence` of high, medium or low. Return exactly one answer per item, with the same `id`.
