#!/usr/bin/env python3
"""Convert cached Notion blocks (from notion_fetch.py) into Jekyll + just-the-docs
Markdown pages under docs/, downloading images into assets/images/.

Run after notion_fetch.py. Idempotent: rewrites docs/ and assets/images/.
"""
import json
import glob
import os
import re
import sys
import time
import hashlib
import urllib.parse
import urllib.request
import urllib.error

# High-confidence secret patterns to scrub from migrated content. The source
# Notion notes contain real credentials (e.g. an OAuth tutorial); never publish
# them. Masking here keeps the migration reproducible and push-protection clean.
SECRET_PATTERNS = [
    (re.compile(r"GOCSPX-[A-Za-z0-9_\-]{10,}"), "GOCSPX-REDACTED_CLIENT_SECRET"),
    (re.compile(r"\d{6,}-[a-z0-9]{16,}\.apps\.googleusercontent\.com"),
     "YOUR_CLIENT_ID.apps.googleusercontent.com"),
    (re.compile(r"AIza[0-9A-Za-z_\-]{35}"), "AIza_REDACTED_API_KEY"),
    (re.compile(r"AKIA[0-9A-Z]{16}"), "AKIA_REDACTED_ACCESS_KEY"),
    (re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}"), "REDACTED_GITHUB_TOKEN"),
    (re.compile(r"xox[baprs]-[A-Za-z0-9\-]{10,}"), "REDACTED_SLACK_TOKEN"),
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?"
                r"-----END [A-Z ]*PRIVATE KEY-----"),
     "-----REDACTED PRIVATE KEY-----"),
]


def scrub_secrets(text):
    for pat, repl in SECRET_PATTERNS:
        text = pat.sub(repl, text)
    return text


HERE = os.path.dirname(__file__)
CACHE = os.path.join(HERE, "cache")
ROOT_DIR = os.path.abspath(os.path.join(HERE, ".."))
DOCS = os.path.join(ROOT_DIR, "docs")
IMG_DIR = os.path.join(ROOT_DIR, "assets", "images")
SITE = os.environ.get("NOTION_SITE", "https://woolen-purchase-6e3.notion.site")

tree = json.load(open(os.path.join(CACHE, "tree.json")))
ROOT_ID = next(i for i, n in tree.items() if n.get("parent") is None and i != "None")

# Merge every cached page's blocks into one global store.
BLOCKS = {}
for f in glob.glob(os.path.join(CACHE, "*.json")):
    if f.endswith("tree.json"):
        continue
    for bid, v in json.load(open(f)).items():
        BLOCKS.setdefault(bid, v)

PAGE_IDS = set(tree.keys()) - {"None"}


# ---------------------------------------------------------------- helpers
def short(pid):
    return pid.replace("-", "")[:8]


def depth(pid):
    d = 0
    cur = tree[pid]["parent"]
    while cur is not None:
        d += 1
        cur = tree.get(cur, {}).get("parent")
    return d


def ancestors(pid):
    """Return list of ancestor ids from top category down to immediate parent."""
    chain = []
    cur = tree[pid]["parent"]
    while cur is not None and cur != ROOT_ID:
        chain.append(cur)
        cur = tree.get(cur, {}).get("parent")
    chain.reverse()
    return chain


def slugify(text, fallback):
    text = (text or "").strip().lower()
    text = re.sub(r"[\s/]+", "-", text)
    text = re.sub(r"[^0-9a-z\uac00-\ud7a3\-_]", "", text)
    text = re.sub(r"-{2,}", "-", text).strip("-")
    return text or fallback


# Unique nav title + slug/permalink per page.
_nav_titles = {}
_used_titles = set()
_slugs = {}
_used_slugs = set()


def raw_title(pid):
    t = tree[pid]["title"] or "(untitled)"
    return re.sub(r"\s+", " ", t).strip()


def nav_title(pid):
    if pid in _nav_titles:
        return _nav_titles[pid]
    base = raw_title(pid)
    title = base
    if title in _used_titles:
        title = f"{base} ({short(pid)})"
    _used_titles.add(title)
    _nav_titles[pid] = title
    return title


def permalink(pid):
    if pid in _slugs:
        return _slugs[pid]
    s = slugify(raw_title(pid), short(pid))
    if s in _used_slugs:
        s = f"{s}-{short(pid)}"
    _used_slugs.add(s)
    link = f"/notes/{s}/"
    _slugs[pid] = link
    return link


# ---------------------------------------------------------------- images
os.makedirs(IMG_DIR, exist_ok=True)
_img_cache = {}


