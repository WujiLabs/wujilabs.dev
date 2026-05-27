#!/usr/bin/env python3
"""
Build public/llms-full.txt by expanding local .md links from public/llms.txt.

Reads public/llms.txt verbatim as the index, then concatenates the contents
of every linked .md file that resolves to a path under public/. External
links (GitHub, arianna.run, etc.) are listed in the index but not expanded —
llms-full.txt is for one-shot LLM context, not a webcrawl.

Journal section is bounded: only the N most recent entries (default 5) are
bundled inline. Older entries stay listed in llms.txt but skipped here to
keep llms-full.txt size predictable as the journal grows.

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
H2_RE = re.compile(r"^##\s+(.+)$", re.MULTILINE)
JOURNAL_DATE_RE = re.compile(r"/journal/(\d{4}-\d{2}-\d{2})")

# Bound the journal section so llms-full.txt stays predictable as essay count
# grows. All entries still appear in /llms.txt; only the N most recent are
# inlined into /llms-full.txt. Tune by editing this constant.
JOURNAL_BUNDLE_LIMIT = 5


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


def section_for(position, sections):
    """Given a position in the index text, return the H2 heading it falls under (or '')."""
    current = ""
    for start, name in sections:
        if start <= position:
            current = name
        else:
            break
    return current


def main():
    if not os.path.exists(SRC):
        print(f"error: {SRC} not found", file=sys.stderr)
        sys.exit(1)

    with open(SRC) as f:
        index = f.read()

    # Map H2 section boundaries: [(char_offset, heading), ...]
    sections = [(m.start(), m.group(1).strip()) for m in H2_RE.finditer(index)]

    # Walk all links in document order; record each with its section + name + path.
    raw_links = []
    for m in LINK_RE.finditer(index):
        name, url = m.group(1), m.group(2)
        path = local_md_path(url)
        if not path:
            continue
        sect = section_for(m.start(), sections)
        raw_links.append({"name": name, "url": url, "path": path, "section": sect})

    # Dedup paths while preserving first-occurrence ordering.
    by_section = {}
    for link in raw_links:
        by_section.setdefault(link["section"], []).append(link)

    # Apply per-section bounds. Journal: keep N most recent (by date in URL).
    expanded = []
    seen_paths = set()
    skipped_journal = 0
    for section, links in by_section.items():
        if section.lower() == "journal":
            # Sort by date (descending), keep first N.
            def date_key(l):
                m = JOURNAL_DATE_RE.search(l["url"])
                return m.group(1) if m else ""
            links_sorted = sorted(links, key=date_key, reverse=True)
            kept = links_sorted[:JOURNAL_BUNDLE_LIMIT]
            skipped_journal = len(links_sorted) - len(kept)
            for link in kept:
                if link["path"] not in seen_paths:
                    expanded.append(link)
                    seen_paths.add(link["path"])
        else:
            for link in links:
                if link["path"] not in seen_paths:
                    expanded.append(link)
                    seen_paths.add(link["path"])

    parts = [index.rstrip(), ""]
    if skipped_journal:
        parts.append(f"<!-- {skipped_journal} older journal entries omitted from this bundle "
                     f"(JOURNAL_BUNDLE_LIMIT={JOURNAL_BUNDLE_LIMIT}); see /llms.txt for the full index. -->")
        parts.append("")
    for link in expanded:
        with open(link["path"]) as f:
            content = f.read().rstrip()
        rel = "/" + os.path.relpath(link["path"], PUBLIC)
        title = link["name"].replace('"', "&quot;")
        parts.append("")
        parts.append(f'<document path="{rel}" title="{title}">')
        parts.append("")
        parts.append(content)
        parts.append("")
        parts.append("</document>")
        parts.append("")

    with open(OUT, "w") as f:
        f.write("\n".join(parts))

    rel = os.path.relpath(OUT, SITE_DIR)
    note = f" ({skipped_journal} older journal entries omitted)" if skipped_journal else ""
    print(f"wrote {rel} ({os.path.getsize(OUT)} bytes, {len(expanded)} doc(s) expanded{note})")


if __name__ == "__main__":
    main()
