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
    elif cmd == "sides":
        from .main import migrate
        from pipeline.sync import recompute_sides

        migrate()
        print(f"Updated party or speaker side on {recompute_sides()} speeches.")
    else:
        sys.exit("usage: python -m app.cli secret|hash-password|scan|backfill|sides")


if __name__ == "__main__":
    main()
