#!/usr/bin/env python3
"""
Convert straight quotes to curly (typographic) quotes in essay source markdown.

Usage:
  python3 scripts/fix-quotes.py                  # journal + thesis markdown sources
  python3 scripts/fix-quotes.py --journal        # journal markdown only
  python3 scripts/fix-quotes.py --thesis         # thesis markdown only
  python3 scripts/fix-quotes.py --astro          # hand-authored .astro pages
                                                 #   (src/pages/**/*.astro)
  python3 scripts/fix-quotes.py --all            # journal + thesis + astro
  python3 scripts/fix-quotes.py --dry-run …      # print unified diffs, write nothing
  python3 scripts/fix-quotes.py <file> [<file>]  # specific files (md or astro;
                                                 #   dispatch on extension)

Smart-quote algorithm (same Unicode chars work for both EN and CJK; CJK fonts
render U+201C/U+201D/U+2018/U+2019 at full width):

  - " after whitespace / line start / opening bracket / tag close ('>') → "
  - " elsewhere                                                         → "
  - ' between letters / at end of word                                  → ' (apostrophe)
  - ' after whitespace / line start / opening bracket                   → '
  - ' elsewhere                                                         → '

Markdown mode preserves fenced code blocks (```…```) and inline code spans (`…`).

Astro mode preserves the frontmatter block, all `<script>`/`<style>` contents,
HTML comments, every character inside an opening tag (so attributes stay intact),
and JSX expressions (`{…}`, brace-nesting tracked). Only HTML text-node content
gets smart-quoted.

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
# Hand-authored Astro pages live here (markdown-driven essay pages live in
# src/pages/journal/ and are auto-generated from the journal/thesis markdown
# sources — we exclude them since they're handled by markdown sync above).
SITE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASTRO_PAGES_DIR = os.path.join(SITE_DIR, "src/pages")
ASTRO_EXCLUDE_DIRS = {"journal"}  # auto-generated; sync-content.py owns these

OPEN_DOUBLE = "“"   # "
CLOSE_DOUBLE = "”"  # "
OPEN_SINGLE = "‘"   # '
CLOSE_SINGLE = "’"  # '

# Characters that, if they immediately precede a straight quote, signal "open"
# — whitespace, opening brackets (including CJK), and `>` for the "text right
# after a tag close" case in HTML/Astro (e.g., `<p>"hello"</p>`).
OPENING_BEFORE = set(" \t\n\r([{<>—–―«「『‘“")


def _smart_text(text):
    """Smart-quote a contiguous text segment.

    Doubles use pure pair-alternation (1st open, 2nd close, 3rd open, …) — this
    is the only robust strategy when text mixes EN and CJK, where the
    "whitespace-before-means-open" heuristic fails on `一个"工具"` patterns.

    Singles handle apostrophes first (intra-word and end-of-word, which always
    emit U+2019), then alternate the remaining pairs. End-of-word ambiguity
    (`Labs'` vs the closing `'` of `'hello'`) is resolved via an `inside_single`
    state machine: if a quoted region is open, the end-of-word `'` closes it;
    otherwise it's a possessive apostrophe.
    """
    out = []
    n = len(text)
    d_open = True
    inside_single = False
    for i, ch in enumerate(text):
        prev = text[i - 1] if i > 0 else ""
        nxt = text[i + 1] if i + 1 < n else ""
        if ch == '"':
            out.append(OPEN_DOUBLE if d_open else CLOSE_DOUBLE)
            d_open = not d_open
        elif ch == "'":
            if prev.isalpha() and nxt.isalpha():
                # Intra-word apostrophe (don't, what's): always U+2019
                out.append(CLOSE_SINGLE)
            elif prev.isalpha() and not nxt.isalpha():
                # End-of-word: closing quote if a pair is open, otherwise apostrophe
                out.append(CLOSE_SINGLE)
                if inside_single:
                    inside_single = False
            else:
                if inside_single:
                    out.append(CLOSE_SINGLE)
                    inside_single = False
                else:
                    out.append(OPEN_SINGLE)
                    inside_single = True
        else:
            out.append(ch)
    return "".join(out)


# Legacy alias — older code paths called _convert(); keep it as a passthrough.
def _convert(text):
    return _smart_text(text)


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


# ---------------------------------------------------------------------------
# Astro mode
# ---------------------------------------------------------------------------

_ASTRO_SCRIPT_STYLE_RE = re.compile(r"<(script|style)\b", re.IGNORECASE)

# JS string literal at a "value position" — preceded by `:`, `,`, `=`, `(`, or `[`
# (with optional whitespace between). This catches object/array values like
# `body: "..."` and `[ "..." ]` while leaving `import x from '...'`, function
# names, and string-like content inside line/block comments untouched.
_FM_VALUE_STRING_RE = re.compile(
    r"([:,=\(\[]\s*)([\"'])((?:\\.|(?!\2).)*)\2",
    re.DOTALL,
)


def _astro_preserve_mask(body):
    """Return a boolean list, same length as body, where True = preserved
    (don't touch). Preserved regions:

      - Inside <script>…</script> and <style>…</style> blocks
      - Inside HTML comments <!-- … -->
      - Every character inside an opening tag <…> (so attributes stay intact)
      - Inside JSX expressions {…} (brace-nesting tracked, ignoring braces
        that appear inside string literals within the expression)
    """
    mask = [False] * len(body)
    i = 0
    n = len(body)
    while i < n:
        # <script> or <style> block — opaque until matching close tag
        m = _ASTRO_SCRIPT_STYLE_RE.match(body, i)
        if m:
            tag = m.group(1).lower()
            close_marker = body.find(f"</{tag}", i + m.end())
            if close_marker < 0:
                end = n
            else:
                gt = body.find(">", close_marker)
                end = gt + 1 if gt >= 0 else n
            for j in range(i, end):
                mask[j] = True
            i = end
            continue
        # HTML comment
        if body.startswith("<!--", i):
            close = body.find("-->", i + 4)
            end = close + 3 if close >= 0 else n
            for j in range(i, end):
                mask[j] = True
            i = end
            continue
        # Generic tag — preserve attribute content, leave text outside alone
        if body[i] == "<" and i + 1 < n and (body[i + 1].isalpha() or body[i + 1] in "/!"):
            gt = body.find(">", i + 1)
            end = gt + 1 if gt >= 0 else n
            for j in range(i, end):
                mask[j] = True
            i = end
            continue
        # JSX expression — walk with nesting, skipping braces in string literals
        if body[i] == "{":
            depth = 1
            j = i + 1
            in_str = None  # None, '"', "'", or "`"
            esc = False
            while j < n and depth > 0:
                ch = body[j]
                if in_str:
                    if esc:
                        esc = False
                    elif ch == "\\":
                        esc = True
                    elif ch == in_str:
                        in_str = None
                else:
                    if ch in ("'", '"', "`"):
                        in_str = ch
                    elif ch == "{":
                        depth += 1
                    elif ch == "}":
                        depth -= 1
                j += 1
            for k in range(i, j):
                mask[k] = True
            i = j
            continue
        i += 1
    return mask


def _smart_inside_string_body(body, delim):
    """Smart-convert content inside a JS string literal body. The outer delimiter
    is JS syntax; we smart-quote only the non-delimiter straight quotes (e.g.
    `'` apostrophe inside `"..."`, or `"..."` quote pair inside `'...'`).
    Escapes are preserved verbatim."""
    # Walk char-by-char, masking escape sequences and the outer-delim positions,
    # then smart-quote the non-masked text in one contiguous segment.
    if not body:
        return body
    n = len(body)
    mask = [False] * n
    i = 0
    while i < n:
        ch = body[i]
        if ch == "\\" and i + 1 < n:
            mask[i] = mask[i + 1] = True
            i += 2
            continue
        if ch == delim:
            mask[i] = True
        i += 1
    return _convert_with_mask(body, mask)


def _convert_with_mask(text, mask):
    """Apply _smart_text to non-masked positions in `text`, preserving masked
    chars verbatim. Pair state (open/close alternation) resets at every masked
    run, so each contiguous unmasked segment gets a fresh open/close balance."""
    out = []
    n = len(text)
    seg = []
    for i, ch in enumerate(text):
        if mask[i]:
            if seg:
                out.append(_smart_text("".join(seg)))
                seg = []
            out.append(ch)
        else:
            seg.append(ch)
    if seg:
        out.append(_smart_text("".join(seg)))
    return "".join(out)


def _fix_frontmatter_strings(fm):
    """Smart-convert content inside string literals at value positions in the
    frontmatter. Preserves the outer JS string delimiters as syntax."""
    def _repl(m):
        prefix = m.group(1)
        delim = m.group(2)
        body = m.group(3)
        return prefix + delim + _smart_inside_string_body(body, delim) + delim
    return _FM_VALUE_STRING_RE.sub(_repl, fm)


def fix_astro(content):
    """Smart-quote an .astro file. In the body, only HTML text-node content is
    converted (attributes, <script>, <style>, comments, JSX expressions stay
    verbatim). In the frontmatter, string literals at value positions
    (`key: "..."`, `[ "..." ]`, etc.) have their *interior content* smart-quoted
    — the outer delimiters are preserved as JS syntax."""
    fm = ""
    body = content
    if content.startswith("---"):
        # Find the line containing the closing --- after the opening one
        end_marker = content.find("\n---", 3)
        if end_marker >= 0:
            after_close_line = content.find("\n", end_marker + 4)
            split = after_close_line + 1 if after_close_line >= 0 else len(content)
            fm = content[:split]
            body = content[split:]
    if fm:
        fm = _fix_frontmatter_strings(fm)

    mask = _astro_preserve_mask(body)
    return fm + _convert_with_mask(body, mask)


# ---------------------------------------------------------------------------
# Dispatch + I/O
# ---------------------------------------------------------------------------


def _convert_for_path(path, content):
    """Pick the right converter based on file extension."""
    if path.endswith(".astro"):
        return fix_astro(content)
    return fix_quotes(content)


def process_file(path, dry_run=False):
    """Returns (changed: bool, diff_text_or_none, before_d, before_s)."""
    with open(path, "r") as f:
        original = f.read()
    before_d = original.count('"')
    before_s = original.count("'")
    fixed = _convert_for_path(path, original)
    if fixed == original:
        return False, None, before_d, before_s
    if dry_run:
        import difflib
        diff = "".join(difflib.unified_diff(
            original.splitlines(keepends=True),
            fixed.splitlines(keepends=True),
            fromfile=path, tofile=path + " (curly)", n=2,
        ))
        return True, diff, before_d, before_s
    with open(path, "w") as f:
        f.write(fixed)
    return True, None, before_d, before_s


def _journal_sources():
    pat = re.compile(r"^\d{4}-\d{2}-\d{2}-.+-(en|zh)\.md$")
    return [
        os.path.join(JOURNAL_DIR, f)
        for f in sorted(os.listdir(JOURNAL_DIR))
        if pat.match(f)
    ]


def _astro_sources():
    """All hand-authored .astro pages under src/pages, excluding auto-generated
    subdirectories (currently: src/pages/journal/)."""
    results = []
    for dirpath, dirnames, filenames in os.walk(ASTRO_PAGES_DIR):
        rel = os.path.relpath(dirpath, ASTRO_PAGES_DIR)
        parts = rel.split(os.sep) if rel != "." else []
        if parts and parts[0] in ASTRO_EXCLUDE_DIRS:
            dirnames[:] = []
            continue
        for f in sorted(filenames):
            if f.endswith(".astro"):
                results.append(os.path.join(dirpath, f))
    return sorted(results)


def main():
    raw_args = sys.argv[1:]
    dry_run = "--dry-run" in raw_args
    args = [a for a in raw_args if a != "--dry-run"]

    if not args:
        targets = _journal_sources() + THESIS_PATHS
    elif args == ["--journal"]:
        targets = _journal_sources()
    elif args == ["--thesis"]:
        targets = list(THESIS_PATHS)
    elif args == ["--astro"]:
        targets = _astro_sources()
    elif args == ["--all"]:
        targets = _journal_sources() + THESIS_PATHS + _astro_sources()
    elif all(not a.startswith("--") for a in args):
        targets = args
    else:
        print(
            "Usage: fix-quotes.py [--journal | --thesis | --astro | --all | "
            "<file>...] [--dry-run]"
        )
        sys.exit(1)

    total_changed = 0
    for path in targets:
        if not os.path.exists(path):
            print(f"  skip (not found): {path}")
            continue
        changed, diff, d, s = process_file(path, dry_run=dry_run)
        rel = path.replace(os.path.expanduser("~"), "~")
        if changed:
            verb = "would fix" if dry_run else "fixed"
            print(f'  {verb}: {rel}  (had {d} straight ", {s} straight \')')
            if dry_run and diff:
                print(diff)
            total_changed += 1
        else:
            print(f"  ok:    {rel}")

    suffix = " (dry-run — nothing written)" if dry_run else ""
    print(f"\nDone. {total_changed}/{len(targets)} file(s) {'would be ' if dry_run else ''}modified{suffix}.")


if __name__ == "__main__":
    main()
