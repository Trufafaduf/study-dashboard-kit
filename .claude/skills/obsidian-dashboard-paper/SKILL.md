---
name: obsidian-dashboard-paper
description: Build or update a paper-graded exam study dashboard in the wiki, inside Obsidian, for work where the user does maths or draws their reasoning by hand - one worked problem per concept with a step rubric that stays locked until the attempt is graded, status stored as page properties, a Dataview dashboard note with a photo submit button per item, an optional claude.ai mastery board whose rubrics are left out of the page until each item is graded, and grading from photos of their work. Use when the user says /obsidian-dashboard-paper, asks for a study dashboard for a maths-heavy exam, sends a photo of a pre-test to grade, or says "grade <course> submissions". For multiple-choice or written-answer exams use obsidian-dashboard-digital instead.
---

# /obsidian-dashboard-paper

For exams where the work is maths or drawn reasoning, done on paper or a tablet
and graded from a photo. Turns a course sub-cluster (e.g.
`wiki/<university>/<course>/`) into a study loop in Obsidian: pre-test every item
cold, grade it, drill what is weak, post-test, repeat. Its sibling,
`obsidian-dashboard-digital`, is for everything that can be answered by typing:
it shares this build script and adds an in-page quiz artifact.

Arguments: the course and exam, e.g. `/obsidian-dashboard-paper chem101 midterm 2`.
With no argument, ask which course and exam.

## Where things live

- The kit's scripts and templates are in this skill folder.
- **Your specs are private**: keep them in `specs/` at the brain root (outside
  the kit if the kit is a submodule), never inside this folder. They hold your
  course, dates and questions.
- A spec's `wiki_dir` is relative to the brain root (the `BRAIN_ROOT` variable,
  or the nearest folder above the spec that contains `wiki/`).
- `brain.config.json` at the brain root (copy `brain.config.example.json`)
  gives your Obsidian vault name so the build can print an `obsidian://` link.

## What it produces

For a spec with `prefix` P, inside the course folder:

| Page | Holds |
| --- | --- |
| item pages (existing concept/source pages) | properties: `<exam_key>: true`, `order`, `lecture`, `mastery`, `pretest_due`, `pretest_score`, `posttest_score`, `last_graded`, `pretest` (link to its questions), `needs` (prerequisite links) |
| `P-pretest-bank` | every item's problem or questions. Each rubric is **locked**: a small DataviewJS view shows it only once the item page has a `pretest_score` (a post-test bank's answers wait for `posttest_score`) |
| `P-answers.json`, `P-answers.js` | the locked rubrics and answers (base64, so a stray glance at the file gives nothing away) and the view the banks call. Obsidian's file list hides both by default |
| `P-mastery` | the loop, status rules, a Dataview status table, the attempt log, a **Review** checklist (one task per reading, slide deck, handout, problem set or past exam, linked to the file and its wiki page), the dated schedule as `[due::]` tasks |
| `out/P-board.html` (optional) | the claude.ai **mastery board**, built by `build_board.py` when the spec has a `board` block: countdown, do-next, dependency map, one panel per item (problem, logic, needs and unlocks, attempts, a copyable grading request), plan and grading tabs. **An item's rubric is written into the page only once its page has a `pretest_score`**; until then the page holds the step count and a locked notice, so the rubric is in neither the page nor its source. `out/` is gitignored |
| `P-dashboard` | DataviewJS countdown and status bar, do-next list (reviews that are due included), **Submit work** (one row per item: pre-test or post-test, and a button that saves photos or a PDF into `P-submissions/` and flags the item page), mermaid map coloured by status, status table, **To review** (progress bar and the checklist, tickable in place), schedule, embedded attempt log |

Status lives only in item properties, the attempt log and the tracker's
checkboxes. A submission adds three properties to the item page until it is
graded: `submitted` (date), `submission_kind` (pre-test or post-test) and
`submission_files` (vault paths). The photos stay in `P-submissions/`, which
the brain should gitignore (`wiki/**/*-submissions/`).
The lock and the submitter are on for every build run from this skill; a spec
can turn either off with `"lock_answers": false` or `"submitter": false`. A rebuild keeps ticked boxes, both review and schedule tasks.
Nothing is kept in browser storage or an artifact.

