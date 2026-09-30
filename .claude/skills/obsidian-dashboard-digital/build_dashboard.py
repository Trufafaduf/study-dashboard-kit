"""Build an Obsidian exam dashboard for one course sub-cluster from a JSON spec.

    python build_dashboard.py specs/<name>.json

Writes, inside the spec's wiki folder:
  - properties on every item page (status fields are preserved if already set)
  - pages for items that carry "create_page" and do not exist yet
  - <prefix>-pretest-bank.md     problems, with answers/rubrics in folded callouts
  - <prefix>-posttest-bank.md    only when an item has "post_bank" or
                                  "post_banks" (fixed post-test sets), in the
                                  same format
  - <prefix>-mastery.md          loop, rules, status table, attempt log, schedule
                                  (an existing attempt log is kept)
  - <prefix>-dashboard.md        Dataview countdown, do-next, submit, map, table, schedule
  - <prefix>-answers.json + .js  locked rubrics and answers (run from the paper
                                  skill, or "lock_answers": true): the banks show an item's
                                  rubric only once that attempt is graded

The spec's "wiki_dir" is relative to the brain root: the BRAIN_ROOT environment
variable if set, otherwise the nearest folder above the spec that contains
wiki/. If brain.config.json sits in that root with a "vault_name", the build
prints an obsidian:// link to the dashboard.

Needs the Dataview plugin with JavaScript queries on. See SKILL.md.
"""
import base64, json, os, re, shutil, sys
from urllib.parse import quote

STATUS_KEYS = ("mastery", "pretest_score", "posttest_score", "last_graded")
MANAGED = ("{k}", "order", "lecture", "mastery", "pretest_due", "pretest_score",
           "posttest_score", "last_graded", "needs", "pretest")

def post_banks(i):
    """An item's fixed post-test sets: "post_bank" (one set) and/or "post_banks" (a list),
    each with a setKey. The first is "post-bank", so attempts saved under it still match."""
    bs = ([i["post_bank"]] if i.get("post_bank") else []) + list(i.get("post_banks", []))
    return [dict(b, key=b.get("key") or ("post-bank" if k == 0 else f"post-bank-{k + 1}")) for k, b in enumerate(bs)]

def rd(p):
    with open(p, encoding="utf-8") as f: return f.read()
def wr(p, t):
    with open(p, "w", encoding="utf-8") as f: f.write(t)

def brain_root(spec_path):
    env = os.environ.get("BRAIN_ROOT")
    if env: return os.path.abspath(env)
    for start in (os.path.dirname(os.path.abspath(spec_path)), os.getcwd()):
        d = start
        while True:
            if os.path.isdir(os.path.join(d, "wiki")): return d
            up = os.path.dirname(d)
            if up == d: break
            d = up
    sys.exit("Can't find the brain root (a folder containing wiki/). Set BRAIN_ROOT.")

def wiki_dir(C, spec_path):
    root = brain_root(spec_path)
    return os.path.normpath(os.path.join(root, C["wiki_dir"])), root

def obsidian_link(root, page_path):
    cfg = os.path.join(root, "brain.config.json")
    if not os.path.exists(cfg): return ""
    c = json.loads(rd(cfg))
    if not c.get("vault_name"): return ""
    rel = os.path.relpath(page_path, root).replace(os.sep, "/")
    if c.get("vault_subpath"): rel = c["vault_subpath"].strip("/") + "/" + rel
    return "obsidian://open?vault=" + quote(c["vault_name"]) + "&file=" + quote(rel[:-3] if rel.endswith(".md") else rel, safe="")

def vault_path(root, rel):
    """A brain-root-relative file as a vault path, for wikilinks to non-wiki files."""
    cfg = os.path.join(root, "brain.config.json")
    sub = json.loads(rd(cfg)).get("vault_subpath", "") if os.path.exists(cfg) else ""
    return (sub.strip("/") + "/" + rel) if sub else rel

