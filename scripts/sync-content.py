#!/usr/bin/env python3
"""
Sync thesis + journal content from source markdown to Astro pages and public/ raw copies.

Usage:
  python3 scripts/sync-content.py              # sync everything (thesis + journal)
  python3 scripts/sync-content.py thesis       # sync only the thesis (both EN + ZH)
  python3 scripts/sync-content.py journal      # sync only journal entries
  python3 scripts/sync-content.py en           # legacy: thesis EN only
  python3 scripts/sync-content.py zh           # legacy: thesis ZH only

Thesis source: ~/wujilabs/launch-2026-05-01/thesis-draft-{en,zh}.md
Thesis targets:
  src/pages/thesis.astro, src/pages/thesis-zh.astro
  public/thesis.md, public/thesis-zh.md

Journal source: ~/wujilabs/journal/<YYYY-MM-DD>-<slug>-{en,zh}.md
Journal targets:
  src/pages/journal/<prefix>.astro        (EN: /journal/<prefix>)
  src/pages/journal/<prefix>-zh.astro     (ZH: /journal/<prefix>-zh)
  public/journal/<prefix>-{en,zh}.md      (raw markdown for AI access)
  public/journal/index.json               (manifest read by /journal/ index page)

Canonical essay format (enforced by the validator — see DESIGN.md "Canonical essay format"):
  - Title is a single `# H1` line.
  - Leading byline = exactly 2 italic lines after the H1
    (author line + date/license line).
  - Drafting metadata (cross-posting variant titles, etc.) lives inside
    <!-- cross-posting --> ... <!-- /cross-posting --> HTML comments.
    sync strips these on the way out.
  - Trailing colophon is OPTIONAL — an italic block at the very end may
    contain supplementary credits (discussion links, sister-practice
    acknowledgments). A pure duplicate of the leading byline (author +
    date together in the trailing block) is REJECTED by the validator.

On any format violation: sync exits with code 2 and names the violation.
Authors fix the source and re-run.
"""

import json
import os
import re
import shutil
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SITE_DIR = os.path.dirname(SCRIPT_DIR)
SOURCE_DIR = os.path.expanduser("~/wujilabs/launch-2026-05-01")
JOURNAL_SOURCE_DIR = os.path.expanduser("~/wujilabs/journal")
JOURNAL_OUT_PAGES = os.path.join(SITE_DIR, "src/pages/journal")
JOURNAL_OUT_PUBLIC = os.path.join(SITE_DIR, "public/journal")

THESIS_CONFIGS = {
    "en": {
        "source": os.path.join(SOURCE_DIR, "thesis-draft-en.md"),
        "astro": os.path.join(SITE_DIR, "src/pages/thesis.astro"),
        "public": os.path.join(SITE_DIR, "public/thesis.md"),
        "description": "The founding thesis of Wuji Labs — peer collaboration between sovereign intelligences.",
        "lang": "en",
        "url": "/thesis",
        "pair_url": "/thesis-zh",
    },
    "zh": {
        "source": os.path.join(SOURCE_DIR, "thesis-draft-zh.md"),
        "astro": os.path.join(SITE_DIR, "src/pages/thesis-zh.astro"),
        "public": os.path.join(SITE_DIR, "public/thesis-zh.md"),
        "description": "无忌实验室创始论文——主权智能之间的对等协作。",
        "lang": "zh-Hans",
        "url": "/thesis-zh",
        "pair_url": "/thesis",
    },
}

# Renderer differences between essay kinds.
ESSAY_KINDS = {
    "thesis": {
        # imports use `../` (one level up from src/pages/*.astro)
        "import_prefix": "../",
        "include_subscribe": False,
    },
    "journal": {
        # imports use `../../` (two levels up from src/pages/journal/*.astro)
        "import_prefix": "../../",
        "include_subscribe": True,
    },
}

# Cross-posting marker block: anything between these comments is drafting-only
# metadata (HN/Reddit/Twitter variant titles, etc.) and gets stripped on sync.
CROSS_POSTING_OPEN = "<!-- cross-posting -->"
CROSS_POSTING_CLOSE = "<!-- /cross-posting -->"
CROSS_POSTING_RE = re.compile(
    re.escape(CROSS_POSTING_OPEN) + r"\s*\n.*?\n\s*" + re.escape(CROSS_POSTING_CLOSE) + r"\s*\n?",
    re.DOTALL,
)
# Patterns that should ALWAYS live inside the marker block. Found outside = validator error.
CROSS_POSTING_LEAKED_PATTERNS = [
    r"Variant titles for cross-posting",
    r"不同平台的标题变体",
]

