#!/usr/bin/env python3
"""
Sync thesis + journal content from source markdown to Astro pages and public/ raw copies.

Usage:
  python3 scripts/sync-content.py              # sync everything (thesis + journal)
  python3 scripts/sync-content.py thesis       # sync only the thesis (both EN + ZH)
  python3 scripts/sync-content.py zh           # sync thesis ZH only (legacy shorthand)
  python3 scripts/sync-content.py en           # sync thesis EN only (legacy shorthand)
  python3 scripts/sync-content.py journal      # sync only journal entries

Thesis source: ~/wujilabs/launch-2026-05-01/thesis-draft-{en,zh}.md
Thesis targets:
  src/pages/thesis.astro, src/pages/thesis-zh.astro
  public/thesis.md, public/thesis-zh.md

Journal source: ~/wujilabs/journal/[YYYY-MM-DD]-[slug]-{en,zh}.md
Journal targets:
  src/pages/journal/[prefix].astro          (EN, e.g. /journal/2026-05-05-retcon-launch)
  src/pages/journal/[prefix]-zh.astro       (ZH, e.g. /journal/2026-05-05-retcon-launch-zh)
  public/journal/[prefix]-{en,zh}.md        (raw markdown for AI access)
  public/journal/index.json                 (manifest read by /journal/ index page)
"""

import json
import re
import sys
import os
import shutil

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SITE_DIR = os.path.dirname(SCRIPT_DIR)
SOURCE_DIR = os.path.expanduser("~/wujilabs/launch-2026-05-01")
JOURNAL_SOURCE_DIR = os.path.expanduser("~/wujilabs/journal")
JOURNAL_OUT_PAGES = os.path.join(SITE_DIR, "src/pages/journal")
JOURNAL_OUT_PUBLIC = os.path.join(SITE_DIR, "public/journal")

CONFIGS = {
    "en": {
        "source": os.path.join(SOURCE_DIR, "thesis-draft-en.md"),
        "astro": os.path.join(SITE_DIR, "src/pages/thesis.astro"),
        "public": os.path.join(SITE_DIR, "public/thesis.md"),
        "description": "The founding thesis of Wuji Labs — peer collaboration between sovereign intelligences.",
        "lang": "en",
    },
    "zh": {
        "source": os.path.join(SOURCE_DIR, "thesis-draft-zh.md"),
        "astro": os.path.join(SITE_DIR, "src/pages/thesis-zh.astro"),
        "public": os.path.join(SITE_DIR, "public/thesis-zh.md"),
        "description": "无忌实验室创始论文——主权智能之间的对等协作。",
        "lang": "zh-Hans",
    },
}


def convert_inline(text, autolink=False):
    """Convert inline markdown to HTML, handling code spans first.
    autolink=True links bare github.com/* and arianna.run mentions (for lists/meta).
    """
    parts = []
    last = 0
    for m in re.finditer(r'`([^`]+)`', text):
        parts.append(_inline_no_code(text[last:m.start()], autolink))
        parts.append(f'<code>{m.group(1)}</code>')
        last = m.end()
    parts.append(_inline_no_code(text[last:], autolink))
    return ''.join(parts)


_AUTOLINK_CTX = False


def _bold_handler(m):
    """If bold text looks like a URL and autolink is on, wrap in <strong><a>."""
    inner = m.group(1)
    if _AUTOLINK_CTX and re.match(r'^(github\.com|arianna\.run|wujilabs\.dev)\b', inner):
        url = 'https://' + inner
        return f'<strong><a href="{url}">{inner}</a></strong>'
    return f'<strong>{inner}</strong>'


def _autolink_bare(text):
    """Link bare domain mentions not already inside an <a> or attribute."""
    def _repl(m):
        before = text[:m.start()]
        if before.endswith('"') or before.endswith('>'):
            return m.group(0)
        url = 'https://' + m.group(0)
        return f'<a href="{url}">{m.group(0)}</a>'
    text = re.sub(r'(?<!["/\w>])github\.com/[\w/-]+', _repl, text)
    text = re.sub(r'(?<!["/\w>])arianna\.run(?!["/\w])', _repl, text)
    return text


