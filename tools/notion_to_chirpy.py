#!/usr/bin/env python3
"""Convert cached Notion blocks into Chirpy Jekyll posts under _posts/.

Reuses the block->markdown rendering from notion_to_md.py, but emits Chirpy
front matter (title/date/categories/tags) and maps the Notion page hierarchy to
Chirpy's 2-level categories (deeper levels become tags). Empty container pages
get an auto-generated index list of their child notes, so category landing
pages are never blank.

Run after notion_fetch.py. Idempotent: rewrites _posts/.
"""
import os
import re
import glob
import datetime

import notion_to_md as N

HERE = os.path.dirname(__file__)
ROOT_DIR = os.path.abspath(os.path.join(HERE, ".."))
POSTS = os.path.join(ROOT_DIR, "_posts")

# ---- Chirpy permalink/title mapping (override just-the-docs links in N) ----
_slugs = {}
_used = set()


def slug_of(pid):
    if pid in _slugs:
        return _slugs[pid]
    s = N.slugify(N.raw_title(pid), N.short(pid))
    if s in _used or len(s) > 60:
        s = (s[:60].rstrip("-") + "-" + N.short(pid))
    _used.add(s)
    _slugs[pid] = s
    return s


def chirpy_permalink(pid):
    return f"/posts/{slug_of(pid)}/"


def chirpy_title(pid):
    return N.raw_title(pid)


# Point N's internal link resolver at Chirpy post URLs.
N.permalink = chirpy_permalink
N.nav_title = chirpy_title


def created_dt(pid):
    v = N.BLOCKS.get(pid, {})
    ms = v.get("created_time") or v.get("last_edited_time")
    if ms:
        return datetime.datetime.fromtimestamp(ms / 1000, tz=datetime.timezone.utc)
    return datetime.datetime(2021, 1, 1, tzinfo=datetime.timezone.utc)


def yaml_q(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def categories_tags(pid):
    anc = N.ancestors(pid)  # top -> immediate parent (excludes root)
    titles = [N.raw_title(a) for a in anc]
    if not titles:
        titles = [N.raw_title(pid)]  # top-level category: file under itself
    cats = titles[:2]
    tags = titles[2:]
    return cats, tags


def child_index(pid):
    """Markdown list linking to child pages, for empty container pages."""
    node = N.tree.get(pid, {})
    kids = node.get("children", [])
    if not kids:
        return ""
    lines = ["아래 노트로 이동하세요.", ""]
    for cid in kids:
        lines.append(f"- [{N.raw_title(cid)}]({chirpy_permalink(cid)})")
    return "\n".join(lines)


def main():
    if os.path.isdir(POSTS):
        for f in glob.glob(os.path.join(POSTS, "*.md")):
            os.remove(f)
    os.makedirs(POSTS, exist_ok=True)

    used_names = set()
    count = 0
    for pid in N.PAGE_IDS:
        if pid == N.ROOT_ID:
            continue
        v = N.BLOCKS.get(pid)
        if not v:
            continue
        body = N.scrub_secrets(N.render_children(v)).strip()
        if not body:
            body = child_index(pid)
        if not body:
            continue  # empty leaf, nothing to publish
        cats, tags = categories_tags(pid)
        dt = created_dt(pid)
        fm = ["---", "title: " + yaml_q(N.raw_title(pid)),
              "date: " + dt.strftime("%Y-%m-%d %H:%M:%S +0000"),
              "categories: [" + ", ".join(yaml_q(c) for c in cats) + "]"]
        if tags:
            fm.append("tags: [" + ", ".join(yaml_q(t) for t in tags) + "]")
        if "\\(" in body or "$$" in body:
            fm.append("math: true")
        fm.append("---")

        name = f"{dt.strftime('%Y-%m-%d')}-{slug_of(pid)}.md"
        if name in used_names:
            name = f"{dt.strftime('%Y-%m-%d')}-{slug_of(pid)}-{N.short(pid)}.md"
        used_names.add(name)
        with open(os.path.join(POSTS, name), "w") as fh:
            fh.write("\n".join(fm) + "\n\n" + body + "\n")
        count += 1
    print(f"wrote {count} Chirpy posts")


if __name__ == "__main__":
    main()