def old_ticks(text):
    """Tick state of an existing tracker's tasks: review tasks by id, others by text."""
    ticks = {}
    for l in text.splitlines():
        m = re.match(r"^- \[(.)\] (.*)$", l)
        if not m or m.group(1) == " ": continue
        r = re.search(r"\[review:: ([^\]]+)\](.*)$", m.group(2))
        if r: ticks["review:" + r.group(1).strip()] = (m.group(1), r.group(2))
        else:
            d = re.match(r"^(.*?\[due:: [^\]]+\])(.*)$", m.group(2))
            if d: ticks[d.group(1)] = (m.group(1), d.group(2))
    return ticks

def review_lines(C, W, ROOT, ticks):
    """The Review section of the tracker: one task per artifact, grouped."""
    if not C.get("review"): return []
    pages = {f[:-3] for _, _, fs in os.walk(os.path.join(ROOT, "wiki")) for f in fs if f.endswith(".md")}
    out = ["## Review", "", C.get("review_intro", "Every reading, slide deck, handout, problem set and past exam in scope, "
           "with a link to the file and to its wiki page. Tick one when you have reviewed it; a rebuild keeps the ticks.").strip(), ""]
    seen = set()
    for g in C["review"]:
        out += [f"### {g['group']}", ""]
        for a in g["items"]:
            assert a["id"] not in seen, f"duplicate review id {a['id']}"; seen.add(a["id"])
            parts = []
            if a.get("file"):
                assert os.path.exists(os.path.join(ROOT, a["file"])), f"review {a['id']}: missing file {a['file']}"
                parts.append(f"[[{vault_path(ROOT, a['file'])}|{a['title']}]]")
            elif a.get("url"): parts.append(f"[{a['title']}]({a['url']})")
            else: parts.append(a["title"])
            if a.get("page"):
                assert a["page"] in pages, f"review {a['id']}: no wiki page {a['page']}"
                parts.append(f"[[{a['page']}]]")
            if a.get("note"): parts.append(a["note"])
            box, tail = ticks.get("review:" + a["id"], (" ", ""))
            due = f" [due:: {a['due']}]" if a.get("due") else ""
            out.append(f"- [{box}] " + " · ".join(parts) + due + f" [review:: {a['id']}]" + tail)
        out.append("")
    return out

def review_block(C, TRACK):
    if not C.get("review"): return ""
    nl = chr(10)
    return nl.join([
        "## To review", "",
        "Everything to read or work through before the exam, each linked to its file and its",
        f"wiki page. Tick them here or on [[{TRACK}#Review]].", "",
        "```dataviewjs",
        f"const t = dv.pages(\"#{C['tag']}\").where(p => p.file.name === \"{TRACK}\").file.tasks.where(t => t.review);",
        "const done = t.where(t => t.completed).length, n = t.length;",
        "const box = dv.el(\"div\", \"\", {attr:{style:\"display:grid;gap:6px;margin:4px 0 8px\"}});",
        "const bar = box.createEl(\"div\", {attr:{style:\"display:flex;height:8px;border-radius:4px;overflow:hidden;background:var(--background-modifier-border)\"}});",
        "if (done) bar.createEl(\"span\", {attr:{style:`width:${done/n*100}%;background:var(--color-green)`}});",
        "const groups = {}; t.forEach(x => { const g = x.section.subpath ?? \"\"; groups[g] = groups[g] ?? [0, 0]; groups[g][1]++; if (x.completed) groups[g][0]++; });",
        "box.createEl(\"div\", {text: `${done} of ${n} reviewed · ` + Object.entries(groups).map(([g, [a, b]]) => `${g} ${a}/${b}`).join(\" · \"), attr:{style:\"color:var(--text-muted);font-size:.9em\"}});",
        "```", "",
        "```dataview",
        f"TASK FROM #{C['tag']}",
        f"WHERE file.name = \"{TRACK}\" AND review",
        "GROUP BY meta(section).subpath",
        "```"]) + nl

