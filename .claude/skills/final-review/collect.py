"""Gather everything the final-review dossier needs into one worklist.

    python collect.py specs/<name>.json <attempts dir> [--out worklist.md]

<attempts dir> is the quiz's `attempts` collection saved with ArtifactData
(`out_dir`); pass "-" for a paper course, whose attempts are read from the
mastery page's attempt log instead.

The worklist lists, per item and in the order config.json asks for: the
item's mastery status and attempt trail, every question missed or weakly
reasoned (latest outcome, the correct answer and reference reason, what was
chosen and written, Claude's feedback), the headings on the item's wiki page
that best match each point, and the source files behind the item. Claude
checks the suggested headings against the page before citing them.
"""
import json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
DIG = os.path.join(os.path.dirname(HERE), "obsidian-dashboard-digital")
sys.path.insert(0, DIG)
from build_dashboard import wiki_dir, vault_path, post_banks, rd as _rd

def rd(p): return _rd(p).replace("\r\n", "\n")   # some pages have Windows line endings

from mastery import load_attempts, misfiled, status, is_solid, passed

STOP = set("the a an of and or to in on for is are was were be by with as at from that this which what why how not no it its into than then their there these those most more less best".split())

def cfg():
    return {k: v for k, v in json.loads(rd(os.path.join(HERE, "config.json"))).items() if not k.startswith("_")}

def toks(s): return {w for w in re.findall(r"[a-z0-9][a-z0-9\-]+", s.lower()) if w not in STOP and len(w) > 2}

def sections(text):
    """(heading, body) for each ## / ### heading of a wiki page, frontmatter stripped."""
    text = re.sub(r"^---\n.*?\n---\n", "", text, count=1, flags=re.S)
    out, head, buf = [], None, []
    for l in text.splitlines():
        m = re.match(r"^#{2,3} (.+)$", l)
        if m:
            if head: out.append((head, "\n".join(buf)))
            head, buf = m.group(1).strip(), []
        elif head: buf.append(l)
    if head: out.append((head, "\n".join(buf)))
    return [(h, b) for h, b in out if h not in ("Related", "Sources")]

SKIP_PAGE = re.compile(r"-(pretest-bank|posttest-bank|mastery|dashboard|final-review|guide)$")

def cluster_sections(W):
    """Every heading of every page in the course folder, except the generated study pages."""
    out = []
    for f in sorted(os.listdir(W)):
        if f.endswith(".md") and not SKIP_PAGE.search(f[:-3]):
            out += [(f[:-3], h, toks(h + " " + b)) for h, b in sections(rd(os.path.join(W, f)))]
    return out

def best_headings(item_id, secs, q, n):
    """The n headings across the course folder whose text best matches the question, answer and reason.
    The item's own page gets a small bonus, since that is where the point should live."""
    want = toks(q["stem"] + " " + q.get("why", "") + " " + correct_text(q))
    scored = sorted(((len(want & t) + (1 if pg == item_id else 0), pg, h) for pg, h, t in secs), reverse=True)
    return [f"[[{pg}#{h}]]" for s, pg, h in scored[:n] if s > 1]

def correct_text(q):
    if q["type"] == "tf" or not q.get("options"): return q["answer"]
    k = ord(q["answer"]) - 65
    return q["options"][k] if 0 <= k < len(q["options"]) else q["answer"]

def source_links(W, ROOT, item_id):
    """Wiki source pages named in the item page's Sources section, with their raw files as vault links."""
    p = os.path.join(W, item_id + ".md")
    if not os.path.exists(p): return []
    text = rd(p); m = re.search(r"^## Sources\n(.*?)(?=^## |\Z)", text, re.S | re.M)
    names = re.findall(r"\[\[([^\]|#]+)", m.group(1)) if m else []
    pages = {f[:-3]: os.path.join(d, f) for d, _, fs in os.walk(os.path.join(ROOT, "wiki")) for f in fs if f.endswith(".md")}
    out = []
    for nm in dict.fromkeys(names):
        if nm not in pages: continue
        fm = re.match(r"^---\n(.*?)\n---\n", rd(pages[nm]), re.S)
        raws = re.findall(r'^\s+-\s+"?([^"\n]+?)"?\s*$', fm.group(1).split("raw_files:", 1)[1].split("\n", 1)[1] if fm and "raw_files:" in fm.group(1) else "", re.M)
        raws = [r for r in raws if r.startswith("raw/") and os.path.exists(os.path.join(ROOT, r))]
        out.append((nm, [f"[[{vault_path(ROOT, r)}|{os.path.basename(r)}]]" for r in raws]))
    return out

def set_questions(item, a):
    if a.get("questions"): return a["questions"], "new questions" if str(a["setKey"]).startswith("gen-") else a["setKey"]
    if a["kind"] == "pretest": return item["questions"], "pre-test"
    for b in post_banks(item):
        if b["key"] == a["setKey"]: return b["questions"], b["label"]
    return None, a["setKey"]

def label_of(item, a):
    if a["kind"] == "pretest": return "pre-test"
    for b in post_banks(item):
        if b["key"] == a["setKey"]: return b["label"]
    return "new questions"

