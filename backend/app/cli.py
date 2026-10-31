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
    else:
        sys.exit("usage: python -m app.cli secret|hash-password")


if __name__ == "__main__":
    main()
