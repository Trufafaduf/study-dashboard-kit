#!/usr/bin/env python3
"""Fresh-clone smoke test for study-dashboard-kit.

    python scripts/smoke_test.py

Clones this repo into a temp directory with a clean environment (no
BRAIN_ROOT, no brain.config.json, no private deny-list) and follows the
README literally:

  1. Copy brain.config.example.json -> brain.config.json (Setup step 2).
  2. Install the pre-commit hook (Setup step 4).
  3. Run every `python ...` command the README shows without a placeholder
     (<...>) in it - this is "Using it standalone" (build both example
     courses: the GEO 110 digital quiz + dashboard, the PHYS 105 paper
     dashboard) and the identifying-info scan.
  4. Check the expected build outputs exist and contain no leftover
     @@PLACEHOLDER@@ tokens.
  5. Run the same commands again and confirm the working tree is byte-for-byte
     unchanged (the builders are idempotent).
  6. Check that every concrete (non-templated) file path the README mentions
     in backticks actually exists in the repo.

Exits non-zero with a clear message on the first category of failure it
finds, after finishing the checks in that category (so you see everything
wrong at once, not just the first).

Stdlib only.
"""
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile

FAILURES = []


def fail(msg):
    FAILURES.append(msg)
    print(f"FAIL: {msg}", file=sys.stderr)


def ok(msg):
    print(f"ok: {msg}")


def run(cmd, cwd, env):
    r = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True)
    if r.returncode != 0:
        fail(
            f"command failed ({r.returncode}) in {cwd}: {' '.join(cmd)}\n"
            f"--- stdout ---\n{r.stdout}\n--- stderr ---\n{r.stderr}"
        )
    return r


def tree_hashes(root, skip=(".git",)):
    out = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in skip]
        for f in filenames:
            p = os.path.join(dirpath, f)
            rel = os.path.relpath(p, root).replace(os.sep, "/")
            with open(p, "rb") as fh:
                out[rel] = hashlib.sha256(fh.read()).hexdigest()
    return out


# Matches "python <script>.py [args...]" on a single line (fenced code block
# line, or inline code span with the backticks stripped first).
CMD_RE = re.compile(r"^python\s+([\w./\\-]+\.py)((?:\s+[\w./\\-]+)*)\s*$")

# Bare, non-templated repo-relative paths mentioned in backticks, used only
# as a soft cross-check (see check_readme_paths).
PATH_RE = re.compile(r"`([A-Za-z0-9_.][\w./-]*\.[A-Za-z0-9]+)`")


def readme_commands(readme_text):
    """Every distinct, non-templated `python <script>.py [args]` line in the
    README, from fenced code blocks and inline code spans alike."""
    lines = []
    for block in re.findall(r"```[^\n]*\n(.*?)```", readme_text, flags=re.S):
        lines += block.splitlines()
    lines += re.findall(r"`([^`\n]+)`", readme_text)  # inline code spans

    cmds, seen = [], set()
    for line in lines:
        m = CMD_RE.match(line.strip())
        if not m:
            continue
        script, args = m.group(1), m.group(2).split()
        full = "python " + script + (" " + " ".join(args) if args else "")
        if "<" in full or ">" in full:
            continue  # templated example, e.g. specs/<course>-<exam>.json
        if full in seen:
            continue
        seen.add(full)
        cmds.append([sys.executable, script] + args)
    return cmds


def check_command_paths(clone, cmds):
    for cmd in cmds:
        script = cmd[1]
        if not os.path.exists(os.path.join(clone, script)):
            fail(f"README command references a script that doesn't exist: {script}")
        for arg in cmd[2:]:
            if arg.startswith("-"):
                continue
            if "/" in arg or "\\" in arg:
                if not os.path.exists(os.path.join(clone, arg)):
                    fail(f"README command references a path that doesn't exist: {arg}")


def check_readme_paths(clone, readme_text):
    """Soft check: every dotted, slashed path in backticks that looks like a
    real repo file should exist. Skips bare field names (no dot) and anything
    with no path separator, which are usually spec/JSON field names, not
    files."""
    missing = []
    for m in PATH_RE.finditer(readme_text):
        rel = m.group(1)
        if "/" not in rel:
            continue  # a bare filename.ext in prose isn't necessarily a repo path
        if not os.path.exists(os.path.join(clone, rel)):
            missing.append(rel)
    if missing:
        print(f"note: README mentions paths not found in the repo (informational): {sorted(set(missing))}")


