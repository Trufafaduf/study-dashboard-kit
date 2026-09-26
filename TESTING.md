# Manual testing checklist

`scripts/smoke_test.py`, `scripts/submodule_test.py` and `scripts/scan_history.py`
(run in CI, see `.github/workflows/test.yml`) cover everything that can be
checked without a human and a real claude.ai account. The steps below are the
ones that can't be automated - do these by hand before publishing a release or
a significant change.

## 1. Claude Code discovers the skills

1. Clone this repo fresh (not the working copy you've been editing).
2. Open the clone in Claude Code.
3. Ask it to list its available skills, or type `/` and look at the command
   list; either way, confirm **`obsidian-dashboard-digital`** and
   **`obsidian-dashboard-paper`** are both listed with their descriptions from
   `SKILL.md`.

If you're testing this kit as a submodule inside a brain instead, do this
after running `link-kit.ps1`/`link-kit.sh` and confirm the skills are
discovered from the **brain's** `.claude/skills/`, not the submodule's.

## 2. The example dashboards render in Obsidian

1. Run the two build commands from the README's "Using it standalone"
   section (or let the smoke test do it, then keep its output instead of
   letting it clean up - see the script if you want to do this by hand).
2. Open `examples/` itself as an Obsidian vault.
3. Install the **Dataview** community plugin if it isn't already, and in its
   settings, enable **JavaScript queries** (dashboards use DataviewJS).
4. Open `examples/wiki/courses/geo110/geo110-mt1-dashboard.md` and
   `examples/wiki/courses/phys105/phys105-mt1-dashboard.md`. Confirm each
   renders: a countdown to the exam, a do-next list, a status table, and (for
   GEO 110) a link to the quiz once you've published one (step 3).
5. Open `geo110-mt1-mastery.md` and `phys105-mt1-mastery.md` and confirm the
   Dataview status table renders there too.

## 3. Publish the example quiz and run one attempt end to end

This step needs a claude.ai account where published artifacts can use the
`db` and `sample` capabilities.

1. Build `examples/specs/out/geo110-mt1-quiz.html` (see README).
2. Publish it with Claude's Artifact tool: `capabilities: {"db": {}, "sample": {}}`,
   an icon, and a one-sentence description.
3. Put the returned URL in `examples/specs/geo110-midterm-1.json`'s
   `quiz_url`, and rebuild the dashboard so it links to the quiz.
4. Open the published quiz. Answer one item's questions, type reasoning for
   each, and submit. Confirm it grades (answers marked, reasoning scored
   1-5) rather than falling back to self-scoring.
5. Ask Claude to "sync geo110". Confirm it reads the attempt from the
   artifact's database, appends a row to `geo110-mt1-mastery.md`'s attempt
   log, and updates the item's `pretest_score`/`mastery` properties.

## 4. A second person, cold

Have someone who hasn't seen this repo before follow the README on their own
machine (a different OS than yours if you can arrange it), from cloning
through building the examples, with no help beyond what's written there. Note
anywhere they got stuck - that's a README gap, not a them problem.
