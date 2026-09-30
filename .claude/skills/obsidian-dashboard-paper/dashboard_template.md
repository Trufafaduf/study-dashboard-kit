---
title: @@TITLE@@ dashboard
type: project
created: @@CREATED@@
updated: @@TODAY@@
tags: [@@TAGS@@]
---

# @@TITLE@@ dashboard

Live view of [[@@TRACK@@]]. Everything below is computed from the item pages'
properties, so it updates as soon as a page changes. Needs the Dataview plugin
with JavaScript queries on.

@@QUIZ_BLOCK@@
```dataviewjs
const exam = new Date("@@EXAM_ISO@@");
const ms = exam - new Date();
const d = Math.floor(ms/864e5), h = Math.floor(ms%864e5/36e5);
const items = dv.pages("#@@TAG@@").where(p => p["@@KEY@@"]);
const n = items.length;
const count = s => items.where(p => (p.mastery ?? "untested") === s).length;
const C = {mastered:"var(--color-green)", shaky:"var(--color-orange)", weak:"var(--color-red)", untested:"var(--text-faint)"};
const box = dv.el("div", "", {attr:{style:"display:grid;gap:10px;margin:4px 0 8px"}});
const top = box.createEl("div", {attr:{style:"display:flex;flex-wrap:wrap;gap:8px 28px;align-items:baseline"}});
top.createEl("span", {text: ms > 0 ? `${d} days ${h} hours to @@EXAM_NAME@@` : "Exam day", attr:{style:"font-size:1.5em;font-weight:600"}});
top.createEl("span", {text:"@@EXAM_LABEL@@", attr:{style:"color:var(--text-muted)"}});
const bar = box.createEl("div", {attr:{style:"display:flex;height:12px;border-radius:4px;overflow:hidden;background:var(--background-modifier-border)"}});
for (const s of ["mastered","shaky","weak","untested"]) { const c = count(s); if (c) bar.createEl("span", {attr:{style:`width:${c/n*100}%;background:${C[s]}`}}); }
box.createEl("div", {text: ["mastered","shaky","weak","untested"].map(s => `${s} ${count(s)}`).join(" · ") + ` · of ${n}`, attr:{style:"color:var(--text-muted);font-size:.9em"}});
```

## Do next

```dataviewjs
const today = dv.date("today");
const items = dv.pages("#@@TAG@@").where(p => p["@@KEY@@"]);
const st = p => p.mastery ?? "untested";
const due = p => p.pretest_due ? dv.date(p.pretest_due) : null;
const clean = t => t.text.replace(/\s*\[(due|review|completion):: [^\]]*\]/g, "");
const reviews = dv.pages("#@@TAG@@").where(p => p.file.name === "@@TRACK@@").file.tasks
  .where(t => t.review && !t.completed && t.due && dv.date(t.due) <= today);
const open = items.where(p => !p.submitted);
const q = [
  ...open.where(p => st(p) === "weak").sort(p => p.order).map(p => [p, "drill what you missed"]),
  ...reviews.map(t => [null, "review: " + clean(t)]),
  ...open.where(p => st(p) === "untested" && due(p) && due(p) <= today).sort(p => p.order).map(p => [p, "pre-test"]),
  ...open.where(p => st(p) === "shaky").sort(p => p.order).map(p => [p, "post-test on new questions"]),
];
if (q.length) dv.list(q.slice(0, 14).map(([p, what]) => p ? `${p.file.link} — ${what} · ${p.pretest ?? ""}` : what));
else dv.paragraph("Nothing due. Pull the next untested item forward.");
```

@@SUBMIT_BLOCK@@

## Map

Arrows run from what an item builds on to what it unlocks. Colour is status:
green mastered, amber shaky, red weak, grey untested.

```dataviewjs
const items = dv.pages("#@@TAG@@").where(p => p["@@KEY@@"]).sort(p => p.order);
const SHORT = @@SHORT@@;
const cols = @@COLS@@;
const id = p => p.file.name.replace(/[^a-z0-9]/gi, "_");
let m = "flowchart LR\n";
cols.forEach((c, i) => {
  m += `  subgraph c${i}["${c}"]\n    direction TB\n`;
  items.where(p => Math.floor(p.order / 100) === i).forEach(p => m += `    ${id(p)}["${SHORT[p.file.name] ?? p.file.name}"]\n`);
  m += "  end\n";
});
items.forEach(p => (p.needs ?? []).forEach(l => { const t = l.path ? l.path.split("/").pop().replace(/\.md$/, "") : String(l); m += `  ${t.replace(/[^a-z0-9]/gi, "_")} --> ${id(p)}\n`; }));
m += "  classDef untested fill:#eaedef,stroke:#7a8591,color:#18202b\n  classDef weak fill:#f8e4e1,stroke:#b3392f,color:#18202b\n  classDef shaky fill:#f6ebd8,stroke:#9c630f,color:#18202b\n  classDef mastered fill:#e1f0e6,stroke:#2e7849,color:#18202b\n";
items.forEach(p => m += `  class ${id(p)} ${p.mastery ?? "untested"}\n`);
dv.paragraph("```mermaid\n" + m + "```");
```

## Status

```dataview
TABLE WITHOUT ID file.link AS Item, lecture AS Lecture, mastery AS Status, pretest AS Problem, pretest_due AS "Pre-test by", pretest_score AS Pre, posttest_score AS Post, last_graded AS Graded
FROM #@@TAG@@ WHERE @@KEY@@ SORT order ASC
```

@@REVIEW_BLOCK@@
## Schedule

```dataview
TASK FROM #@@TAG@@
WHERE file.name = "@@TRACK@@" AND !review
GROUP BY due
```

## Graded attempts

![[@@TRACK@@#Attempt log]]

## How grading works

@@GRADING@@

## Related

- [[@@TRACK@@]] — the record and the rules.
- [[@@BANK@@]] — @@BANK_NOTE@@.
@@RELATED@@