def _inline_no_code(text, autolink=False):
    """Convert bold, italic, and links (no code spans)."""
    global _AUTOLINK_CTX
    _AUTOLINK_CTX = autolink
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)
    text = re.sub(r'\*\*([^*]+)\*\*', _bold_handler, text)
    text = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', r'<em>\1</em>', text)
    if autolink:
        text = _autolink_bare(text)
    return text


def parse_markdown(source):
    """Parse markdown into (title, meta_lines, last_meta_line, blocks)."""
    lines = source.split('\n')

    title = None
    meta_lines = []
    last_meta_raw = None
    body_start = 0

    for i, line in enumerate(lines):
        s = line.strip()
        if s.startswith('# ') and title is None:
            title = s[2:]
            body_start = i + 1
            continue
        if title is not None and s == '':
            body_start = i + 1
            continue
        if title is not None and s.startswith('*') and s.endswith('*'):
            meta_lines.append(s.strip('*').strip())
            body_start = i + 1
            continue
        break

    # Find the trailing meta line (last non-empty line starting with *)
    trailing = lines[body_start:]
    j = len(trailing) - 1
    while j >= 0 and trailing[j].strip() == '':
        j -= 1
    if j >= 0 and trailing[j].strip().startswith('*') and trailing[j].strip().endswith('*'):
        last_meta_raw = trailing[j].strip().strip('*').strip()
        trailing = trailing[:j]
        # also strip any trailing --- before the meta
        while trailing and trailing[-1].strip() in ('', '---'):
            if trailing[-1].strip() == '---':
                trailing.pop()
                break
            trailing.pop()

    blocks = _parse_blocks(trailing)
    return title, meta_lines, last_meta_raw, blocks


def _parse_blocks(lines):
    """Parse content lines into typed blocks."""
    blocks = []
    i = 0
    n = len(lines)

    while i < n:
        s = lines[i].strip()

        if s == '':
            i += 1
            continue

        if s == '---':
            blocks.append(('hr',))
            i += 1
            continue

        if s.startswith('### '):
            blocks.append(('h3', s[4:]))
            i += 1
            continue

        if s.startswith('## '):
            blocks.append(('h2', s[3:]))
            i += 1
            continue

        if s.startswith('- '):
            items = []
            while i < n and lines[i].strip().startswith('- '):
                items.append(lines[i].strip()[2:])
                i += 1
            blocks.append(('ul', items))
            continue

        if s.startswith('> '):
            bq = []
            while i < n and lines[i].strip().startswith('> '):
                bq.append(lines[i].strip()[2:])
                i += 1
            blocks.append(('blockquote', bq))
            continue

        # Paragraph: collect until blank line or block-level element
        para = []
        while i < n:
            l = lines[i].strip()
            if l == '' or l == '---' or l.startswith('## ') or l.startswith('### '):
                break
            if l.startswith('- ') or l.startswith('> '):
                break
            para.append(l)
            i += 1
        blocks.append(('p', ' '.join(para)))

    return blocks


def render_astro(title, meta_lines, last_meta_raw, blocks, config):
    """Render parsed markdown to a complete .astro file."""
    indent = '  '
    parts = []

    # Header meta
    meta_html = '<br />'.join(meta_lines)

    parts.append('---')
    parts.append("import ThesisLayout from '../layouts/ThesisLayout.astro';")
    parts.append('---')
    parts.append('')
    parts.append('<ThesisLayout')
    parts.append(f'  title="{_escape_attr(title)}"')
    parts.append(f'  description="{_escape_attr(config["description"])}"')
    parts.append(f'  lang="{config["lang"]}"')
    parts.append('>')
    parts.append(f'{indent}<h1>{title}</h1>')
    parts.append(f'{indent}<p class="meta">{meta_html}</p>')
    parts.append('')

    for block in blocks:
        btype = block[0]

        if btype == 'hr':
            parts.append(f'{indent}<hr />')
            parts.append('')

        elif btype == 'h2':
            parts.append(f'{indent}<h2>{block[1]}</h2>')
            parts.append('')

        elif btype == 'h3':
            parts.append(f'{indent}<h3>{block[1]}</h3>')
            parts.append('')

        elif btype == 'p':
            parts.append(f'{indent}<p>{convert_inline(block[1])}</p>')
            parts.append('')

        elif btype == 'ul':
            parts.append(f'{indent}<ul>')
            for item in block[1]:
                parts.append(f'{indent}  <li>{convert_inline(item, autolink=True)}</li>')
            parts.append(f'{indent}</ul>')
            parts.append('')

        elif btype == 'blockquote':
            parts.append(f'{indent}<blockquote>')
            for line in block[1]:
                parts.append(f'{indent}  <p>{convert_inline(line)}</p>')
            parts.append(f'{indent}</blockquote>')
            parts.append('')

    # Trailing horizontal rule + meta
    parts.append(f'{indent}<hr />')
    parts.append('')
    if last_meta_raw:
        parts.append(f'{indent}<p class="meta">{convert_inline(last_meta_raw, autolink=True)}</p>')

    parts.append('</ThesisLayout>')
    parts.append('')

    return '\n'.join(parts)


