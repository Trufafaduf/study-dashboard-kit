"""Build the claude.ai mastery board for a paper spec.

    python build_board.py specs/<name>.json

Writes out/<prefix>-board.html next to the spec (gitignored), for publishing with
the Artifact tool to the spec's "board": {"url": ...}. It is a snapshot of the
wiki: status and scores from the item pages' properties, attempts from the
mastery page's attempt log, plan ticks from its schedule.

**Rubrics are locked until graded.** An item's rubric goes into the page only
once its page has a pretest_score. Before that the page carries the number of
steps and nothing else, so neither the board nor its source can show it.
Rebuild and republish after every grading so the graded item's rubric appears.
"""
import datetime, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_dashboard import wiki_dir, vault_path, old_ticks, rd

HERE = os.path.dirname(os.path.abspath(__file__))

def props(path):
    """The item page's frontmatter as {key: raw value} (scalars only)."""
    m = re.match(r"^---\n(.*?)\n---\n", rd(path), re.S)
    out = {}
    for l in (m.group(1).split("\n") if m else []):
        km = re.match(r"^([A-Za-z0-9_]+):\s*(.*)$", l)
        if km: out[km.group(1)] = km.group(2).strip().strip('"')
    return out

def attempt_rows(track_path):
    """Rows of the mastery page's attempt log: | date | [[item]] | problem | marks | score | note |."""
    if not os.path.exists(track_path): return []
    t = rd(track_path)
    if "## Attempt log" not in t: return []
    seg = t.split("## Attempt log", 1)[1].split("\n## ", 1)[0]
    rows = []
    for l in seg.splitlines():
        if not re.match(r"^\|\s*\d{4}-\d\d-\d\d", l): continue
        c = [x.strip() for x in l.strip().strip("|").split("|")]
        if len(c) < 6: continue
        item = re.sub(r"^\[\[([^\]|#]+).*$", r"\1", c[1])
        rows.append(dict(item=item, date=c[0], problem=c[2], marks=c[3], score=c[4], note=" | ".join(c[5:])))
    return rows

def main(spec_path):
    S = json.loads(rd(spec_path)); C = S["course"]; W, ROOT = wiki_dir(C, spec_path)
    P = C["prefix"]; TRACK = C.get("tracker_name", f"{P}-mastery"); B = C.get("board", {})
    PASS = C.get("pass", 0.8)
    rows = attempt_rows(os.path.join(W, TRACK + ".md"))
    ticks = old_ticks(rd(os.path.join(W, TRACK + ".md"))) if os.path.exists(os.path.join(W, TRACK + ".md")) else {}
    nodes = []; locked = 0
    for i in S["items"]:
        pr = props(os.path.join(W, i["id"] + ".md"))
        graded = bool(pr.get("pretest_score"))
        if i["format"] == "steps":
            q, full = i["q"], [dict(s=r[0], e=r[1]) for r in i["rubric"]]
        else:
            q = " ".join(f"({k}) {x['stem']}" for k, x in enumerate(i["questions"], 1))
            full = [dict(s=x["stem"], e=f"{x['answer']}: {x['why']}") for x in i["questions"]]
        if not graded: locked += 1
        nodes.append(dict(id=i["id"], col=i["col"], title=i["title"], short=i["short"], lec=i["lec"], mins=i["mins"],
                          pre=i.get("needs", []), logic=i["logic"], q=q, steps=len(full),
                          rubric=full if graded else None,          # the lock: absent until graded
                          post=i.get("post", []), due=i["due"],
                          st=dict(status=pr.get("mastery") or "untested", pre=pr.get("pretest_score") or "–",
                                  post=pr.get("posttest_score") or "–", last=pr.get("last_graded") or "–"),
                          attempts=[r for r in rows if r["item"] == i["id"]]))
    plan = [dict(date=d["date"], dow=d["dow"], mon=d["mon"], head=d["head"],
                 items=[dict(t=x, done=ticks.get(f"{x} [due:: {d['date']}]", (" ", ""))[0] != " ") for x in d["items"]])
            for d in C["plan"]]
    cfg = os.path.join(ROOT, "brain.config.json")
    vault = json.loads(rd(cfg)).get("vault_name", "") if os.path.exists(cfg) else ""
    data = dict(prefix=P, built=str(datetime.date.today()), exam=C["exam"], cols=C["cols"], **{"pass": PASS},
                gradeLabel=B.get("grade_label", f"Grade {C['title']} pre-test"), nodes=nodes, plan=plan, vault=vault,
                wikiDir=vault_path(ROOT, os.path.relpath(W, ROOT).replace(os.sep, "/")) + "/")
    esc = lambda x: x.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    html = rd(os.path.join(HERE, "board_template.html"))
    for k, v in {"@@BOARD_TITLE@@": B.get("title", f"{C['title']} board"), "@@EYEBROW@@": B.get("eyebrow", C["title"]),
                 "@@HEADING@@": B.get("heading", f"{C['exam']['name']} mastery"),
                 "@@SUB@@": B.get("sub", "Every item the exam draws on. Pre-test each one cold, submit a photo of your work for grading, and drill whatever comes back weak."),
                 "@@EXAM_NAME@@": C["exam"]["name"], "@@SUBMIT_CMD@@": f"grade {C['tag']} submissions",
                 "@@PASS@@": f"{round(PASS * 100)}%", "@@TRACK@@": TRACK,
                 "@@POST_NOTE@@": B.get("post_note", "Post-tests come from each item's list, on a different problem from its pre-test.")}.items():
        html = html.replace(k, esc(v) if k in ("@@BOARD_TITLE@@", "@@EYEBROW@@", "@@HEADING@@", "@@SUB@@", "@@EXAM_NAME@@", "@@POST_NOTE@@") else v)
    html = html.replace("/*__DATA__*/null", json.dumps(data, ensure_ascii=False).replace("</", "<\\/"))
    assert "@@" not in html, "leftover placeholder in board"
    out_dir = os.path.join(os.path.dirname(os.path.abspath(spec_path)), "out"); os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, P + "-board.html")
    with open(out, "w", encoding="utf-8") as f: f.write(html)
    print(f"wrote {out}: {len(nodes)} items, {len(nodes) - locked} rubrics unlocked, {locked} locked")
    if B.get("url"): print("publish to:", B["url"])

if __name__ == "__main__":
    main(sys.argv[1])
