"""Check that every wikilink on a page resolves: the page, the heading, or the raw file.

    python check_links.py <wiki page .md>

Run from the brain root. Vault links to raw files ("Brain/raw/...") are checked
against the brain root, using brain.config.json's vault_subpath. Exits 1 and
lists the broken links if any.
"""
import json, os, re, sys

def main(page):
    sub = ""
    if os.path.exists("brain.config.json"):
        sub = json.load(open("brain.config.json", encoding="utf-8")).get("vault_subpath", "").strip("/")
    s = open(page, encoding="utf-8").read()
    pages = {f[:-3]: os.path.join(d, f) for d, _, fs in os.walk("wiki") for f in fs if f.endswith(".md")}
    bad, n = [], 0
    for link in re.findall(r"\[\[([^\]]+)\]\]", s):
        n += 1; t = link.split("|")[0]
        if sub and t.startswith(sub + "/"):
            if not os.path.exists(t[len(sub) + 1:]): bad.append(t)
            continue
        name, _, head = t.partition("#")
        if name not in pages: bad.append(t); continue
        if head:
            txt = open(pages[name], encoding="utf-8").read().replace("\r\n", "\n")
            if not re.search(r"^#+ " + re.escape(head) + r"\s*$", txt, re.M): bad.append(t)
    print(f"{n} links, {len(bad)} broken" + ("".join(f"\n  {b}" for b in bad)))
    sys.exit(1 if bad else 0)

if __name__ == "__main__":
    main(sys.argv[1])