def main():
    repo_root = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=True
    ).stdout.strip()

    tmp = tempfile.mkdtemp(prefix="sdk-smoke-")
    clone = os.path.join(tmp, "study-dashboard-kit")
    print(f"cloning {repo_root} -> {clone}")
    subprocess.run(["git", "clone", "-q", repo_root, clone], check=True)

    if os.path.exists(os.path.join(clone, "brain.config.json")):
        fail("fresh clone already has brain.config.json (should be gitignored)")
    if os.path.exists(os.path.join(clone, ".identifying-denylist.txt")):
        fail("fresh clone already has .identifying-denylist.txt (should be gitignored)")

    env = dict(os.environ)
    env.pop("BRAIN_ROOT", None)

    readme = open(os.path.join(clone, "README.md"), encoding="utf-8").read()

    # 1. copy the example config (Setup step 2)
    shutil.copy(os.path.join(clone, "brain.config.example.json"), os.path.join(clone, "brain.config.json"))
    ok("copied brain.config.example.json -> brain.config.json")

    # 2. install hooks (Setup step 4)
    run([sys.executable, "scripts/install_hooks.py"], cwd=clone, env=env)
    hook = os.path.join(clone, ".git", "hooks", "pre-commit")
    if os.path.exists(hook):
        ok("pre-commit hook installed")
    else:
        fail("pre-commit hook was not installed")

    # 3. every literal command the README shows
    cmds = readme_commands(readme)
    if not cmds:
        fail("found no runnable python commands in README.md - did the README change shape?")
    check_command_paths(clone, cmds)
    for cmd in cmds:
        run(cmd, cwd=clone, env=env)
    ok(f"ran {len(cmds)} command(s) from the README: " + "; ".join(" ".join(c[1:]) for c in cmds))

    # 4. expected outputs, no leftover placeholders
    expect = [
        "examples/specs/out/geo110-mt1-quiz.html",
        "examples/wiki/courses/geo110/geo110-mt1-dashboard.md",
        "examples/wiki/courses/geo110/geo110-mt1-mastery.md",
        "examples/wiki/courses/geo110/geo110-mt1-pretest-bank.md",
        "examples/wiki/courses/phys105/phys105-mt1-dashboard.md",
        "examples/wiki/courses/phys105/phys105-mt1-mastery.md",
        "examples/wiki/courses/phys105/phys105-mt1-pretest-bank.md",
        "examples/wiki/courses/phys105/phys105-mt1-answers.json",
        "examples/wiki/courses/phys105/phys105-mt1-answers.js",
    ]
    for rel in expect:
        p = os.path.join(clone, rel)
        if not os.path.exists(p):
            fail(f"expected build output missing: {rel}")
            continue
        text = open(p, encoding="utf-8", errors="replace").read()
        if "@@" in text:
            fail(f"leftover @@ placeholder in {rel}")
    if not FAILURES:
        ok("every expected build output exists with no leftover @@ placeholders")

    # 4b. paper banks lock their rubrics and the dashboard has the submitter; digital ones don't
    def text(rel): return open(os.path.join(clone, rel), encoding="utf-8").read()
    pb, gb = text("examples/wiki/courses/phys105/phys105-mt1-pretest-bank.md"), text("examples/wiki/courses/geo110/geo110-mt1-pretest-bank.md")
    if "[!check]" in pb or "dv.view(" not in pb:
        fail("phys105 pre-test bank should lock its rubrics behind dv.view, with no folded callouts")
    if "## Submit work" not in text("examples/wiki/courses/phys105/phys105-mt1-dashboard.md"):
        fail("phys105 dashboard is missing its Submit work section")
    if "[!check]" in gb or "dv.view(" not in gb or "## Submit work" in text("examples/wiki/courses/geo110/geo110-mt1-dashboard.md"):
        fail("geo110 (digital) bank should lock its answers, and its dashboard should have no submitter")
    quiz = text("examples/specs/out/geo110-mt1-quiz.html").split("const DATA = ", 1)[1].split("
", 1)[0]
    if '"why"' in quiz or '"answer"' in quiz or '"sealed"' not in quiz:
        fail("geo110 quiz page should carry sealed answers, with no plain answer or why fields")
    if not FAILURES:
        ok("both builds lock answers until graded, the quiz seals them, and only paper gets the submitter")

    # 5. idempotence: run the same commands again, tree must be unchanged
    before = tree_hashes(clone)
    for cmd in cmds:
        run(cmd, cwd=clone, env=env)
    after = tree_hashes(clone)
    if before != after:
        changed = sorted(set(before) ^ set(after)) or [k for k in before if before[k] != after[k]]
        fail(f"running the builders again changed files (not idempotent): {changed}")
    else:
        ok("running the same commands again changed nothing (idempotent)")

    # 6. soft check: README-mentioned paths exist
    check_readme_paths(clone, readme)

    shutil.rmtree(tmp, ignore_errors=True)

    if FAILURES:
        print(f"\n{len(FAILURES)} failure(s):", file=sys.stderr)
        for f in FAILURES:
            print(f" - {f}", file=sys.stderr)
        sys.exit(1)

    print("\nsmoke test passed.")


if __name__ == "__main__":
    main()
