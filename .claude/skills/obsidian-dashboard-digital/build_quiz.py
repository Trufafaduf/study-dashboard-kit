"""Build the quiz artifact page for a digital spec.

    python build_quiz.py specs/<name>.json

Writes out/<prefix>-quiz.html with every item's questions, answers and reasons
(answers and reasons sealed, so the page and its source show them only after grading),
plus any fixed post-test sets ("post_bank" / "post_banks") and the text of the item's wiki page
(for Claude to write post-test questions from). Publish it with the Artifact tool, capabilities {db: {}, sample: {}}.

Output goes to an out/ folder next to the spec (gitignored: the page embeds the
answers). Wiki paths resolve as in build_dashboard.py.
"""
import base64, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_dashboard import wiki_dir, post_banks

HERE = os.path.dirname(os.path.abspath(__file__))
PAGE_CHARS = 7000

def rd(p):
    with open(p, encoding="utf-8") as f: return f.read()

def page_text(path):
    s = rd(path)
    s = re.sub(r"^---\n.*?\n---\n", "", s, count=1, flags=re.S)
    s = s.split("\n## Related", 1)[0]
    s = re.sub(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|([^\]]+))?\]\]", lambda m: m.group(2) or m.group(1).replace("-", " "), s)
    return s.strip()[:PAGE_CHARS]

def seal(qs):
    """Questions with answer and why sealed (reversed base64 of JSON), so the page source doesn't show them."""
    out = []
    for q in qs:
        q = dict(q); k = {"answer": q.pop("answer"), "why": q.pop("why")}
        q["sealed"] = base64.b64encode(json.dumps(k, ensure_ascii=False).encode("utf-8")).decode("ascii")[::-1]
        out.append(q)
    return out

def main(spec_path):
    S = json.loads(rd(spec_path)); C = S["course"]; W, _ = wiki_dir(C, spec_path)
    items = []
    for i in S["items"]:
        assert i["format"] == "mcq", f"{i['id']}: the digital quiz takes mcq items only"
        items.append(dict(id=i["id"], title=i["title"], col=i["col"], lec=i["lec"], mins=i["mins"], due=i["due"],
                          logic=i["logic"], questions=seal(i["questions"]),
                          post_banks=[dict(b, questions=seal(b["questions"])) for b in post_banks(i)],
                          page=page_text(os.path.join(W, i["id"] + ".md"))))
    data = dict(course=dict(prefix=C["prefix"], title=C["title"], eyebrow=C["quiz"]["eyebrow"], heading=C["quiz"]["heading"],
                            subject=C["quiz"]["subject"], exam=C["exam"], cols=C["cols"],
                            **{"pass": C.get("pass", 0.8), "solid": C.get("solid", 0.9)}), items=items)
    html = rd(os.path.join(HERE, "quiz_template.html"))
    html = html.replace("@@PAGE_TITLE@@", C["quiz"]["page_title"])
    html = html.replace("/*__DATA__*/null", json.dumps(data, ensure_ascii=False).replace("</", "<\\/"))
    out_dir = os.path.join(os.path.dirname(os.path.abspath(spec_path)), "out")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, C["prefix"] + "-quiz.html")
    with open(out, "w", encoding="utf-8") as f: f.write(html)
    print("wrote", out, len(html), "bytes,", len(items), "items")

if __name__ == "__main__":
    main(sys.argv[1])