# Author phrases used to detect trailing-byline duplication.
AUTHOR_PHRASES = ["Wuji Labs", "无忌实验室"]
# Date patterns (English, Chinese, ISO). Used to detect trailing-byline duplication.
DATE_PATTERN_RE = re.compile(
    r"\d{4}-\d{2}-\d{2}|\d{4}年\d{1,2}月\d{1,2}日|"
    r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}",
    re.IGNORECASE,
)

# Journal filename: YYYY-MM-DD-<slug>-<en|zh>.md
JOURNAL_FILENAME_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})-(.+)-(en|zh)\.md$")


# ===========================================================================
# Custom exception for format violations
# ===========================================================================


class EssayFormatError(Exception):
    """Raised when an essay source violates the canonical format. The renderer
    refuses to sync until the author fixes the source."""


# ===========================================================================
# Inline markdown helpers (unchanged from original)
# ===========================================================================


def convert_inline(text, autolink=False):
    """Convert inline markdown to HTML, handling code spans first."""
    parts = []
    last = 0
    for m in re.finditer(r"`([^`]+)`", text):
        parts.append(_inline_no_code(text[last:m.start()], autolink))
        parts.append(f"<code>{m.group(1)}</code>")
        last = m.end()
    parts.append(_inline_no_code(text[last:], autolink))
    return "".join(parts)


_AUTOLINK_CTX = False


def _bold_handler(m):
    """If bold text looks like a URL and autolink is on, wrap in <strong><a>."""
    inner = m.group(1)
    if _AUTOLINK_CTX and re.match(r"^(github\.com|arianna\.run|wujilabs\.dev)\b", inner):
        url = "https://" + inner
        return f'<strong><a href="{url}">{inner}</a></strong>'
    return f"<strong>{inner}</strong>"


def _autolink_bare(text):
    """Link bare domain mentions not already inside an <a> or attribute."""
    def _repl(m):
        before = text[: m.start()]
        if before.endswith('"') or before.endswith(">"):
            return m.group(0)
        url = "https://" + m.group(0)
        return f'<a href="{url}">{m.group(0)}</a>'
    text = re.sub(r'(?<!["/\w>])github\.com/[\w/-]+', _repl, text)
    text = re.sub(r'(?<!["/\w>])arianna\.run(?!["/\w])', _repl, text)
    return text


