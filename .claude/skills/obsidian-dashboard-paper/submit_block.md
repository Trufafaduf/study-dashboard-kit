## Submit work

Pick pre-test or post-test, then add photos (or a PDF) of your work. They are
saved to `@@SUBDIR@@/` and the item is flagged as awaiting a grade. Then tell
Claude Code **grade @@TAG@@ submissions**; the button copies that for you. An
item's rubric unlocks on the bank once its attempt is graded. Short on time?
**Timecrunch grade** opens the item on the bank, where you reveal the rubric
and mark your own steps; saving records it like any other grade.

```dataviewjs
const items = dv.pages("#@@TAG@@").where(p => p["@@KEY@@"]).sort(p => p.order);
const dir = "@@SUBDIR@@", cmd = "grade @@TAG@@ submissions";
const pad = n => String(n).padStart(2, "0");
const pending = items.where(p => p.submitted);
dv.el("div", pending.length ? `${pending.length} awaiting grading. Tell Claude Code: ${cmd}` : "Nothing awaiting grading.",
  {attr: {style: "margin:4px 0 8px;color:var(--text-muted)"}});
const list = dv.el("div", "", {attr: {style: "display:grid"}});
for (const p of items) {
  const st = p.mastery ?? "untested";
  const row = list.createEl("div", {attr: {style: "display:flex;flex-wrap:wrap;align-items:center;gap:6px 12px;padding:6px 0;border-bottom:1px solid var(--background-modifier-border)"}});
  const a = row.createEl("a", {text: p.file.name, cls: "internal-link", attr: {"data-href": p.file.path, href: p.file.path, style: "flex:1 1 220px"}});
  a.onclick = e => { e.preventDefault(); app.workspace.openLinkText(p.file.path, "", false); };
  row.createEl("span", {text: p.submitted ? `awaiting grade · ${p.submission_kind ?? ""} · ${p.submitted}` : st,
    attr: {style: `font-size:.9em;color:${p.submitted ? "var(--text-accent)" : "var(--text-muted)"}`}});
  const sel = row.createEl("select", {cls: "dropdown"});
  for (const o of ["pre-test", "post-test"]) sel.createEl("option", {text: o, value: o});
  sel.value = (st === "shaky" || st === "mastered") ? "post-test" : "pre-test";
  const btn = row.createEl("button", {text: p.submitted ? "Add photos" : "Submit photos"});
  const inp = row.createEl("input", {attr: {type: "file", accept: "image/*,application/pdf", multiple: "", style: "display:none"}});
  btn.onclick = () => inp.click();
  const tc = row.createEl("button", {text: "Timecrunch grade"});
  tc.onclick = () => { const l = p.pretest; if (l && l.path) app.workspace.openLinkText(l.path + (l.subpath ? "#" + l.subpath : ""), p.file.path, false); };
  inp.onchange = async () => {
    const files = [...inp.files]; if (!files.length) return;
    btn.disabled = true; btn.setText("Saving…");
    if (!app.vault.getAbstractFileByPath(dir)) await app.vault.createFolder(dir);
    const t = new Date(), day = `${t.getFullYear()}-${pad(t.getMonth() + 1)}-${pad(t.getDate())}`;
    const stamp = `${day}-${pad(t.getHours())}${pad(t.getMinutes())}${pad(t.getSeconds())}`;
    const saved = [];
    for (const [k, f] of files.entries()) {
      const ext = (f.name.includes(".") ? f.name.split(".").pop() : "jpg").toLowerCase();
      const path = `${dir}/${p.file.name}-${stamp}-${k + 1}.${ext}`;
      await app.vault.createBinary(path, await f.arrayBuffer()); saved.push(path);
    }
    await app.fileManager.processFrontMatter(app.vault.getAbstractFileByPath(p.file.path), fm => {
      fm.submitted = day; fm.submission_kind = sel.value;
      fm.submission_files = [...(fm.submission_files ?? []), ...saved];
    });
    try { await navigator.clipboard.writeText(cmd); } catch (e) {}
    new Notice(`Saved ${saved.length} file(s) for ${p.file.name}. Paste into Claude Code: ${cmd}`, 8000);
  };
}
```