def download_image(v):
    src = ""
    try:
        src = v["properties"]["source"][0][0]
    except Exception:
        return None
    if not src:
        return None
    if v["id"] in _img_cache:
        return _img_cache[v["id"]]
    if src.startswith("http") and "amazonaws.com" not in src and "notion" not in src:
        url = src  # external, fetch directly
    else:
        enc = urllib.parse.quote(src, safe="")
        url = (f"{SITE}/image/{enc}?table=block&id={v['id']}"
               f"&cache=v2&spaceId={v.get('space_id','')}")
    ext = os.path.splitext(urllib.parse.urlparse(src).path)[1].lower()
    if ext not in (".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"):
        ext = ".png"
    name = f"{v['id'].replace('-','')}{ext}"
    dest = os.path.join(IMG_DIR, name)
    rel = f"/assets/images/{name}"
    if os.path.exists(dest):
        _img_cache[v["id"]] = rel
        return rel
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                data = r.read()
            with open(dest, "wb") as fh:
                fh.write(data)
            _img_cache[v["id"]] = rel
            return rel
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
            print(f"  img retry {attempt+1}: {e}", file=sys.stderr)
            time.sleep(2 ** attempt)
    print(f"  IMG FAIL {v['id']} {src}", file=sys.stderr)
    return None


# ---------------------------------------------------------------- rich text
def esc_inline(t):
    # escape characters that would break inline markdown/liquid in prose
    return t.replace("{{", "&#123;&#123;").replace("{%", "&#123;%")


def rich(segs, in_table=False):
    if not segs:
        return ""
    out = []
    for seg in segs:
        if not seg:
            continue
        text = seg[0]
        decos = seg[1] if len(seg) > 1 and seg[1] else []
        types = [d[0] for d in decos]
        # page mention
        if "p" in types:
            for d in decos:
                if d[0] == "p" and d[1] in PAGE_IDS:
                    out.append(f"[{nav_title(d[1])}]({permalink(d[1])})")
                    break
            else:
                out.append("(page)")
            continue
        if text == "⁍" or "e" in types:  # equation
            for d in decos:
                if d[0] == "e":
                    out.append(f"\\({d[1]}\\)")
                    break
            continue
        piece = text
        if in_table:
            piece = piece.replace("\n", "<br>").replace("|", "\\|")
        piece = esc_inline(piece)
        if "c" in types:
            code = text.replace("`", "\u200b`")
            piece = f"`{code}`"
        else:
            if "s" in types:
                piece = f"~~{piece}~~"
            if "b" in types:
                piece = f"**{piece}**"
            if "i" in types:
                piece = f"_{piece}_"
        for d in decos:
            if d[0] == "a":
                piece = f"[{piece}]({d[1]})"
                break
        out.append(piece)
    return "".join(out)


def prop_text(v, key="title"):
    return rich((v.get("properties", {}) or {}).get(key, []))


# ---------------------------------------------------------------- blocks
def children_ids(v):
    return [c for c in v.get("content", []) if c in BLOCKS]


def indent(text, n):
    if n <= 0:
        return text
    pad = " " * n
    return "\n".join((pad + line if line else line) for line in text.split("\n"))


def render_children(v, level=0, skip_pages=True):
    parts = []
    for cid in children_ids(v):
        cv = BLOCKS[cid]
        if skip_pages and cv.get("type") == "page":
            continue
        r = render_block(cv, level)
        if r is not None and r != "":
            parts.append(r)
    return "\n\n".join(parts)


def blockquote(text):
    return "\n".join((f"> {line}" if line else ">") for line in text.split("\n"))


def render_block(v, level=0):
    t = v.get("type")
    if t in ("header", "sub_header", "sub_sub_header"):
        hashes = {"header": "##", "sub_header": "###", "sub_sub_header": "####"}[t]
        return f"{hashes} {prop_text(v)}"
    if t == "text":
        txt = prop_text(v)
        return txt.replace("\n", "  \n") if txt else ""
    if t in ("bulleted_list", "numbered_list", "to_do"):
        marker = "1." if t == "numbered_list" else "-"
        if t == "to_do":
            checked = (v.get("properties", {}).get("checked", [[""]])[0][0] == "Yes")
            marker = "- [x]" if checked else "- [ ]"
        line = prop_text(v).replace("\n", " ")
        block = f"{marker} {line}"
        kids = render_children(v, level + 1)
        if kids:
            block += "\n" + indent(kids, 2)
        return indent(block, level * 2) if level else block
    if t == "quote":
        return blockquote(prop_text(v).replace("\n", "  \n"))
    if t == "callout":
        icon = v.get("format", {}).get("page_icon", "")
        head = (icon + " " if icon and len(icon) <= 2 else "") + prop_text(v)
        kids = render_children(v)
        body = head + ("\n\n" + kids if kids else "")
        return blockquote(body)
    if t == "toggle":
        summary = prop_text(v)
        kids = render_children(v)
        return (f"<details markdown=\"1\"><summary>{summary}</summary>\n\n"
                f"{kids}\n\n</details>")
    if t == "code":
        lang = (v.get("properties", {}).get("language", [["text"]])[0][0] or "text")
        lang = lang.lower().replace(" ", "").replace("plaintext", "text")
        code = "".join(s[0] for s in v.get("properties", {}).get("title", []))
        return "{% raw %}\n```" + lang + "\n" + code + "\n```\n{% endraw %}"
    if t == "divider":
        return "---"
    if t == "image":
        rel = download_image(v)
        cap = prop_text(v, "caption")
        if not rel:
            return f"*(image unavailable){(' — ' + cap) if cap else ''}*"
        md = f"![{cap or 'image'}]({rel})"
        return md + (f"\n\n*{cap}*" if cap else "")
    if t == "table":
        return render_table(v)
    if t == "bookmark":
        link = v.get("properties", {}).get("link", [[""]])[0][0]
        title = prop_text(v) or link
        return f"[{title}]({link})" if link else ""
    if t == "external_object_instance":
        uri = v.get("format", {}).get("uri", "")
        return f"[{uri}]({uri})" if uri else ""
    if t == "file":
        src = v.get("properties", {}).get("source", [[""]])[0][0]
        name = prop_text(v) or src
        return f"[{name}]({src})" if src else ""
    if t == "alias":
        tgt = v.get("format", {}).get("alias_pointer", {}).get("id", "")
        if tgt in PAGE_IDS:
            return f"[{nav_title(tgt)}]({permalink(tgt)})"
        return ""
    if t in ("column_list", "column"):
        return render_children(v, level)
    if t == "collection_view":
        return ""  # embedded DB view; skipped
    if t == "page":
        return ""  # handled by nav / children list
    if t == "divider":
        return "---"
    # fallback: render any text we can find
    txt = prop_text(v)
    return txt if txt else ""


