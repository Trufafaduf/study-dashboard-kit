// Built by the study-dashboard kit. A bank page calls this for each item's rubric or answers.
// They show once the item page's `prop` (pretest_score or posttest_score) is set. Before that,
// "Timecrunch grade" reveals the rubric at once and lets you mark each step yourself; saving
// writes the score, status and an attempt-log row, exactly where Claude's grading would.
const {item, set, prop, data, track, pass = 0.8} = input;
const page = dv.page(item);
const v = page ? page[prop] : null;
const graded = v !== undefined && v !== null && String(v).trim() !== "";
const what = prop === "pretest_score" ? "pre-test" : "post-test";
const decode = b64 => new TextDecoder().decode(Uint8Array.from(atob(b64), c => c.charCodeAt(0)));
const load = async () => (JSON.parse(await app.vault.adapter.read(data))[item] ?? {})[set];
if (graded) {
  const b64 = await load();
  if (!b64) dv.paragraph("No rubric stored for this item. Rebuild the dashboard.");
  else dv.paragraph(decode(b64));
} else {
  const box = dv.el("div", "", {attr: {style: "margin:4px 0 12px;padding:8px 12px;border:1px dashed var(--background-modifier-border);border-radius:6px;font-size:.9em"}});
  box.createEl("div", {text: `Rubric locked until this item's ${what} is graded. Submit your work from the dashboard, or grade it yourself now.`, attr: {style: "color:var(--text-muted);margin-bottom:6px"}});
  const btn = box.createEl("button", {text: "Timecrunch grade"});
  btn.onclick = async () => {
    btn.remove();
    const md = decode(await load() ?? "");
    dv.paragraph(md);
    const n = md.split("\n").filter(l => /^\|\s*\d+\s*\|/.test(l)).length;
    const marks = Array(n).fill("N");
    const panel = dv.el("div", "", {attr: {style: "display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin:6px 0 12px"}});
    panel.createEl("span", {text: "Your steps (tap to mark Y):", attr: {style: "color:var(--text-muted);font-size:.9em"}});
    const toggles = marks.map((_, k) => {
      const t = panel.createEl("button", {text: `${k + 1}: N`});
      t.onclick = () => { marks[k] = marks[k] === "Y" ? "N" : "Y"; t.setText(`${k + 1}: ${marks[k]}`); };
      return t;
    });
    const save = panel.createEl("button", {text: "Save grade", cls: "mod-cta"});
    save.onclick = async () => {
      save.disabled = true; toggles.forEach(t => t.disabled = true);
      const pad = x => String(x).padStart(2, "0"), d = new Date();
      const day = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
      const y = marks.filter(m => m === "Y").length, score = n ? y / n : 0, pct = `${Math.round(score * 100)}%`;
      const cur = page.mastery ?? "untested", last = page.last_graded ? String(page.last_graded).slice(0, 10) : "";
      const st = score < pass ? "weak"
        : prop === "posttest_score" && cur === "shaky" && last && last < day ? "mastered"
        : cur === "mastered" ? "mastered" : "shaky";
      await app.fileManager.processFrontMatter(app.vault.getAbstractFileByPath(page.file.path), fm => {
        fm[prop] = pct; fm.last_graded = day; fm.mastery = st;
        delete fm.submitted; delete fm.submission_kind; delete fm.submission_files;
      });
      const tf = track && app.vault.getAbstractFileByPath(track);
      if (tf) await app.vault.process(tf, s => {
        const row = `| ${day} | [[${item}]] | ${what} | ${marks.join("")} | ${pct} | timecrunch self-grade |`;
        const i = s.indexOf("## Attempt log"); if (i < 0) return s;
        const end = s.indexOf("\n## ", i + 1), seg = s.slice(i, end < 0 ? s.length : end);
        const lines = seg.split("\n"); let k = lines.length - 1;
        while (k > 0 && !lines[k].trim().startsWith("|")) k--;
        lines.splice(k + 1, 0, row);
        return s.slice(0, i) + lines.join("\n") + (end < 0 ? "" : s.slice(end));
      });
      new Notice(`Saved ${item}: ${marks.join("")} = ${pct}, ${st}.`, 6000);
    };
  };
}
