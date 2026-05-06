#!/usr/bin/env python3
"""
Build public/llms-full.txt by expanding local .md links from public/llms.txt.

Reads public/llms.txt verbatim as the index, then concatenates the contents
of every linked .md file that resolves to a path under public/. External
links (GitHub, arianna.run, etc.) are listed in the index but not expanded —
llms-full.txt is for one-shot LLM context, not a webcrawl.

Wired into `bun run build`. Output is .gitignored — derived artifact, never commit.
"""

import os
import re
import sys
from urllib.parse import urlparse

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SITE_DIR = os.path.dirname(SCRIPT_DIR)
PUBLIC = os.path.join(SITE_DIR, "public")
SRC = os.path.join(PUBLIC, "llms.txt")
OUT = os.path.join(PUBLIC, "llms-full.txt")

LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def local_md_path(url):
    """If url points to an .md under our public/ tree, return the local path; else None."""
    parsed = urlparse(url)
    if parsed.netloc and parsed.netloc != "wujilabs.dev":
        return None
    path = parsed.path
    if not path.endswith(".md"):
        return None
    candidate = os.path.join(PUBLIC, path.lstrip("/"))
    return candidate if os.path.exists(candidate) else None


def main():
    if not os.path.exists(SRC):
        print(f"error: {SRC} not found", file=sys.stderr)
        sys.exit(1)

    with open(SRC) as f:
        index = f.read()

    seen_paths = []
    for m in LINK_RE.finditer(index):
        url = m.group(2)
        path = local_md_path(url)
        if path and path not in seen_paths:
            seen_paths.append(path)

    parts = [index.rstrip(), ""]
    for path in seen_paths:
        with open(path) as f:
            content = f.read().rstrip()
        parts.append("---")
        parts.append("")
        parts.append(content)
        parts.append("")

    with open(OUT, "w") as f:
        f.write("\n".join(parts))

    rel = os.path.relpath(OUT, SITE_DIR)
    print(f"wrote {rel} ({os.path.getsize(OUT)} bytes, {len(seen_paths)} essay(s) expanded)")


if __name__ == "__main__":
    main()