def main(spec_path, att_dir, out_path=None):
    K = cfg(); S = json.loads(rd(spec_path)); C = S["course"]; W, ROOT = wiki_dir(C, spec_path)
    atts = load_attempts(att_dir) if att_dir != "-" else []
    items = S["items"]; rank = {s: k for k, s in enumerate(K["order"])}
    rows = []
    for idx, it in enumerate(items):
        mine = [a for a in atts if a["item"] == it["id"] and not misfiled(a, it)]
        st = status(mine, C) if att_dir != "-" else "see mastery log"
        hist = {}
        for a in mine:
            qs, _ = set_questions(it, a)
            if not qs or len(qs) != len(a.get("answers", [])): continue
            for q, ans in zip(qs, a["answers"]):
                hist.setdefault(q["stem"], (q, []))[1].append((a, ans))
        points = []
        for stem, (q, h) in hist.items():
            a, ans = h[-1]
            blank = not ans.get("choice")
            wrong = not ans.get("letterOk")
            weak = ans.get("reasonScore", 5) < K["reason_below"]
            ever = any((not x.get("letterOk")) or x.get("reasonScore", 5) < K["reason_below"] for _, x in h)
            if wrong and blank and not K["include_blanks"]: continue
            if not wrong and weak and not K["include_weak_reasons"]: continue
            kind = "blank" if wrong and blank else "wrong" if wrong else "weak reason" if weak else "fixed" if ever else None
            if not kind or (kind == "fixed" and not K["include_fixed"]): continue
            points.append(dict(kind=kind, q=q, a=a, ans=ans, tries=len(h)))
        order_k = {"wrong": 0, "blank": 1, "weak reason": 2, "fixed": 3}
        points.sort(key=lambda p: (order_k[p["kind"]], p["a"]["ts"]))
        if st == "mastered" and K["skip_mastered_without_misses"] and not [p for p in points if p["kind"] != "fixed"]: continue
        rows.append((rank.get(st, len(rank)), it.get("col", 0), idx, it, st, mine, points))
    rows.sort(key=lambda r: r[:3])
    secs = cluster_sections(W)

    o = [f"# Worklist: {C['title']}", "", f"Exam: {C['exam']['label']}", f"Config: {json.dumps(K)}", ""]
    counts = {}
    for r in rows: counts[r[4]] = counts.get(r[4], 0) + 1
    o += ["Status counts (items shown): " + ", ".join(f"{k} {v}" for k, v in counts.items()), ""]
    for _, _, _, it, st, mine, points in rows:
        trail = "; ".join(f"{a['date']} {label_of(it, a)} {round(a['score']*100)}%" + (" solid" if is_solid(a, C) and a['score'] < C.get('pass', 0.8) else "")
                          + ("" if passed(a, C) else " (not a pass)") for a in mine) or "no attempts"
        o += [f"## {it['title']} — [[{it['id']}]] — {st}", "", f"Lecture: {it.get('lec', '')}. Attempts: {trail}.", f"Logic: {it.get('logic', '')}", ""]
        for p in points[:K["max_points_per_step"]]:
            q, a, ans = p["q"], p["a"], p["ans"]
            o += [f"### [{p['kind']}] {q['stem']}",
                  f"- Correct: {q['answer']} — {correct_text(q)}",
                  f"- Reference reason: {q.get('why', '')}",
                  f"- You chose: {ans.get('choice') or 'blank'}; reason score {ans.get('reasonScore')}; seen {p['tries']}x; last {a['date']} ({label_of(it, a)})",
                  f"- You wrote: {ans.get('reasoning') or '(blank)'}",
                  f"- Feedback: {ans.get('feedback') or ''}",
                  f"- Heading candidates: {', '.join(best_headings(it['id'], secs, q, K['heading_candidates'])) or 'none; read the page'}",
                  f"- Zoe/handout ref: {m.group(1) if (m := re.search(r'\(((?:L\d|handout)[^)]*)\)\s*$', q['stem'])) else ''}", ""]
        if len(points) > K["max_points_per_step"]: o += [f"({len(points) - K['max_points_per_step']} more points not shown; raise max_points_per_step)", ""]
        o += ["Sources behind this item:"] + [f"- [[{nm}]]: " + (", ".join(raws) or "no raw file") for nm, raws in source_links(W, ROOT, it["id"])]
        rv = [f"- {x['title']}: [[{vault_path(ROOT, x['file'])}|file]] ({x['page']})" for g in C.get("review", []) for x in g["items"]
              if x.get("file") and x.get("page") in [it["id"]] + [nm for nm, _ in source_links(W, ROOT, it["id"])]]
        o += (["Review-list entries tied to it:"] + rv if rv else []) + [""]
    text = "\n".join(o)
    if out_path:
        with open(out_path, "w", encoding="utf-8") as f: f.write(text)
        print("wrote", out_path, len(rows), "items,", sum(len(r[6]) for r in rows), "points")
    else: print(text)

if __name__ == "__main__":
    args = [x for x in sys.argv[1:] if not x.startswith("--")]
    out = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else None
    if out: args = [x for x in args if x != out]
    main(args[0], args[1], out)
