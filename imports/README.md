# Hansard files downloaded by hand

Drop Hansard files here when a parliament's website blocks the scanner, then run `make import-folder`.
They go through the same pipeline as scanned days (marked `manual`, de-duplicated by hash), and a later
scan of the same day hands over without duplicates.

**Tasmania** — keep the names the Parliament's document search gives its downloads, anywhere in this folder:

    imports/HA Tuesday 1 September 2026.docx
    imports/LC Tuesday 1 September 2026.docx

From https://search.parliament.tas.gov.au: choose 2026, open a sitting day, and download the Word
document for each house. The Word (.docx) version is the one the Tasmanian reader reads today.

**Any other parliament** — one folder per chamber, each file named by its sitting date:

    imports/VIC-LA/2026-09-24.pdf
    imports/WA-LC/2026-06-09.pdf

Victoria, South Australia and Western Australia still need their readers written against a first real
file, so for those, send one file first.

To add files without git: on GitHub, open this folder on the `claude/hansard-watch-app` branch, choose
**Add file → Upload files**, drop them in, and commit.
