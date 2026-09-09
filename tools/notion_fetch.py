#!/usr/bin/env python3
"""Fetch a public Notion site recursively via the unofficial public API.

Caches each page's recordMap blocks to tools/cache/<page_id>.json and writes a
hierarchy tree to tools/cache/tree.json. One-time migration helper.

ponytail: relies on Notion's undocumented public loadPageChunk endpoint (no
official public read API). If Notion changes it, re-run against a fresh export.
"""
import json
import os
import sys
import time
import urllib.request
import urllib.error

SITE = os.environ.get("NOTION_SITE", "https://woolen-purchase-6e3.notion.site")
ROOT = os.environ.get("NOTION_ROOT", "ee098147-e79a-48e9-bc81-4266a48ac6bd")
API = SITE + "/api/v3/loadPageChunk"
CACHE = os.path.join(os.path.dirname(__file__), "cache")
os.makedirs(CACHE, exist_ok=True)


def dash(uuid_no_dash):
    s = uuid_no_dash.replace("-", "")
    return f"{s[0:8]}-{s[8:12]}-{s[12:16]}-{s[16:20]}-{s[20:32]}"


def post(payload, retries=4):
    data = json.dumps(payload).encode()
    for attempt in range(retries):
        req = urllib.request.Request(
            API, data=data,
            headers={"Content-Type": "application/json",
                     "User-Agent": "Mozilla/5.0 notion-migrate"},
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode())
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
            wait = 2 ** attempt
            print(f"  retry {attempt+1} after {e} (sleep {wait}s)", file=sys.stderr)
            time.sleep(wait)
    raise RuntimeError(f"failed to fetch {payload.get('pageId')}")


def fetch_page_blocks(page_id):
    """Return merged {block_id: value} for a page across all chunks."""
    blocks = {}
    cursor = {"stack": []}
    for _ in range(50):  # safety cap
        resp = post({
            "pageId": dash(page_id),
            "limit": 100,
            "cursor": cursor,
            "chunkNumber": 0,
            "verticalColumns": False,
        })
        rm = resp.get("recordMap", {}).get("block", {})
        for bid, rec in rm.items():
            v = rec.get("value", {}).get("value")
            if v:
                blocks[bid] = v
        cursor = resp.get("cursor", {"stack": []})
        if not cursor.get("stack"):
            break
    return blocks


def title_of(v):
    props = v.get("properties", {}) or {}
    t = props.get("title", [])
    return "".join(seg[0] for seg in t if seg and isinstance(seg[0], str)).strip()


def main():
    tree = {}          # id -> {title, parent, order, children:[ids]}
    order_counter = {}
    queue = [(ROOT, None)]
    seen = set()
    while queue:
        page_id, parent = queue.pop(0)
        norm = dash(page_id)
        if norm in seen:
            continue
        seen.add(norm)
        print(f"fetch {norm} (parent={parent})", file=sys.stderr)
        blocks = fetch_page_blocks(norm)
        with open(os.path.join(CACHE, norm + ".json"), "w") as f:
            json.dump(blocks, f, ensure_ascii=False)
        page_v = blocks.get(norm) or blocks.get(page_id)
        title = title_of(page_v) if page_v else "(untitled)"
        parent_children = tree.setdefault(parent, {"title": None, "parent": None,
                                                    "order": 0, "children": []}) if parent else None
        node = tree.setdefault(norm, {"title": title, "parent": parent,
                                      "order": order_counter.get(parent, 0),
                                      "children": []})
        node["title"] = title
        node["parent"] = parent
        order_counter[parent] = order_counter.get(parent, 0) + 1
        node["order"] = order_counter[parent]
        # enqueue child pages in content order
        content = (page_v or {}).get("content", []) if page_v else []
        for cid in content:
            cv = blocks.get(cid)
            if cv and cv.get("type") == "page":
                node["children"].append(dash(cid))
                queue.append((cid, norm))
        time.sleep(0.05)  # be gentle
    with open(os.path.join(CACHE, "tree.json"), "w") as f:
        json.dump(tree, f, ensure_ascii=False, indent=2)
    print(f"done. pages: {len(seen)}", file=sys.stderr)


if __name__ == "__main__":
    main()
