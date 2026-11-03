@echo off
rem Opens the private reading edition of Burton's Anatomy of Melancholy in the default browser.
rem It serves site\private (built by `uv run burton build --all`) on this computer only; close this window to stop.
cd /d "%~dp0"
title The Anatomy of Melancholy (local edition)
uv run burton serve --profile private --port 8765 --open