def render_table(v):
    rows = [BLOCKS[c] for c in v.get("content", []) if c in BLOCKS]
    if not rows:
        return ""
    col_order = v.get("format", {}).get("table_block_column_order")
    if not col_order:
        col_order = list((rows[0].get("properties", {}) or {}).keys())
    has_header = v.get("format", {}).get("table_block_column_header", False)

    def cells(r):
        p = r.get("properties", {}) or {}
        return [rich(p.get(c, []), in_table=True) or " " for c in col_order]

    out = []
    body = rows
    if has_header:
        out.append("| " + " | ".join(cells(rows[0])) + " |")
        out.append("| " + " | ".join(["---"] * len(col_order)) + " |")
        body = rows[1:]
    else:
        out.append("| " + " | ".join([" "] * len(col_order)) + " |")
        out.append("| " + " | ".join(["---"] * len(col_order)) + " |")
    for r in body:
        out.append("| " + " | ".join(cells(r)) + " |")
    return "\n".join(out)


# ---------------------------------------------------------------- front matter
def yaml_str(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def front_matter(pid):
    node = tree[pid]
    d = depth(pid)
    anc = ancestors(pid)
    fm = ["---", "title: " + yaml_str(nav_title(pid))]
    if d == 1:
        fm.append(f"nav_order: {node['order']}")
    elif d == 2:
        fm.append("parent: " + yaml_str(nav_title(anc[0])))
        fm.append(f"nav_order: {node['order']}")
    else:  # d >= 3, flatten under level-2 ancestor
        # ponytail: just-the-docs nav supports 3 levels; deeper pages are
        # flattened under their top-2 ancestors. Full content is preserved.
        fm.append("grand_parent: " + yaml_str(nav_title(anc[0])))
        fm.append("parent: " + yaml_str(nav_title(anc[1])))
        fm.append(f"nav_order: {node['order']}")
    if node["children"]:
        fm.append("has_children: true")
    fm.append("permalink: " + yaml_str(permalink(pid)))
    fm.append("---")
    return "\n".join(fm)


# ---------------------------------------------------------------- main
def main():
    # reset docs
    if os.path.isdir(DOCS):
        for f in glob.glob(os.path.join(DOCS, "*.md")):
            os.remove(f)
    os.makedirs(DOCS, exist_ok=True)

    # pre-assign nav titles/permalinks in a stable order (top-down) so that
    # parents get the clean title before children can collide with it.
    ordered = sorted(PAGE_IDS, key=lambda p: (depth(p), raw_title(p)))
    for pid in ordered:
        nav_title(pid)
        permalink(pid)

    count = 0
    for pid in PAGE_IDS:
        if pid == ROOT_ID:
            continue
        v = BLOCKS.get(pid)
        if not v:
            continue
        body = scrub_secrets(render_children(v))
        fname = permalink(pid).strip("/").split("/")[-1] + ".md"
        with open(os.path.join(DOCS, fname), "w") as fh:
            fh.write(front_matter(pid) + "\n\n" + body + "\n")
        count += 1
        if count % 20 == 0:
            print(f"  wrote {count} pages...", file=sys.stderr)

    # home page from root body
    rv = BLOCKS[ROOT_ID]
    home_body = scrub_secrets(render_children(rv))
    home = ("---\n"
            "title: Home\n"
            "layout: default\n"
            "nav_order: 0\n"
            "---\n\n"
            "# Geun's Study\n\n" + home_body + "\n")
    with open(os.path.join(ROOT_DIR, "index.md"), "w") as fh:
        fh.write(home)
    print(f"done. wrote {count} note pages + home. images: {len(_img_cache)}",
          file=sys.stderr)


if __name__ == "__main__":
    main()
