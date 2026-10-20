# Survey scripts

Throwaway inspection scripts used to produce the counts in `../../SURVEY.md`.
They read an unzipped copy of the EPUB (pass the path to `EPUB/xhtml`).
Python is not installed on this machine yet, so they were run with Calibre's bundled interpreter:

    calibre-debug -e survey/scripts/inspect1.py <unzipped>/EPUB/xhtml

They are not part of the pipeline. M1 replaces them with `burton/ingest` and `burton/verify`.
