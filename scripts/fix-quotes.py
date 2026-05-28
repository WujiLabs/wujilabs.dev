#!/usr/bin/env python3
"""
Convert straight quotes to curly (typographic) quotes in essay source markdown.

Usage:
  python3 scripts/fix-quotes.py                  # all journal + thesis sources
  python3 scripts/fix-quotes.py --journal        # journal sources only
  python3 scripts/fix-quotes.py --thesis         # thesis sources only
  python3 scripts/fix-quotes.py <file> [<file>]  # specific files

Smart-quote algorithm (same Unicode chars work for both EN and CJK; CJK fonts
render U+201C/U+201D/U+2018/U+2019 at full width):

  - " after whitespace / line start / opening bracket → "  (U+201C left double)
  - " elsewhere                                       → "  (U+201D right double)
  - ' between letters / at end of word                → '  (U+2019, apostrophe)
  - ' after whitespace / line start / opening bracket → '  (U+2018 left single)
  - ' elsewhere                                       → '  (U+2019 right single)

Preserves fenced code blocks (```…```) and inline code spans (`…`) verbatim —
straight quotes inside code stay straight.

Idempotent: re-running on already-curly files is a no-op.
"""

import os
import re
import sys

JOURNAL_DIR = os.path.expanduser("~/wujilabs/journal")
THESIS_PATHS = [
    os.path.expanduser("~/wujilabs/launch-2026-05-01/thesis-draft-en.md"),
    os.path.expanduser("~/wujilabs/launch-2026-05-01/thesis-draft-zh.md"),
]

OPEN_DOUBLE = "“"   # "
CLOSE_DOUBLE = "”"  # "
OPEN_SINGLE = "‘"   # '
CLOSE_SINGLE = "’"  # '

# Characters that, if they immediately precede a straight quote, signal "open"
# — whitespace and various opening brackets including CJK ones.
OPENING_BEFORE = set(" \t\n\r([{<—–―«「『‘“")


def _convert(text):
    """Smart-convert quotes in a single non-code text segment."""
    out = []
    n = len(text)
    for i, ch in enumerate(text):
        prev = text[i - 1] if i > 0 else ""
        if ch == '"':
            if i == 0 or prev in OPENING_BEFORE:
                out.append(OPEN_DOUBLE)
            else:
                out.append(CLOSE_DOUBLE)
        elif ch == "'":
            nxt = text[i + 1] if i + 1 < n else ""
            # Apostrophe inside a word (don't, AI's) or at end of word (Labs')
            if prev.isalpha() and (nxt.isalpha() or nxt.isdigit() or not nxt.isalpha()):
                out.append(CLOSE_SINGLE)
            elif i == 0 or prev in OPENING_BEFORE:
                out.append(OPEN_SINGLE)
            else:
                out.append(CLOSE_SINGLE)
        else:
            out.append(ch)
    return "".join(out)


_FENCE_RE = re.compile(r"```.*?```", re.DOTALL)
_INLINE_CODE_RE = re.compile(r"`[^`\n]+`")


def fix_quotes(content):
    """Smart-quote the content, preserving fenced code + inline code spans."""
    parts = []
    last = 0
    for m in _FENCE_RE.finditer(content):
        parts.append(("text", content[last:m.start()]))
        parts.append(("code", m.group(0)))
        last = m.end()
    parts.append(("text", content[last:]))

    out = []
    for kind, segment in parts:
        if kind == "code":
            out.append(segment)
            continue
        sub_last = 0
        for m in _INLINE_CODE_RE.finditer(segment):
            out.append(_convert(segment[sub_last:m.start()]))
            out.append(m.group(0))
            sub_last = m.end()
        out.append(_convert(segment[sub_last:]))
    return "".join(out)


def process_file(path):
    """Returns (changed: bool, before_straight_doubles: int, before_straight_singles: int)."""
    with open(path, "r") as f:
        original = f.read()
    before_d = original.count('"')
    before_s = original.count("'")
    fixed = fix_quotes(original)
    if fixed == original:
        return False, before_d, before_s
    with open(path, "w") as f:
        f.write(fixed)
    return True, before_d, before_s


def _journal_sources():
    pat = re.compile(r"^\d{4}-\d{2}-\d{2}-.+-(en|zh)\.md$")
    return [
        os.path.join(JOURNAL_DIR, f)
        for f in sorted(os.listdir(JOURNAL_DIR))
        if pat.match(f)
    ]


def main():
    args = sys.argv[1:]
    if not args:
        targets = _journal_sources() + THESIS_PATHS
    elif args == ["--journal"]:
        targets = _journal_sources()
    elif args == ["--thesis"]:
        targets = list(THESIS_PATHS)
    elif all(not a.startswith("--") for a in args):
        targets = args
    else:
        print("Usage: fix-quotes.py [--journal | --thesis | <file>...]")
        sys.exit(1)

    total_changed = 0
    for path in targets:
        if not os.path.exists(path):
            print(f"  skip (not found): {path}")
            continue
        changed, d, s = process_file(path)
        rel = path.replace(os.path.expanduser("~"), "~")
        if changed:
            print(f"  fixed: {rel}  (had {d} straight \", {s} straight ')")
            total_changed += 1
        else:
            print(f"  ok:    {rel}")

    print(f"\nDone. {total_changed}/{len(targets)} file(s) modified.")


if __name__ == "__main__":
    main()
