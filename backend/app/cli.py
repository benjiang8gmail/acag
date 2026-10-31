"""Small admin commands used by the Makefile."""

import getpass
import secrets
import sys

from .auth import hash_password


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "secret":
        print(secrets.token_urlsafe(48))
    elif cmd == "hash-password":
        pw = getpass.getpass("New password: ")
        if not pw or pw != getpass.getpass("Repeat: "):
            sys.exit("Passwords were empty or didn't match.")
        print(hash_password(pw))
    elif cmd in ("scan", "backfill"):
        # The same command does both: with no watermark a source backfills
        # BACKFILL_MONTHS; after that it only picks up what is new (§8).
        import json

        from .main import migrate
        from pipeline.sync import run_scan

        migrate()
        run = run_scan(trigger="cli")
        print(f"Scan {run.id}: {run.status}")
        if not run.per_source_json:
            print("No enabled sources. Sources are enabled in config/sources.yaml once their "
                  "connector passes its real-fixture tests (docs/sources.md).")
        for sid, c in run.per_source_json.items():
            print(f"  {sid}: {json.dumps(c)}")
    elif cmd in ("import", "import-folder"):
        # Manual import (spec §9.11), for parliaments whose sites block the scanner:
        #   import SOURCE_ID YYYY-MM-DD FILE [URL]   e.g. import VIC-LA 2026-09-24 ~/Downloads/hansard.pdf
        #   import-folder DIR                        with files laid out as DIR/VIC-LA/2026-09-24.pdf
        import json
        from datetime import date
        from pathlib import Path

        from .main import migrate
        from pipeline.sync import import_document, import_folder

        migrate()
        args = sys.argv[2:]
        try:
            if cmd == "import":
                if len(args) not in (3, 4):
                    sys.exit("usage: python -m app.cli import SOURCE_ID YYYY-MM-DD FILE [URL]")
                results = [import_document(args[0], date.fromisoformat(args[1]), Path(args[2]).expanduser(),
                                           url=args[3] if len(args) == 4 else None)]
            else:
                if len(args) != 1:
                    sys.exit("usage: python -m app.cli import-folder DIR")
                results = import_folder(Path(args[0]).expanduser())
        except ValueError as e:
            sys.exit(str(e))
        for r in results:
            print(json.dumps(r))
        if not results:
            print("Nothing to import: expected DIR/<SOURCE_ID>/<YYYY-MM-DD>.pdf (or .xml, .docx, .html, .json, .txt).")
    elif cmd == "sides":
        from .main import migrate
        from pipeline.sync import recompute_sides

        migrate()
        print(f"Updated party or speaker side on {recompute_sides()} speeches.")
    else:
        sys.exit("usage: python -m app.cli secret|hash-password|scan|backfill|import|import-folder|sides")


if __name__ == "__main__":
    main()