def _escape_attr(s):
    """Escape double quotes for HTML attributes."""
    return s.replace('&', '&amp;').replace('"', '&quot;')


def check_quotes(source, lang):
    """Check for straight quotes that should be curly. Returns list of warnings."""
    warnings = []
    for i, line in enumerate(source.split('\n'), 1):
        for j, ch in enumerate(line):
            if ch == '"':
                ctx = line[max(0, j - 15):j + 16]
                warnings.append(f'  line {i}: straight double quote (U+0022) near: {ctx}')
            elif ch == "'":
                before = line[:j]
                if not re.search(r"[a-zA-Z]$", before):
                    ctx = line[max(0, j - 15):j + 16]
                    warnings.append(f"  line {i}: straight single quote (U+0027) near: {ctx}")
    return warnings


def sync(lang):
    cfg = CONFIGS[lang]
    source_path = cfg['source']

    if not os.path.exists(source_path):
        print(f'  ERROR: source not found: {source_path}')
        return False

    with open(source_path, 'r') as f:
        source = f.read()

    quote_warnings = check_quotes(source, lang)
    if quote_warnings:
        print(f'  ⚠ {len(quote_warnings)} straight quote(s) found in source:')
        for w in quote_warnings:
            print(w)

    title, meta_lines, last_meta_raw, blocks = parse_markdown(source)
    astro = render_astro(title, meta_lines, last_meta_raw, blocks, cfg)

    # Write .astro
    with open(cfg['astro'], 'w') as f:
        f.write(astro)
    print(f'  {cfg["astro"]}')

    # Copy raw markdown to public/
    shutil.copy2(source_path, cfg['public'])
    print(f'  {cfg["public"]}')

    return True


# ===========================================================================
# JOURNAL SYNC
#
# Pipeline per source file ~/wujilabs/journal/<prefix>-<lang>.md:
#   1. Parse filename into (prefix, lang). E.g. 2026-05-12-insights-zh.md
#      → prefix="2026-05-12-insights", lang="zh".
#   2. Extract date (first YYYY-MM-DD) and slug (the rest of the prefix).
#   3. Parse markdown via the existing thesis parser.
#   4. Detect language pair: if both <prefix>-en.md and <prefix>-zh.md exist,
#      write a langPair URL pointer in each generated .astro frontmatter.
#   5. Render .astro per essay → src/pages/journal/<prefix>{,-zh}.astro
#   6. Copy raw .md → public/journal/<prefix>-<lang>.md (for LLM access)
#   7. After processing all entries, write public/journal/index.json manifest.
# ===========================================================================

JOURNAL_FILENAME_RE = re.compile(r'^(\d{4}-\d{2}-\d{2})-(.+)-(en|zh)\.md$')


def parse_journal_filename(name):
    """('2026-05-12-insights-zh.md') → ('2026-05-12', 'insights', 'zh') or None."""
    m = JOURNAL_FILENAME_RE.match(name)
    if not m:
        return None
    return (m.group(1), m.group(2), m.group(3))


def journal_url(prefix, lang):
    """URL pattern per /plan-design-review lock: EN = /journal/<prefix>, ZH = /journal/<prefix>-zh."""
    return f"/journal/{prefix}" if lang == "en" else f"/journal/{prefix}-zh"