def quiz_block(C):
    if not C.get("quiz_url"): return ""
    nl = chr(10)
    return ("## Answer questions" + nl + nl +
            f"**[Open the {C['title']} quiz]({C['quiz_url']})** to answer, give your reasoning and get "
            "graded. Attempts sync back to this wiki when you ask Claude to sync." + nl)

def question_lines(qs, logic, wrap=lambda a: a):
    """Multiple-choice and true/false questions, then their answers in a folded callout
    (passed through wrap, which locks them when answers are locked)."""
    b = []; n = len(qs)
    for k, q in enumerate(qs, 1):
        if q["type"] == "tf":
            b += [f"**{k}. True or false.** {q['stem']}", ""]
        else:
            b += [f"**{k}.** {q['stem']}", ""] + [f"- {chr(65+j)}. {o}" for j, o in enumerate(q["options"])] + [""]
    a = [f"> [!check]- Answers: {n} questions, pass at {-(-n*4//5)}", f"> **Logic.** {logic}", ">",
         "> | # | Answer | Why |", "> | --- | --- | --- |"]
    a += [f"> | {k} | {q['answer']} | {q['why']} |" for k, q in enumerate(qs, 1)]
    return b + wrap(a)

def unfold(lines):
    """A folded callout as plain markdown, for the answers file: the view renders it once unlocked."""
    out = []
    for l in lines:
        m = re.match(r"^> \[!check\]- (.*)$", l)
        out.append(f"**{m.group(1)}**" if m else re.sub(r"^> ?", "", l))
    return "\n".join(out)

def submit_block(C, K, SUBDIR):
    """The dashboard's Submit work section: a photo button per item that saves the files into the
    vault and flags the item page, so Claude can find and grade every pending submission."""
    tpl = rd(os.path.join(os.path.dirname(os.path.abspath(__file__)), "submit_block.md"))
    for k, v in {"@@TAG@@": C["tag"], "@@KEY@@": K, "@@SUBDIR@@": SUBDIR}.items(): tpl = tpl.replace(k, v)
    return tpl