## Steps

1. **Check the wiki is ready.** Run `/ingest` first if `raw/` has anything
   outside `raw/ingested/`. Read the course hub, its exam guide, the syllabus
   page, past exams and practice questions. Settle three things and say them
   before writing: the **exam date and time**, the **scope** (by lecture, not
   textbook chapter; mark anything uncertain as its own "scope unconfirmed"
   column rather than dropping it), and the **format** (worked problems or
   multiple choice).
2. **Pick the items.** One item per concept page in scope. Item ids are page
   filenames. Create a page only when a needed idea has none (for example the
   prerequisite maths skills a course assumes); give it rule, worked example
   and trap. Draw `needs` edges from what each item builds on.
3. **Write the questions** from the wiki pages, never from memory:
   - `format: "steps"` for worked-problem exams: one new problem per item, a
     rubric of 3–6 binary steps written logic-first (a plain sentence per step,
     the expected result beside it). Check every expected result by hand.
   - Never use held-back mock exams, and avoid figures the wiki records as
     contested (check each page's Contradictions section).
   - Honour course rules recorded on the hub (for instance a ban on generative
     AI for assignments: study questions are fine, graded assignments are off
     limits).
4. **Write the spec** as `specs/<course>-<exam>.json` at the brain root. The
   kit's example (`examples/specs/`) shows the shape. Use `format: "steps"`
   here; multiple-choice specs belong to the digital skill. Course fields:
   `title`, `prefix`, `tag`, `exam_key`, `wiki_dir`, `created`, `today`, `tags`,
   `exam` {`when` ISO with offset, `label`, `name`}, `cols`, `related`,
   `bank_intro`, `tracker_intro`, `loop`, `grading` (say how to submit: the
   dashboard's Submit work button, then "grade <tag> submissions"; and that the
   rubric unlocks after grading), `plan`
   [{`date`,`dow`,`mon`,`head`,`items`}], `schedule_note`, `review` (below),
   and optional `review_intro` and `bank_name` / `tracker_name` /
   `dashboard_name` overrides. Item fields: `id`,
   `title` (also the bank heading the `pretest` link points at), `short` (map
   label), `col`, `lec`, `mins`, `needs`, `logic`, `due`, `format`, then `q` +
   `rubric` [[step, expected], ...] or `questions`, optional `post`, optional
   `create_page` {`title`,`tags`,`body`}.

   **Review list.** `review` is [{`group`, `items`}], one group per kind of
   material (lecture slides, readings, sections, problem sets, past exams).
   Each item has a stable `id` (the tick is kept by it across rebuilds),
   `title`, `file` (path from the brain root, usually in `raw/ingested/`; take
   it from the source page's `raw_files`) or `url`, `page` (the wiki source
   page), optional `due` and a short `note`. List every artifact in scope, not
   only the ones already in a plan task. Leave out held-back mocks, so the
   checklist never invites opening one; say so in `review_intro`.
5. **Build**: `python <this skill folder>/build_dashboard.py specs/<file>.json`
   from the brain root. It is safe to rerun: existing `mastery` and scores are
   kept, and the attempt log is carried over. It asserts every `needs` target
   exists, and every review item's file and page.
6. **Wire it into the wiki** per CLAUDE.md: links both ways (hub Analyses, exam
   guide, practice-question page), index entries for the three pages, and a log
   entry. Run a broken-link check on the three new pages.
7. **Open it** with the `obsidian://` link the build prints (needs
   `brain.config.json`). Dataview must be installed with JavaScript queries on.
   **Board** (when the spec has `board`: {`url`, and optional `title`,
   `eyebrow`, `heading`, `sub`, `post_note`, `grade_label`}): run
   `python <this skill folder>/build_board.py specs/<file>.json` and publish
   `specs/out/<prefix>-board.html` to `board.url` with the Artifact tool (read
   it first when this conversation hasn't published it). No capabilities. For a
   new board, publish without `url`, then write the URL into the spec.
8. **Commit** (if Auto-commit is on, per Version control in `CLAUDE.md`): the
   spec, the generated pages, edited item and hub pages, index and log, by path,
   with the log heading as the message. Rebuilds commit the same way. Never push.

## Grading an attempt

Two ways in. Either the user sends a photo in chat and names the item, or they
submit from the dashboard and say **"grade <tag> submissions"** (or "grade
submissions"). For the second, find every item page in the course folder with a
`submitted` property, and read each file in its `submission_files` (images with
Read; a PDF with its pages). Grade each item as below, pre-test or post-test by
its `submission_kind`, oldest first.

Grade against the rubric or answers **in the spec**, not the bank page: the bank
keeps them locked until the grade is in, and the spec is the source.

Partial work is a valid attempt. Grade whatever was sent: a step or question
left blank is marked N, like a wrong one. Never ask for the rest first, and tell
the user to stop where they're stuck rather than guess, so the marks show what
they actually know. Write the study instructions in `loop` and `grading` the
same way ("write the steps you can"), never "show every step".

1. Mark each step or question Y or N against the rubric or answers. For
   steps, a step passes only if its claim is true and it uses the right tool.
   Say which failed and why, and whether the miss is really a prerequisite.
   For a set of questions with final answers (multiple choice, short numeric
   answers), mark the answer and the working separately. If 90% or more of the
   answers are right (the spec's `solid`), the attempt is **solid** and passes
   however thin the working; the log note names the questions whose working
   was missing or wrong. A single worked problem keeps the step rule.
2. Append a row to the `P-mastery` attempt log:
   `| YYYY-MM-DD | [[item]] | pre-test or the post-test source | YYNY | 75% | note |`.
3. Update the item page's properties: `pretest_score` or `posttest_score`,
   `last_graded`, and `mastery` by the rules below, and delete `submitted`,
   `submission_kind` and `submission_files` if present. Setting the score is
   what unlocks the item's rubric on the bank. The dashboard updates itself.
   Leave the photos where they are; they're local and gitignored.
4. For a post-test, use a different problem from the item's `post` list (problem
   sets, sections, unheld past exams), never a held-back mock.
5. If the spec has a `board`, rebuild it with `build_board.py` and republish
   it to `board.url`. That is what puts the graded item's rubric on the board;
   never paste a rubric into the board or chat before its grade is in.
6. Log the grading in `wiki/log.md`, then **commit** (if Auto-commit is on): the
   tracker, the item page and `log.md`, by path, with the log heading as the
   message. Never push.

Status rules: an attempt passes at 80%+ (the spec's `pass`), or when it is
solid (above). **untested** (no attempt), **weak** (latest did not pass),
**shaky** (one pass), **mastered** (two passes on different questions, 24 hours
or more apart).

## Pitfalls

- A `|` inside maths breaks a markdown table: write `\lvert x\rvert`.
- Spec strings with LaTeX written from Python must be raw strings, or `\t`,
  `\f`, `\b` turn into control characters.
- Dataview can't query rows of a markdown table, which is why status is in
  properties and the table is a query.
- A learning-management system's Files export often holds only the Files area.
  Lecture slides posted in modules or pages can be missing from it; check before
  assuming the scope is covered.
- The board is a snapshot. Rebuild and republish it after every grading, or
  its statuses go stale and graded rubrics stay locked. `build_board.py` and
  `board_template.html` belong to this skill only.
- `build_dashboard.py`, `dashboard_template.md`, `submit_block.md` and
  `answers_view.js` are shared with `obsidian-dashboard-digital`; keep the two
  copies identical. The script tells the skills apart by its folder name.
- The lock stops accidental peeking, not a determined reader: the answers file
  is in the vault. Never paste a locked rubric into chat before the grade is in.
- Obsidian rewrites an item page's frontmatter in its own style when the
  submitter sets properties (quotes, list layout). The build reads either style.
- The submitter's file picker needs Obsidian desktop or mobile with Dataview
  JavaScript queries on. On mobile, the picker offers the camera.
