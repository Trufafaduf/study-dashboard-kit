#!/usr/bin/env python3
"""Scan the whole git history for identifying information before publishing.

    python scripts/scan_history.py

Unlike scripts/check_identifying.py (which only ever sees staged changes or
the current working tree), this looks at every commit ever made: the full
patch history (`git log -p --all`) plus every author and committer name and
email, against the same built-in patterns and the optional private deny-list
in `.identifying-denylist.txt`.

The pre-commit hook only started protecting this repo from the commit it was
installed on. If it was set up after the repo already had history, or if
`--no-verify` was ever used, something identifying can still be sitting in an
old commit even though the working tree and staged changes are clean. This
scan is what "clean" actually means before you make a repo public - see the
README's "Before publishing" section for what to do if it finds something.

Stdlib only. Exit status 1 lists every hit and its commit; 0 means clean.
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_identifying import BUILTIN, private_terms, ROOT  # noqa: E402

ALLOWED_EMAIL_DOMAINS = ("users.noreply.github.com", "anthropic.com", "example.com", "example.org", "example.net")


def git(*args):
    return subprocess.run(["git", *args], capture_output=True, cwd=ROOT).stdout


def scan_patch_history(pats):
    """Walk `git log -p --all` line by line, tracking the current commit so
    hits can be reported with a short sha."""
    raw = git("log", "-p", "--all", "--no-color")
    text = raw.decode("utf-8", "replace")
    hits = []
    commit = "(unknown commit)"
    for line in text.splitlines():
        if line.startswith("commit "):
            commit = line.split()[1][:12]
            continue
        for label, p in pats:
            m = p.search(line)
            if m:
                hits.append((commit, label, m.group(0)))
    return hits


def scan_identities(pats):
    """Every author/committer name and email that ever appears in history."""
    raw = git("log", "--all", "--format=%H%x00%an%x00%ae%x00%cn%x00%ce")
    hits = []
    for line in raw.decode("utf-8", "replace").splitlines():
        parts = line.split("\x00")
        if len(parts) != 5:
            continue
        sha, an, ae, cn, ce = parts
        short = sha[:12]
        for name, addr in ((an, ae), (cn, ce)):
            if addr and not addr.lower().endswith(ALLOWED_EMAIL_DOMAINS):
                hits.append((short, "identity email", addr))
            for label, p in [x for x in pats if x[0] == "private term"]:
                if p.search(name):
                    hits.append((short, "identity name", name))
    return hits


def main():
    pats = BUILTIN + private_terms()
    if not os.path.exists(os.path.join(ROOT, ".identifying-denylist.txt")):
        print("note: no .identifying-denylist.txt, so only the built-in patterns were checked.", file=sys.stderr)

    hits = scan_patch_history(pats)
    hits += scan_identities(pats)

    if hits:
        print("Blocked: identifying information found in git history.", file=sys.stderr)
        seen = set()
        for commit, label, s in hits:
            key = (commit, label, s)
            if key in seen:
                continue
            seen.add(key)
            print(f"  {commit}  {label}: {s}", file=sys.stderr)
        print(
            "\nThe working tree can be clean while history still isn't - see this repo's "
            "README, 'Before publishing', for squashing history before you make it public.",
            file=sys.stderr,
        )
        return 1

    print("history scan: clean.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