def render_journal_astro(title, meta_lines, last_meta_raw, blocks, *, lang, lang_pair_url):
    """Render a journal-entry .astro. Like render_astro, but:
       - imports paths are ../../layouts/ + ../../components/ (nested route)
       - embeds <SubscribeBlock /> before the back-link
       - if lang_pair_url is set, renders the cross-language toggle in the meta line
    """
    indent = '  '
    parts = []

    description = title  # short, page-specific; index manifest carries the full title

    parts.append('---')
    parts.append("import ThesisLayout from '../../layouts/ThesisLayout.astro';")
    parts.append("import SubscribeBlock from '../../components/SubscribeBlock.astro';")
    parts.append('---')
    parts.append('')
    parts.append('<ThesisLayout')
    parts.append(f'  title="{_escape_attr(title)}"')
    parts.append(f'  description="{_escape_attr(description)}"')
    parts.append(f'  lang="{"zh-Hans" if lang == "zh" else "en"}"')
    parts.append('>')
    parts.append(f'{indent}<h1>{title}</h1>')

    # Meta line(s). Always includes the dated byline. Cross-language toggle appended when pair exists.
    meta_html_parts = []
    if meta_lines:
        meta_html_parts.append('<br />'.join(meta_lines))
    if lang_pair_url:
        other_lang_label = 'EN' if lang == 'zh' else '中文'
        toggle = f'<a href="{lang_pair_url}" class="lang-toggle">{other_lang_label}</a>'
        meta_html_parts.append(toggle)
    if meta_html_parts:
        parts.append(f'{indent}<p class="meta">{" · ".join(meta_html_parts)}</p>')
    parts.append('')

    for block in blocks:
        btype = block[0]
        if btype == 'hr':
            parts.append(f'{indent}<hr />')
            parts.append('')
        elif btype == 'h2':
            parts.append(f'{indent}<h2>{block[1]}</h2>')
            parts.append('')
        elif btype == 'h3':
            parts.append(f'{indent}<h3>{block[1]}</h3>')
            parts.append('')
        elif btype == 'p':
            parts.append(f'{indent}<p>{convert_inline(block[1])}</p>')
            parts.append('')
        elif btype == 'ul':
            parts.append(f'{indent}<ul>')
            for item in block[1]:
                parts.append(f'{indent}  <li>{convert_inline(item, autolink=True)}</li>')
            parts.append(f'{indent}</ul>')
            parts.append('')
        elif btype == 'blockquote':
            parts.append(f'{indent}<blockquote>')
            for line in block[1]:
                parts.append(f'{indent}  <p>{convert_inline(line)}</p>')
            parts.append(f'{indent}</blockquote>')
            parts.append('')

    # Optional trailing meta + subscribe block. The thesis layout adds its own
    # back-link automatically; SubscribeBlock sits above it.
    if last_meta_raw:
        parts.append(f'{indent}<hr />')
        parts.append('')
        parts.append(f'{indent}<p class="meta">{convert_inline(last_meta_raw, autolink=True)}</p>')

    parts.append(f'{indent}<SubscribeBlock />')
    parts.append('</ThesisLayout>')
    parts.append('')

    # Minor CSS for the lang-toggle anchor in the meta line. Inline + scoped
    # to this page only; doesn't pollute the global design system.
    parts.append('<style is:global>')
    parts.append('  .meta .lang-toggle {')
    parts.append('    color: var(--text-2);')
    parts.append('    text-decoration: none;')
    parts.append('    border-bottom: 1px solid var(--rule);')
    parts.append('  }')
    parts.append('  .meta .lang-toggle:hover {')
    parts.append('    color: var(--link);')
    parts.append('    border-bottom-color: var(--link);')
    parts.append('  }')
    parts.append('</style>')

    return '\n'.join(parts)