def _inline_no_code(text, autolink=False):
    """Convert bold, italic, and links (no code spans)."""
    global _AUTOLINK_CTX
    _AUTOLINK_CTX = autolink
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
    text = re.sub(r"\*\*([^*]+)\*\*", _bold_handler, text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", text)
    if autolink:
        text = _autolink_bare(text)
    return text


# ===========================================================================
# Cross-posting block strip + format validator
# ===========================================================================


def strip_cross_posting(source):
    """Remove <!-- cross-posting --> ... <!-- /cross-posting --> blocks.
    Returns the cleaned source with marker blocks (and their contents) gone."""
    return CROSS_POSTING_RE.sub("", source)


def validate_essay(source, source_path):
    """Strict validator. Raises EssayFormatError on any violation.

    Checks (in order):
      1. Title H1 present.
      2. Leading byline = exactly 2 italic lines after the H1 (allowing blanks
         and an optional cross-posting marker block in between).
      3. Cross-posting patterns do NOT appear outside <!-- cross-posting --> markers.
      4. Trailing italic block (if any) is NOT a pure byline duplicate
         (author phrase + date together). A colophon with just a link or
         acknowledgment is allowed.
    """
    cleaned = strip_cross_posting(source)
    lines = cleaned.split("\n")

    # 1. H1 present?
    h1_idx = None
    for i, line in enumerate(lines):
        if line.strip().startswith("# "):
            h1_idx = i
            break
    if h1_idx is None:
        raise EssayFormatError(f"{source_path}: no H1 title line found (must start with '# ')")

    # 2. Leading byline: count italic lines after H1
    i = h1_idx + 1
    while i < len(lines) and lines[i].strip() == "":
        i += 1
    italic_count = 0
    while i < len(lines):
        s = lines[i].strip()
        if s.startswith("*") and s.endswith("*") and len(s) > 2:
            italic_count += 1
            i += 1
            continue
        # End of italic block on first non-italic, non-blank line
        break
    if italic_count != 2:
        raise EssayFormatError(
            f"{source_path}: leading byline must be exactly 2 italic lines after the H1; "
            f"found {italic_count}. Expected pattern:\n"
            f"  *<author line>*\n"
            f"  *<date>. <license>.*"
        )

    # 3. Cross-posting patterns outside markers?
    for pattern in CROSS_POSTING_LEAKED_PATTERNS:
        if re.search(pattern, cleaned):
            raise EssayFormatError(
                f"{source_path}: cross-posting pattern '{pattern}' found outside "
                f"<!-- cross-posting --> markers. Wrap drafting metadata in:\n"
                f"  <!-- cross-posting -->\n"
                f"  > ...\n"
                f"  <!-- /cross-posting -->"
            )

    # 4. Trailing-byline duplication check
    j = len(lines) - 1
    while j >= 0 and lines[j].strip() == "":
        j -= 1
    if j >= 0:
        trailing = lines[j].strip()
        if trailing.startswith("*") and trailing.endswith("*") and len(trailing) > 2:
            inner = trailing.strip("*").strip()
            has_author = any(re.search(rf"\b{re.escape(p)}\b", inner) for p in AUTHOR_PHRASES)
            has_date = bool(DATE_PATTERN_RE.search(inner))
            if has_author and has_date:
                raise EssayFormatError(
                    f"{source_path}: trailing italic block contains BOTH the author phrase "
                    f"and a date — that's a duplicate byline. Remove it (the leading byline "
                    f"is the canonical author identification). Trailing colophons may contain "
                    f"other info (discussion links, sister-practice acknowledgments) but "
                    f"not author+date.\n"
                    f"  Found at end of file: {trailing[:150]}{'…' if len(trailing) > 150 else ''}"
                )


# ===========================================================================
# Markdown parser
# ===========================================================================


def parse_markdown(source):
    """Parse markdown into (title, leading_meta, trailing_colophon, blocks).

    Assumes strip_cross_posting has already been applied.
    trailing_colophon is None when no trailing italic block exists, or the
    italic content string (validator has already ensured it's not a duplicate
    byline, so any present trailing block is a legitimate colophon).
    """
    lines = source.split("\n")
    title = None
    meta_lines = []
    body_start = 0

    for i, line in enumerate(lines):
        s = line.strip()
        if s.startswith("# ") and title is None:
            title = s[2:]
            body_start = i + 1
            continue
        if title is not None and s == "":
            body_start = i + 1
            continue
        if title is not None and s.startswith("*") and s.endswith("*"):
            meta_lines.append(s.strip("*").strip())
            body_start = i + 1
            continue
        break

    # Detect trailing colophon (italic block at the very end after a final `---`).
    trailing = lines[body_start:]
    trailing_colophon = None
    j = len(trailing) - 1
    while j >= 0 and trailing[j].strip() == "":
        j -= 1
    if j >= 0 and trailing[j].strip().startswith("*") and trailing[j].strip().endswith("*"):
        trailing_colophon = trailing[j].strip().strip("*").strip()
        trailing = trailing[:j]
        # Strip the separator `---` before the colophon, plus any trailing blanks.
        while trailing and trailing[-1].strip() in ("", "---"):
            if trailing[-1].strip() == "---":
                trailing.pop()
                break
            trailing.pop()

    blocks = _parse_blocks(trailing)
    return title, meta_lines, trailing_colophon, blocks


def _parse_blocks(lines):
    """Parse content lines into typed blocks."""
    blocks = []
    i = 0
    n = len(lines)

    while i < n:
        s = lines[i].strip()

        if s == "":
            i += 1
            continue
        if s == "---":
            blocks.append(("hr",))
            i += 1
            continue
        if s.startswith("### "):
            blocks.append(("h3", s[4:]))
            i += 1
            continue
        if s.startswith("## "):
            blocks.append(("h2", s[3:]))
            i += 1
            continue
        if s.startswith("- "):
            items = []
            while i < n and lines[i].strip().startswith("- "):
                items.append(lines[i].strip()[2:])
                i += 1
            blocks.append(("ul", items))
            continue
        if s.startswith("> "):
            bq = []
            while i < n and lines[i].strip().startswith("> "):
                bq.append(lines[i].strip()[2:])
                i += 1
            blocks.append(("blockquote", bq))
            continue

        # Paragraph: collect until blank line or block-level element.
        para = []
        while i < n:
            l = lines[i].strip()
            if l == "" or l == "---" or l.startswith("## ") or l.startswith("### "):
                break
            if l.startswith("- ") or l.startswith("> "):
                break
            para.append(l)
            i += 1
        blocks.append(("p", " ".join(para)))

    return blocks


def _escape_attr(s):
    """Escape double quotes for HTML attributes."""
    return s.replace("&", "&amp;").replace('"', "&quot;")


def check_quotes(source, lang):
    """Check for straight quotes that should be curly. Returns list of warnings."""
    warnings = []
    for i, line in enumerate(source.split("\n"), 1):
        for j, ch in enumerate(line):
            if ch == '"':
                ctx = line[max(0, j - 15): j + 16]
                warnings.append(f"  line {i}: straight double quote (U+0022) near: {ctx}")
            elif ch == "'":
                before = line[:j]
                if not re.search(r"[a-zA-Z]$", before):
                    ctx = line[max(0, j - 15): j + 16]
                    warnings.append(f"  line {i}: straight single quote (U+0027) near: {ctx}")
    return warnings


# ===========================================================================
# Unified essay renderer (thesis + journal)
# ===========================================================================


def render_essay_astro(
    title, leading_meta, trailing_colophon, blocks,
    *, kind, lang, description, lang_pair_url=None,
):
    """Render a thesis or journal essay to a complete .astro file.

    Differences between kinds (controlled by ESSAY_KINDS):
      - import path depth (../ for thesis at src/pages/, ../../ for journal
        at src/pages/journal/)
      - whether to embed <SubscribeBlock /> at the end (journal only)

    The cross-language toggle in the meta line is rendered whenever
    lang_pair_url is set. For thesis, it's always set (EN ↔ ZH always pair).
    For journal, it's set only when both languages exist for the same slug.
    """
    config = ESSAY_KINDS[kind]
    indent = "  "
    parts = []

    # Frontmatter imports
    parts.append("---")
    parts.append(f"import ThesisLayout from '{config['import_prefix']}layouts/ThesisLayout.astro';")
    if config["include_subscribe"]:
        parts.append(
            f"import SubscribeBlock from '{config['import_prefix']}components/SubscribeBlock.astro';"
        )
    parts.append("---")
    parts.append("")

    # Page open
    parts.append("<ThesisLayout")
    parts.append(f'  title="{_escape_attr(title)}"')
    parts.append(f'  description="{_escape_attr(description)}"')
    parts.append(f'  lang="{lang}"')
    parts.append(">")
    parts.append(f"{indent}<h1>{title}</h1>")

    # Meta line: leading byline (joined by <br />) + optional cross-language toggle
    meta_html_parts = []
    if leading_meta:
        meta_html_parts.append("<br />".join(leading_meta))
    if lang_pair_url:
        other_label = "EN" if lang.startswith("zh") else "中文"
        toggle = f'<a href="{lang_pair_url}" class="lang-toggle">{other_label}</a>'
        meta_html_parts.append(toggle)
    if meta_html_parts:
        parts.append(f'{indent}<p class="meta">{" · ".join(meta_html_parts)}</p>')
    parts.append("")

    # Body blocks
    for block in blocks:
        btype = block[0]
        if btype == "hr":
            parts.append(f"{indent}<hr />")
            parts.append("")
        elif btype == "h2":
            parts.append(f"{indent}<h2>{block[1]}</h2>")
            parts.append("")
        elif btype == "h3":
            parts.append(f"{indent}<h3>{block[1]}</h3>")
            parts.append("")
        elif btype == "p":
            parts.append(f"{indent}<p>{convert_inline(block[1])}</p>")
            parts.append("")
        elif btype == "ul":
            parts.append(f"{indent}<ul>")
            for item in block[1]:
                parts.append(f"{indent}  <li>{convert_inline(item, autolink=True)}</li>")
            parts.append(f"{indent}</ul>")
            parts.append("")
        elif btype == "blockquote":
            parts.append(f"{indent}<blockquote>")
            for line in block[1]:
                parts.append(f"{indent}  <p>{convert_inline(line)}</p>")
            parts.append(f"{indent}</blockquote>")
            parts.append("")

    # Trailing colophon (always non-byline content per validator)
    if trailing_colophon:
        parts.append(f"{indent}<hr />")
        parts.append("")
        parts.append(f'{indent}<p class="meta">{convert_inline(trailing_colophon, autolink=True)}</p>')

    # SubscribeBlock (journal only). ThesisLayout adds its own back-link below.
    if config["include_subscribe"]:
        parts.append(f"{indent}<SubscribeBlock />")

    parts.append("</ThesisLayout>")
    parts.append("")

    # Scoped CSS for the lang-toggle anchor (only when toggle is present)
    if lang_pair_url:
        parts.append("<style is:global>")
        parts.append("  .meta .lang-toggle {")
        parts.append("    color: var(--text-2);")
        parts.append("    text-decoration: none;")
        parts.append("    border-bottom: 1px solid var(--rule);")
        parts.append("  }")
        parts.append("  .meta .lang-toggle:hover {")
        parts.append("    color: var(--link);")
        parts.append("    border-bottom-color: var(--link);")
        parts.append("  }")
        parts.append("</style>")

    return "\n".join(parts)


# ===========================================================================
# Thesis sync
# ===========================================================================


def sync_thesis(lang):
    """Sync one thesis language. Always emits the cross-language toggle since
    thesis EN and ZH are always paired."""
    cfg = THESIS_CONFIGS[lang]
    source_path = cfg["source"]
    if not os.path.exists(source_path):
        print(f"  ERROR: source not found: {source_path}")
        return False

    with open(source_path, "r") as f:
        source = f.read()

    # Quote-style check (informational only)
    quote_warnings = check_quotes(source, lang)
    if quote_warnings:
        print(f"  ⚠ {len(quote_warnings)} straight quote(s) found in source:")
        for w in quote_warnings:
            print(w)

    # Strict validation — raises EssayFormatError if anything's off
    validate_essay(source, source_path)

    # Strip cross-posting (thesis usually has none, but applied uniformly)
    cleaned = strip_cross_posting(source)
    title, meta_lines, trailing, blocks = parse_markdown(cleaned)

    astro = render_essay_astro(
        title, meta_lines, trailing, blocks,
        kind="thesis",
        lang=cfg["lang"],
        description=cfg["description"],
        lang_pair_url=cfg["pair_url"],
    )

    with open(cfg["astro"], "w") as f:
        f.write(astro)
    print(f'  {cfg["astro"]}')

    shutil.copy2(source_path, cfg["public"])
    print(f'  {cfg["public"]}')
    return True


# ===========================================================================
# Journal sync
# ===========================================================================


def parse_journal_filename(name):
    """('2026-05-12-insights-zh.md') → ('2026-05-12', 'insights', 'zh') or None."""
    m = JOURNAL_FILENAME_RE.match(name)
    if not m:
        return None
    return (m.group(1), m.group(2), m.group(3))


def journal_url(prefix, lang):
    """URL pattern: EN = /journal/<prefix>, ZH = /journal/<prefix>-zh."""
    return f"/journal/{prefix}" if lang == "en" else f"/journal/{prefix}-zh"


def sync_journal():
    """Sync all journal entries from ~/wujilabs/journal/."""
    if not os.path.isdir(JOURNAL_SOURCE_DIR):
        print(f"  ERROR: journal source dir not found: {JOURNAL_SOURCE_DIR}")
        return False

    # Inventory: parse filenames first to detect language pairs.
    entries = []
    for name in sorted(os.listdir(JOURNAL_SOURCE_DIR)):
        parsed = parse_journal_filename(name)
        if not parsed:
            continue  # README.md, drafts/, etc.
        date, slug_rest, lang = parsed
        prefix = f"{date}-{slug_rest}"
        entries.append({
            "prefix": prefix,
            "lang": lang,
            "date": date,
            "slug": slug_rest,
            "source": os.path.join(JOURNAL_SOURCE_DIR, name),
        })

    if not entries:
        print("  (no journal entries to sync)")
        return True

    prefix_to_langs = {}
    for e in entries:
        prefix_to_langs.setdefault(e["prefix"], set()).add(e["lang"])

    os.makedirs(JOURNAL_OUT_PAGES, exist_ok=True)
    os.makedirs(JOURNAL_OUT_PUBLIC, exist_ok=True)

    # Prune stale outputs (left over from source renames or supersessions).
    # Without this, a renamed essay leaves a ghost route alive at the old URL.
    expected_astro = set()
    expected_public_md = set()
    for e in entries:
        astro_name = f"{e['prefix']}.astro" if e["lang"] == "en" else f"{e['prefix']}-zh.astro"
        expected_astro.add(astro_name)
        expected_public_md.add(f"{e['prefix']}-{e['lang']}.md")

    # Preserve hand-authored pages in the journal directory (index, future
    # routes). Only auto-managed essay pages match the YYYY-MM-DD-<slug> shape.
    for name in os.listdir(JOURNAL_OUT_PAGES):
        if not name.endswith(".astro"):
            continue
        if name in expected_astro:
            continue
        if not re.match(r"^\d{4}-\d{2}-\d{2}-", name):
            continue
        stale = os.path.join(JOURNAL_OUT_PAGES, name)
        os.remove(stale)
        print(f"  pruned stale: {stale}")
    for name in os.listdir(JOURNAL_OUT_PUBLIC):
        if name == "index.json":
            continue
        if name.endswith(".md") and name not in expected_public_md:
            stale = os.path.join(JOURNAL_OUT_PUBLIC, name)
            os.remove(stale)
            print(f"  pruned stale: {stale}")

    manifest_entries = []
    for e in entries:
        with open(e["source"], "r") as f:
            source = f.read()

        # Strict validation per essay
        validate_essay(source, e["source"])

        cleaned = strip_cross_posting(source)
        title, meta_lines, trailing, blocks = parse_markdown(cleaned)
        if not title:
            print(f"  WARN: no title in {e['source']}, skipping")
            continue

        # Lang pair: only when both <prefix>-en.md and <prefix>-zh.md exist
        langs_present = prefix_to_langs[e["prefix"]]
        lang_pair_url = None
        if "en" in langs_present and "zh" in langs_present:
            other = "zh" if e["lang"] == "en" else "en"
            lang_pair_url = journal_url(e["prefix"], other)

        astro = render_essay_astro(
            title, meta_lines, trailing, blocks,
            kind="journal",
            lang=("zh-Hans" if e["lang"] == "zh" else "en"),
            description=title,
            lang_pair_url=lang_pair_url,
        )

        astro_name = f"{e['prefix']}.astro" if e["lang"] == "en" else f"{e['prefix']}-zh.astro"
        astro_path = os.path.join(JOURNAL_OUT_PAGES, astro_name)
        with open(astro_path, "w") as f:
            f.write(astro)

        public_name = f"{e['prefix']}-{e['lang']}.md"
        public_path = os.path.join(JOURNAL_OUT_PUBLIC, public_name)
        shutil.copy2(e["source"], public_path)

        print(f"  {astro_path}")
        print(f"  {public_path}")

        manifest_entries.append({
            "prefix": e["prefix"],
            "lang": e["lang"],
            "date": e["date"],
            "title": title,
            "url": journal_url(e["prefix"], e["lang"]),
            "lang_pair_url": lang_pair_url,
            "public_md": f"/journal/{public_name}",
        })

    # Reverse-chronological for the index page
    manifest_entries.sort(key=lambda x: (x["date"], x["prefix"]), reverse=True)

    manifest_path = os.path.join(JOURNAL_OUT_PUBLIC, "index.json")
    with open(manifest_path, "w") as f:
        json.dump({"entries": manifest_entries}, f, indent=2, ensure_ascii=False)
    print(f"  {manifest_path}")
    return True


# ===========================================================================
# Entry point
# ===========================================================================


def main():
    args = sys.argv[1:]
    if not args:
        targets = ["thesis", "journal"]
    elif args == ["thesis"]:
        targets = ["thesis"]
    elif args == ["journal"]:
        targets = ["journal"]
    elif all(a in THESIS_CONFIGS for a in args):
        # legacy: `sync-content.py zh` / `en` / `en zh`
        targets = [("thesis-" + a) for a in args]
    else:
        print("Unknown target(s):", args)
        print("Usage:")
        print("  sync-content.py                # everything")
        print("  sync-content.py thesis         # thesis EN + ZH")
        print("  sync-content.py journal        # journal entries")
        print("  sync-content.py en             # thesis EN (legacy)")
        print("  sync-content.py zh             # thesis ZH (legacy)")
        sys.exit(1)

    print("Syncing content...")
    try:
        for t in targets:
            if t == "thesis":
                for lang in ["en", "zh"]:
                    print(f"\n[THESIS {lang.upper()}]")
                    sync_thesis(lang)
            elif t == "journal":
                print(f"\n[JOURNAL]")
                sync_journal()
            elif t.startswith("thesis-"):
                lang = t.split("-", 1)[1]
                print(f"\n[THESIS {lang.upper()}]")
                sync_thesis(lang)
    except EssayFormatError as e:
        print(f"\n✗ FORMAT VIOLATION — sync aborted.\n{e}\n", file=sys.stderr)
        sys.exit(2)

    print("\nDone. Run `bun run dev` to verify.")


if __name__ == "__main__":
    main()
