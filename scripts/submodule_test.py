#!/usr/bin/env python3
"""Submodule test for study-dashboard-kit.

    python scripts/submodule_test.py

Simulates a real user adding this kit to their own brain as a git submodule:

  1. Make a throwaway "brain" repo in a temp dir, with its own wiki/.
  2. Add this repo as a submodule (kit-dashboards/), from the local clone
     (`-c protocol.file.allow=always`, since a local path isn't an allowed
     submodule protocol by default).
  3. Run scripts/link-kit.ps1 on Windows, scripts/link-kit.sh elsewhere - the
     link step for the current OS.
  4. Confirm Claude Code's discovery paths resolve:
     .claude/skills/obsidian-dashboard-digital/SKILL.md and
     .claude/skills/obsidian-dashboard-paper/SKILL.md under the brain root.
  5. Build both example courses (from kit-dashboards/examples/) invoked with
     paths relative to the brain root, the way a real user would run them.

Stdlib only. Exit non-zero with a clear message on any failure.
"""
import os
import platform
import subprocess
import sys
import shutil
import tempfile

FAILURES = []


def fail(msg):
    FAILURES.append(msg)
    print(f"FAIL: {msg}", file=sys.stderr)


def ok(msg):
    print(f"ok: {msg}")


def run(cmd, cwd, env=None, check=True):
    r = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True)
    if check and r.returncode != 0:
        fail(
            f"command failed ({r.returncode}) in {cwd}: {' '.join(cmd)}\n"
            f"--- stdout ---\n{r.stdout}\n--- stderr ---\n{r.stderr}"
        )
    return r


def git(args, cwd, env=None):
    return run(["git"] + args, cwd=cwd, env=env)


def main():
    repo_root = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=True
    ).stdout.strip()

    tmp = tempfile.mkdtemp(prefix="sdk-submodule-")
    brain = os.path.join(tmp, "my-brain")
    os.makedirs(os.path.join(brain, "wiki"), exist_ok=True)
    with open(os.path.join(brain, "wiki", ".gitkeep"), "w") as f:
        f.write("")
    print(f"throwaway brain: {brain}")

    env = dict(os.environ)
    env.pop("BRAIN_ROOT", None)
    env["GIT_AUTHOR_NAME"] = env["GIT_COMMITTER_NAME"] = "submodule-test"
    env["GIT_AUTHOR_EMAIL"] = env["GIT_COMMITTER_EMAIL"] = "submodule-test@example.com"

    git(["init", "-q", "-b", "main"], cwd=brain, env=env)
    git(["add", "wiki/.gitkeep"], cwd=brain, env=env)
    git(["commit", "-q", "-m", "init"], cwd=brain, env=env)

    # 2. add this repo as a submodule from the local clone
    git(
        ["-c", "protocol.file.allow=always", "submodule", "add", repo_root, "kit-dashboards"],
        cwd=brain,
        env=env,
    )
    ok("added kit-dashboards as a submodule from the local clone")
    kit_dir = os.path.join(brain, "kit-dashboards")

    # 3. link step for the current OS
    if platform.system() == "Windows":
        r = run(
            ["powershell", "-ExecutionPolicy", "Bypass", "-File", os.path.join(kit_dir, "scripts", "link-kit.ps1")],
            cwd=brain,
            env=env,
        )
    else:
        script = os.path.join(kit_dir, "scripts", "link-kit.sh")
        run(["chmod", "+x", script], cwd=brain, env=env, check=False)
        r = run(["sh", script], cwd=brain, env=env)
    if not FAILURES:
        ok("ran the link step for " + platform.system())

    # 4. discovery paths resolve
    for name in ("obsidian-dashboard-digital", "obsidian-dashboard-paper"):
        p = os.path.join(brain, ".claude", "skills", name, "SKILL.md")
        if os.path.exists(p):
            ok(f".claude/skills/{name}/SKILL.md resolves")
        else:
            fail(f".claude/skills/{name}/SKILL.md does not resolve after linking")

    # 5. build both example courses, invoked with paths relative to the brain root
    digital = os.path.join("kit-dashboards", ".claude", "skills", "obsidian-dashboard-digital")
    paper = os.path.join("kit-dashboards", ".claude", "skills", "obsidian-dashboard-paper")
    specs = os.path.join("kit-dashboards", "examples", "specs")
    builds = [
        [sys.executable, os.path.join(digital, "build_quiz.py"), os.path.join(specs, "geo110-midterm-1.json")],
        [sys.executable, os.path.join(digital, "build_dashboard.py"), os.path.join(specs, "geo110-midterm-1.json")],
        [sys.executable, os.path.join(paper, "build_dashboard.py"), os.path.join(specs, "phys105-midterm-1.json")],
    ]
    for cmd in builds:
        run(cmd, cwd=brain, env=env)
    ok("built both example courses from the brain root")

    expect = [
        "kit-dashboards/examples/specs/out/geo110-mt1-quiz.html",
        "kit-dashboards/examples/wiki/courses/geo110/geo110-mt1-dashboard.md",
        "kit-dashboards/examples/wiki/courses/phys105/phys105-mt1-dashboard.md",
    ]
    for rel in expect:
        if not os.path.exists(os.path.join(brain, rel)):
            fail(f"expected build output missing: {rel}")
    if not FAILURES:
        ok("build outputs landed inside the submodule's own examples/ (unaffected by the outer brain root)")

    shutil.rmtree(tmp, ignore_errors=True)

    if FAILURES:
        print(f"\n{len(FAILURES)} failure(s):", file=sys.stderr)
        for f in FAILURES:
            print(f" - {f}", file=sys.stderr)
        sys.exit(1)

    print("\nsubmodule test passed.")


if __name__ == "__main__":
    main()
