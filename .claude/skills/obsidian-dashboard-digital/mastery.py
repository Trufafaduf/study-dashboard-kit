"""Recompute every item's mastery from all its saved attempts.

    python mastery.py specs/<name>.json <attempts dir> [--write]

<attempts dir> holds one JSON file per attempt, as ArtifactData writes them with
`out_dir` (a list of the `attempts` collection). Prints each item's status and
the attempts behind it; --write also sets `mastery` on the item pages.

Rules, as in the quiz: an attempt passes when its score reaches the spec's
`pass` (default 0.8) or its answers alone reach `solid` (default 0.9). weak:
the latest did not pass; shaky: one pass; mastered: two passes on different
question sets (setKey) at least 24 hours apart. A pre-test attempt whose answer
count differs from the item's question count was saved under the wrong item (an
old quiz bug) and is skipped.
"""
import glob, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_dashboard import wiki_dir

def load_attempts(folder):
    out = []
    for f in glob.glob(os.path.join(folder, "**", "*.json"), recursive=True):
        with open(f, encoding="utf-8") as fh: d = json.load(fh)
        a = d.get("data", d); a["_id"] = d.get("id", os.path.basename(f)[:-5]); out.append(a)
    return sorted(out, key=lambda a: a["ts"])

def is_solid(a, C): return isinstance(a.get("mcqCorrect"), int) and a["total"] and a["mcqCorrect"] / a["total"] >= C.get("solid", 0.9)
def passed(a, C): return a["score"] >= C.get("pass", 0.8) or is_solid(a, C)

def misfiled(a, item):
    return a["kind"] == "pretest" and item is not None and len(a.get("answers", [])) != len(item["questions"])

def status(atts, C):
    if not atts: return "untested"
    if not passed(atts[-1], C): return "weak"
    ps = [a for a in atts if passed(a, C)]
    if len(ps) >= 2 and len({a["setKey"] for a in ps}) >= 2 and ps[-1]["ts"] - ps[0]["ts"] >= 864e5: return "mastered"
    return "shaky"

def main(spec_path, folder, write=False):
    S = json.load(open(spec_path, encoding="utf-8")); C = S["course"]; BY = {i["id"]: i for i in S["items"]}
    W, _ = wiki_dir(C, spec_path); atts = load_attempts(folder); res = {}
    for iid, item in BY.items():
        mine = [a for a in atts if a["item"] == iid and not misfiled(a, item)]
        res[iid] = status(mine, C)
        trail = ", ".join(f"{a['date']} {a['kind'][:4]} {round(a['score']*100)}%" + (" solid" if is_solid(a, C) and a["score"] < C.get("pass", 0.8) else "")
                          for a in mine)
        print(f"{res[iid]:9} {iid}: {trail or '-'}")
        if write and mine:
            p = os.path.join(W, iid + ".md"); s = open(p, encoding="utf-8").read()
            s2 = re.sub(r"^mastery: .*$", f"mastery: {res[iid]}", s, count=1, flags=re.M)
            if s2 != s:
                with open(p, "w", encoding="utf-8", newline="\n") as fh: fh.write(s2)
    skipped = [a["_id"] for a in atts if misfiled(a, BY.get(a["item"]))]
    if skipped: print("skipped as misfiled:", ", ".join(skipped))
    return res

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], "--write" in sys.argv)