def main(spec_path):
    S = json.loads(rd(spec_path))
    C = S["course"]; ITEMS = S["items"]; W, ROOT = wiki_dir(C, spec_path); K = C["exam_key"]; TODAY = C["today"]
    PASS = f"{round(C.get('pass', 0.8) * 100)}%"; SOLID = f"{round(C.get('solid', 0.9) * 100)}%"
    P = C["prefix"]; BANK = C.get("bank_name", f"{P}-pretest-bank"); TRACK = C.get("tracker_name", f"{P}-mastery"); DASH = C.get("dashboard_name", f"{P}-dashboard")
    PBANK = C.get("post_bank_name", f"{P}-posttest-bank"); HAS_PB = any(post_banks(i) for i in ITEMS)
    # Paper builds lock answers and add the photo submitter; digital builds (graded in the quiz) don't, unless the spec says so.
    PAPER = "paper" in os.path.basename(os.path.dirname(os.path.abspath(__file__)))
    LOCK = C.get("lock_answers", PAPER); SUBMIT = C.get("submitter", PAPER)
    VW = vault_path(ROOT, os.path.relpath(W, ROOT).replace(os.sep, "/")); ANS = f"{P}-answers"; SUBDIR = f"{VW}/{P}-submissions"
    answers = {}
    def lock(item, key, prop):
        """Swap a folded answer callout for a view that shows it only once `prop` is set on the item page."""
        def wrap(lines):
            if not LOCK: return lines
            answers.setdefault(item, {})[key] = base64.b64encode(unfold(lines).encode("utf-8")).decode("ascii")
            return ["```dataviewjs", f'await dv.view("{VW}/{ANS}", {{item: "{item}", set: "{key}", prop: "{prop}", data: "{VW}/{ANS}.json", track: "{VW}/{TRACK}.md", pass: {C.get("pass", 0.8)}}});', "```"]
        return wrap
    BY = {i["id"]: i for i in ITEMS}
    for i in ITEMS:
        for n in i.get("needs", []): assert n in BY, f"{i['id']} needs unknown {n}"
    order = {}
    for c in range(len(C["cols"])):
        for k, i in enumerate([x for x in ITEMS if x["col"] == c]): order[i["id"]] = c * 100 + k

    # ---- pages that must be created
    for i in ITEMS:
        p = os.path.join(W, i["id"] + ".md")
        if i.get("create_page") and not os.path.exists(p):
            cp = i["create_page"]
            wr(p, "\n".join(["---", f"title: {cp['title']}", f"type: {cp.get('type','concept')}", f"created: {TODAY}",
                f"updated: {TODAY}", f"tags: [{', '.join(cp['tags'])}]", "---", "", f"# {cp['title']}", "", cp["body"].strip(), "",
                "## Related", "", f"- [[{TRACK}]] and [[{BANK}]] — this item's pre-test and mastery status.", ""]))
        assert os.path.exists(p), f"missing page {p}"

    # ---- properties
    for i in ITEMS:
        p = os.path.join(W, i["id"] + ".md"); s = rd(p)
        m = re.match(r"^---\n(.*?)\n---\n", s, re.S); assert m, f"no frontmatter in {p}"
        lines = m.group(1).split("\n"); old = {}; keep = []; skip_list = False
        for l in lines:
            km = re.match(r"^([A-Za-z0-9_]+):\s*(.*)$", l)
            if km:
                skip_list = False
                key = km.group(1)
                if key in [x.format(k=K) for x in MANAGED]:
                    old[key] = km.group(2).strip(); skip_list = (key == "needs"); continue
            elif skip_list and l.startswith("  - "):
                continue
            keep.append(l)
        st = {k: (old.get(k) or "") for k in STATUS_KEYS}
        props = [f"{K}: true", f"order: {order[i['id']]}", f"lecture: \"{i['lec']}\"",
                 f"mastery: {st['mastery'] or 'untested'}", f"pretest_due: {i['due']}",
                 f"pretest_score: {st['pretest_score']}".rstrip(), f"posttest_score: {st['posttest_score']}".rstrip(),
                 f"last_graded: {st['last_graded']}".rstrip(), f"pretest: \"[[{BANK}#{i['title']}]]\""]
        props += (["needs:"] + [f"  - \"[[{n}]]\"" for n in i["needs"]]) if i.get("needs") else ["needs: []"]
        fm = re.sub(r"^updated: .*$", f"updated: {TODAY}", "\n".join(keep + props), flags=re.M)
        wr(p, "---\n" + fm + "\n---\n" + s[m.end():])

    # ---- bank
    b = ["---", f"title: {C['title']} pre-test bank", "type: analysis", f"created: {C['created']}", f"updated: {TODAY}",
         f"tags: [{', '.join(C['tags'])}]", "---", "", f"# {C['title']} pre-test bank", "",
         f"*Written by Claude from the concept pages. Not a course source.*", "", C["bank_intro"].strip(), ""]
    for c, name in enumerate(C["cols"]):
        b += [f"## {name}", ""]
        for i in [x for x in ITEMS if x["col"] == c]:
            needs = ", ".join(f"[[{n}]]" for n in i.get("needs", []))
            b += [f"### {i['title']}", "", f"[[{i['id']}]] · {i['lec']} · about {i['mins']} minutes · pre-test by {i['due']}"
                  + (f" · needs {needs}" if needs else ""), ""]
            if i["format"] == "steps":
                n = len(i["rubric"])
                ru = [f"> [!check]- Rubric: {n} steps, pass at {-(-n*4//5)}",
                      f"> **Logic.** {i['logic']}", ">", "> | # | Step | Expected |", "> | --- | --- | --- |"]
                ru += [f"> | {k} | {r[0]} | {r[1]} |" for k, r in enumerate(i["rubric"], 1)]
                b += [f"**Problem.** {i['q']}", ""] + lock(i["id"], "pre", "pretest_score")(ru)
            else:
                b += question_lines(i["questions"], i["logic"], lock(i["id"], "pre", "pretest_score"))
            post = list(i.get("post", []))
            if post_banks(i): post.append(f"[[{PBANK}#{i['title']}]] ({'; '.join(pb['label'] for pb in post_banks(i))})")
            if post: b += ["", "Post-test from: " + "; ".join(post) + "."]
            b.append("")
    b += ["## Related", "", f"- [[{TRACK}]]", f"- [[{DASH}]]"] + ([f"- [[{PBANK}]]"] if HAS_PB else []) + [f"- [[{r}]]" for r in C["related"]] + [""]
    wr(os.path.join(W, BANK + ".md"), "\n".join(b))

    # ---- post-test bank: fixed post-test sets (a GSI's practice questions, say), when any item has one
    if HAS_PB:
        b = ["---", f"title: {C['title']} post-test bank", "type: analysis", f"created: {C.get('post_bank_created', TODAY)}", f"updated: {TODAY}",
             f"tags: [{', '.join(C['tags'])}]", "---", "", f"# {C['title']} post-test bank", "",
             C.get("post_bank_intro", "Fixed post-test questions, one set per item, answers folded. Take an item's set "
                   "after its pre-test, at least a day later.").strip(), ""]
        for c, name in enumerate(C["cols"]):
            its = [x for x in ITEMS if x["col"] == c and post_banks(x)]
            if not its: continue
            b += [f"## {name}", ""]
            for i in its:
                b += [f"### {i['title']}", ""]
                for pb in post_banks(i):
                    b += [f"[[{i['id']}]] · **{pb['label']}**" + (f" · {pb['source']}" if pb.get("source") else ""), ""]
                    b += question_lines(pb["questions"], i["logic"], lock(i["id"], "post:" + pb["key"], "posttest_score")) + [""]
        b += ["## Related", "", f"- [[{BANK}]]", f"- [[{TRACK}]]", f"- [[{DASH}]]"] + [f"- [[{r}]]" for r in C["related"]] + [""]
        wr(os.path.join(W, PBANK + ".md"), "\n".join(b))

    # ---- locked answers: the data, and the view the banks call
    if LOCK:
        wr(os.path.join(W, ANS + ".json"), json.dumps(answers, indent=1, sort_keys=True) + "\n")
        shutil.copyfile(os.path.join(os.path.dirname(os.path.abspath(__file__)), "answers_view.js"), os.path.join(W, ANS + ".js"))

    # ---- tracker (keep an existing attempt log)
    tp = os.path.join(W, TRACK + ".md"); log_rows = []; ticks = {}
    log_note = C.get("log_note", "Newest last. Marks are Y and N in question or step order.")
    if os.path.exists(tp):
        old = rd(tp); ticks = old_ticks(old)
        if "## Attempt log" in old:
            seg = old.split("## Attempt log", 1)[1].split("\n## ", 1)[0]
            log_rows = [l for l in seg.splitlines() if re.match(r"^\|\s*\d{4}-\d\d-\d\d", l)]
            kept = [l for l in seg.splitlines() if l.strip() and not l.lstrip().startswith("|")]
            if kept and "log_note" not in C: log_note = kept[0].strip()
    t = ["---", f"title: {C['title']} mastery", "type: project", f"created: {C['created']}", f"updated: {TODAY}",
         f"tags: [{', '.join(C['tags'])}]", "---", "", f"# {C['title']} mastery", "", C["tracker_intro"].strip(), "",
         "## Where the data lives", "",
         f"Each item's page carries its status in its properties: `mastery`, `pretest_due`, `pretest_score`,",
         f"`posttest_score`, `last_graded`, `needs` (its prerequisites) and `pretest` (a link to its",
         f"problem on [[{BANK}]]). Every item page has `{K}: true`, which is how [[{DASH}]] finds them.", "",
         "## The loop", "", C["loop"].strip(), "",
         "## Status rules", "",
         f"An attempt **passes** at {PASS} or more. It is **solid**, and passes whatever the reasoning or working,",
         f"when {SOLID} or more of its answers are right; the log then notes what reasoning to shore up.", "",
         "- **untested**: no graded attempt yet.",
         "- **weak**: the latest attempt did not pass.",
         "- **shaky**: one passing attempt.",
         "- **mastered**: two passing attempts on different questions, at least 24 hours apart.", "",
         "## Status", "", "```dataview",
         "TABLE WITHOUT ID file.link AS Item, lecture AS Lecture, mastery AS Status, pretest_due AS \"Pre-test by\", pretest_score AS Pre, posttest_score AS Post, last_graded AS Graded",
         f"FROM #{C['tag']} WHERE {K} SORT order ASC", "```", "",
         "## Attempt log", "", log_note, "",
         "| Date | Item | Problem | Marks | Score | Note |", "| --- | --- | --- | --- | --- | --- |", *log_rows, "",
         *review_lines(C, W, ROOT, ticks),
         "## Schedule", ""]
    for d in C["plan"]:
        t += [f"**{d['dow']} {int(d['date'][-2:])} {d['mon']} — {d['head']}**", ""]
        for x in d["items"]:
            key = f"{x} [due:: {d['date']}]"; box, tail = ticks.get(key, (" ", ""))
            t.append(f"- [{box}] {key}{tail}")
        t.append("")
    t += [C.get("schedule_note", "").strip(), "", "## Related", "", f"- [[{DASH}]]", f"- [[{BANK}]]"] + ([f"- [[{PBANK}]]"] if HAS_PB else []) + [f"- [[{r}]]" for r in C["related"]] + [""]
    wr(tp, "\n".join(t))

    # ---- dashboard
    short = {i["id"]: i["short"] for i in ITEMS}
    tpl = rd(os.path.join(os.path.dirname(os.path.abspath(__file__)), "dashboard_template.md"))
    rep = {"@@TITLE@@": C["title"], "@@CREATED@@": C["created"], "@@TODAY@@": TODAY, "@@TAGS@@": ", ".join(C["tags"]),
           "@@TAG@@": C["tag"], "@@KEY@@": K, "@@EXAM_ISO@@": C["exam"]["when"], "@@EXAM_LABEL@@": C["exam"]["label"],
           "@@EXAM_NAME@@": C["exam"]["name"], "@@COLS@@": json.dumps(C["cols"], ensure_ascii=False),
           "@@SHORT@@": json.dumps(short, ensure_ascii=False), "@@TRACK@@": TRACK, "@@BANK@@": BANK,
           "@@GRADING@@": C["grading"].strip(), "@@QUIZ_BLOCK@@": quiz_block(C), "@@SUBMIT_BLOCK@@": submit_block(C, K, SUBDIR) if SUBMIT else "",
           "@@BANK_NOTE@@": "questions; each rubric unlocks once that attempt is graded" if LOCK else "questions and folded answers", "@@REVIEW_BLOCK@@": review_block(C, TRACK), "@@RELATED@@": "\n".join(f"- [[{r}]]" for r in C["related"])}
    if not rep["@@QUIZ_BLOCK@@"]: tpl = tpl.replace("@@QUIZ_BLOCK@@\n", "")
    if not rep["@@SUBMIT_BLOCK@@"]: tpl = tpl.replace("@@SUBMIT_BLOCK@@\n", "")
    if not rep["@@REVIEW_BLOCK@@"]: tpl = tpl.replace("@@REVIEW_BLOCK@@\n", "")
    for k, v in rep.items(): tpl = tpl.replace(k, v)
    wr(os.path.join(W, DASH + ".md"), tpl)
    print(f"built {DASH}: {len(ITEMS)} items")
    link = obsidian_link(ROOT, os.path.join(W, DASH + ".md"))
    if link: print("open:", link)

if __name__ == "__main__":
    main(sys.argv[1])
