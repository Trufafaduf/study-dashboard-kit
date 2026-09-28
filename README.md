# study-dashboard-kit

Two Claude Code skills that turn a course cluster in an Obsidian-based wiki
into an exam study loop, with status stored as page properties and a dashboard
built on the Dataview plugin. Originally part of
[brain-kit](https://github.com/Trufafaduf/brain-kit); split out so the study
tools can be used, versioned and improved on their own.

- **`obsidian-dashboard-digital`**, for multiple choice, true/false and short
  written reasons. It builds a quiz page published as a claude.ai artifact. You
  pick answers and type your reasoning; grading happens in the page, in two
  parts: each **answer** is marked right or wrong, and Claude scores each
  **reason** 1–5 against a reference reason from your notes (5 exact, 4 close,
  3 pass, 2 partial, 1 missing). An attempt passes when at least 80% of answers
  are right and at least 80% of reasons score 3 or more, or is **solid** (also
  a pass) when 90% of answers are right, with a note on the reasons to shore up.
  Both thresholds are spec settings (`pass`, `solid`). "Post-test: new
  questions" asks Claude to write fresh questions from the item's wiki page.
  Attempts are saved in the artifact's database; say "sync `<course>`" and
  Claude logs them in the wiki and updates each item's mastery.
- **`obsidian-dashboard-paper`**, for maths and hand-drawn work. One worked
  problem per concept with a folded step-by-step rubric; you work on paper,
  send a photo, and Claude grades it against the rubric.
- **`final-review`**, for the night before. Turns every graded attempt into one
  Obsidian page, a step per item with the weakest first: each missed point as the
  fact to learn, linked to the wiki heading that states it and the source file
  behind it. Its settings (`config.json`) and layout (`dossier_template.md`) are
  plain files, so feedback changes them without touching code.

Mastery rules are shared: **weak** if the latest attempt did not pass,
**shaky** after one pass, **mastered** after two passes on different questions
at least 24 hours apart.

## Requirements

- Claude Code, with these skills discoverable at `.claude/skills/<name>/SKILL.md`
  (directly, or through the brain that includes this kit — see below).
- Python 3.9 or later (stdlib only; no dependencies to install).
- An Obsidian vault with the **Dataview** community plugin, JavaScript queries
  enabled, to render the dashboard notes.
- For the digital skill: a claude.ai account where published artifacts can use
  the `db` (page database) and `sample` (ask Claude from the page)
  capabilities. Without them the quiz page cannot save attempts, and grading
  falls back to self-scoring.

## Setup

1. Clone this repo, or add it to your own brain repo as a submodule (below).
2. Copy `brain.config.example.json` to `brain.config.json` (gitignored) at your
   brain's root and set `vault_name` to your Obsidian vault's name. If your
   brain sits inside a larger vault, set `vault_subpath` to its path within the
   vault. The builds use this only to print `obsidian://` links.
3. Open the folder in Obsidian and install the **Dataview** community plugin.
4. Install the privacy hook: `python scripts/install_hooks.py`. It also
   creates an empty `.identifying-denylist.txt` (gitignored); add your own
   terms to it, following `.identifying-denylist.example.txt`.

### macOS, Linux and Windows

Everything here runs on all three; CI tests macOS, Ubuntu and Windows on
Python 3.9 and 3.12. Two differences:

- **Python command.** Commands in this README say `python`. On macOS and most
  Linux systems that is `python3` (macOS ships it with the Xcode command-line
  tools: `xcode-select --install`). The git hook finds either on its own.
- **Linking.** Windows uses `scripts/link-kit.ps1` (junctions and hard links,
  no admin rights needed); macOS and Linux use `scripts/link-kit.sh`
  (symlinks). If your shell says "permission denied", run it as
  `sh scripts/link-kit.sh`.

## Using it standalone

`examples/` is itself a tiny brain: it has its own `wiki/` (two fictional
courses, GEO 110 and PHYS 105) and `specs/` with a spec for each. Build them
from this repo's root to try the skills without a real course:

```
python .claude/skills/obsidian-dashboard-digital/build_quiz.py examples/specs/geo110-midterm-1.json
python .claude/skills/obsidian-dashboard-digital/build_dashboard.py examples/specs/geo110-midterm-1.json
python .claude/skills/obsidian-dashboard-paper/build_dashboard.py examples/specs/phys105-midterm-1.json
```

The builders find the brain root from the `BRAIN_ROOT` environment variable,
or, failing that, the nearest folder above the spec that contains `wiki/` —
here, `examples/`. Open `examples/` itself as an Obsidian vault (with
Dataview) to see the dashboards render.

## Using it inside a brain

Your exam specs are private: keep them in `specs/` at your brain's root, never
inside this kit, whether you clone the kit directly or add it as a submodule.
A spec's `wiki_dir` is relative to the brain root, resolved the same way as
above, so `specs/` and `wiki/` in your own brain work even though the scripts
live inside the kit.

As a submodule:

```
git submodule add <this-repo-url> kit-dashboards
git submodule update --remote kit-dashboards   # pull improvements later
```

Then point Claude Code at its skills, by linking or copying:

```
my-brain/                        private repo
  kit-dashboards/                this repo, as a submodule
  .claude/skills/obsidian-dashboard-digital  ->  kit-dashboards/.claude/skills/obsidian-dashboard-digital
  .claude/skills/obsidian-dashboard-paper    ->  kit-dashboards/.claude/skills/obsidian-dashboard-paper
  .claude/skills/final-review                ->  kit-dashboards/.claude/skills/final-review
  specs/                         your exam specs (private)
  wiki/
```

Use `scripts/link-kit.ps1` (Windows, `powershell -ExecutionPolicy Bypass -File
scripts\link-kit.ps1`, junctions and hard links) or `scripts/link-kit.sh`
(macOS/Linux, symlinks) to create those links — see each script's header for
usage; both are idempotent, safe to rerun after `git submodule update
--remote`. In practice you ask
Claude ("make a study dashboard for `<course>`") and it runs the builders for
you; see each skill's `SKILL.md` for the full workflow.

## Building, in general

From the brain root (your own, or `examples/` above):

```
python <kit>/.claude/skills/obsidian-dashboard-digital/build_quiz.py specs/<course>-<exam>.json
python <kit>/.claude/skills/obsidian-dashboard-digital/build_dashboard.py specs/<course>-<exam>.json
python <kit>/.claude/skills/obsidian-dashboard-paper/build_dashboard.py specs/<course>-<exam>.json
```

The quiz page (digital only) is written to `specs/out/` (gitignored, since it
embeds the answers); publish it as a claude.ai artifact with the `db` and
`sample` capabilities and record its URL in the spec's `quiz_url`. The paper
skill uses `build_dashboard.py` only.

## Privacy model

- `brain.config.json`, `.identifying-denylist.txt`, and build output (`out/`)
  are gitignored.
- `scripts/check_identifying.py` runs as a pre-commit hook. It blocks any
  commit whose staged content contains a home-directory path, a claude.ai
  artifact link, an email address (other than noreply and example domains), or
  any term in your private `.identifying-denylist.txt`. Run
  `python scripts/check_identifying.py --all` to scan the whole tree.
- Your names are never built into the checker: they live only in your
  gitignored deny-list.
- Don't bypass the hook with `--no-verify`. If a hit is a false positive,
  rephrase the text.

## Before publishing

The pre-commit hook only protects commits made after it was installed. If
this repo (or a fork of it) ever had commits before that, or `--no-verify`
was used even once, the working tree can be clean while an old commit still
isn't. Run `python scripts/scan_history.py` to check the full history -
every patch ever committed (`git log -p --all`) and every author/committer
name and email - against the same built-in patterns and your deny-list.

If it finds something and the repo has no history worth keeping, squash to a
single initial commit and force-push:

```
git checkout --orphan clean-main
git add -A
git commit -m "Initial commit"
git branch -D main
git branch -m main
git push --force origin main
```

Rewrite history this way only on a repo you're sure has no collaborators
relying on the old commits, and only after fixing whatever the scan found in
the current working tree first (an orphan commit still contains today's
files).

## Limitations

- Quiz pages contain their answers in the page source. That is fine for a
  single-user study tool; don't share a quiz with classmates before an exam.
- Grading and post-test questions each use one Claude call from your own
  usage.

## Licence

MIT. See `LICENSE`.