def sync_journal():
    """Sync all journal entries from ~/wujilabs/journal/."""
    if not os.path.isdir(JOURNAL_SOURCE_DIR):
        print(f'  ERROR: journal source dir not found: {JOURNAL_SOURCE_DIR}')
        return False

    # Inventory: parse all source files first to detect language pairs.
    entries = []  # list of dicts: {prefix, lang, date, slug, source}
    for name in sorted(os.listdir(JOURNAL_SOURCE_DIR)):
        parsed = parse_journal_filename(name)
        if not parsed:
            continue  # skip README.md, drafts/, etc.
        date, slug_rest, lang = parsed
        prefix = f"{date}-{slug_rest}"
        entries.append({
            'prefix': prefix,
            'lang': lang,
            'date': date,
            'slug': slug_rest,
            'source': os.path.join(JOURNAL_SOURCE_DIR, name),
        })

    if not entries:
        print('  (no journal entries to sync)')
        return True

    # Pair detection: prefix → set of langs present
    prefix_to_langs = {}
    for e in entries:
        prefix_to_langs.setdefault(e['prefix'], set()).add(e['lang'])

    # Ensure output dirs exist.
    os.makedirs(JOURNAL_OUT_PAGES, exist_ok=True)
    os.makedirs(JOURNAL_OUT_PUBLIC, exist_ok=True)

    manifest_entries = []
    for e in entries:
        with open(e['source'], 'r') as f:
            source = f.read()

        title, meta_lines, last_meta_raw, blocks = parse_markdown(source)
        if not title:
            print(f"  WARN: no title in {e['source']}, skipping")
            continue

        # Determine lang pair URL
        langs_present = prefix_to_langs[e['prefix']]
        lang_pair_url = None
        if 'en' in langs_present and 'zh' in langs_present:
            other = 'zh' if e['lang'] == 'en' else 'en'
            lang_pair_url = journal_url(e['prefix'], other)

        astro = render_journal_astro(
            title, meta_lines, last_meta_raw, blocks,
            lang=e['lang'],
            lang_pair_url=lang_pair_url,
        )

        # Output filename: EN = <prefix>.astro, ZH = <prefix>-zh.astro
        astro_name = f"{e['prefix']}.astro" if e['lang'] == 'en' else f"{e['prefix']}-zh.astro"
        astro_path = os.path.join(JOURNAL_OUT_PAGES, astro_name)
        with open(astro_path, 'w') as f:
            f.write(astro)

        # Raw markdown copy for LLM access
        public_name = f"{e['prefix']}-{e['lang']}.md"
        public_path = os.path.join(JOURNAL_OUT_PUBLIC, public_name)
        shutil.copy2(e['source'], public_path)

        print(f"  {astro_path}")
        print(f"  {public_path}")

        manifest_entries.append({
            'prefix': e['prefix'],
            'lang': e['lang'],
            'date': e['date'],
            'title': title,
            'url': journal_url(e['prefix'], e['lang']),
            'lang_pair_url': lang_pair_url,
            'public_md': f"/journal/{public_name}",
        })

    # Sort manifest reverse-chronological for the index page.
    manifest_entries.sort(key=lambda x: (x['date'], x['prefix']), reverse=True)

    manifest_path = os.path.join(JOURNAL_OUT_PUBLIC, 'index.json')
    with open(manifest_path, 'w') as f:
        json.dump({'entries': manifest_entries}, f, indent=2, ensure_ascii=False)
    print(f'  {manifest_path}')

    return True


def main():
    args = sys.argv[1:]
    if not args:
        targets = ['thesis', 'journal']
    elif args == ['thesis']:
        targets = ['thesis']
    elif args == ['journal']:
        targets = ['journal']
    elif all(a in CONFIGS for a in args):
        # legacy: `sync-content.py zh` / `en` / `en zh`
        targets = [('thesis-' + a) for a in args]
    else:
        print('Unknown target(s):', args)
        print('Usage:')
        print('  sync-content.py                # everything')
        print('  sync-content.py thesis         # thesis EN + ZH')
        print('  sync-content.py journal        # journal entries')
        print('  sync-content.py en             # thesis EN (legacy)')
        print('  sync-content.py zh             # thesis ZH (legacy)')
        sys.exit(1)

    print('Syncing content...')
    for t in targets:
        if t == 'thesis':
            for lang in ['en', 'zh']:
                print(f'\n[THESIS {lang.upper()}]')
                sync(lang)
        elif t == 'journal':
            print(f'\n[JOURNAL]')
            sync_journal()
        elif t.startswith('thesis-'):
            lang = t.split('-', 1)[1]
            print(f'\n[THESIS {lang.upper()}]')
            sync(lang)

    print('\nDone. Run `bun run dev` to verify.')


if __name__ == '__main__':
    main()
