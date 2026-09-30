// Built by the study-dashboard kit. A bank page calls this for each item's rubric or answers.
// They show only once the item page's `prop` (pretest_score or posttest_score) is set.
const {item, set, prop, data} = input;
const page = dv.page(item);
const v = page ? page[prop] : null;
const graded = v !== undefined && v !== null && String(v).trim() !== "";
if (!graded) {
  const what = prop === "pretest_score" ? "pre-test" : "post-test";
  dv.el("div", `Rubric locked until this item's ${what} is graded. Submit your work from the dashboard.`,
    {attr: {style: "margin:4px 0 12px;padding:8px 12px;border:1px dashed var(--background-modifier-border);border-radius:6px;color:var(--text-muted);font-size:.9em"}});
} else {
  const all = JSON.parse(await app.vault.adapter.read(data));
  const b64 = (all[item] ?? {})[set];
  if (!b64) dv.paragraph("No rubric stored for this item. Rebuild the dashboard.");
  else dv.paragraph(new TextDecoder().decode(Uint8Array.from(atob(b64), c => c.charCodeAt(0))));
}
