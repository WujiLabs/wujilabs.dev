#!/usr/bin/env python3
"""
Sync thesis content from source markdown to Astro pages and public/ raw copies.

Usage:
  python3 scripts/sync-content.py          # sync both EN and ZH
  python3 scripts/sync-content.py zh       # sync ZH only
  python3 scripts/sync-content.py en       # sync EN only

Source: ~/wujilabs/launch-2026-05-01/thesis-draft-{en,zh}.md
Targets:
  src/pages/thesis.astro, src/pages/thesis-zh.astro   (HTML rendering)
  public/thesis.md, public/thesis-zh.md               (raw markdown for AI access)
"""

import re
import sys
import os
import shutil

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SITE_DIR = os.path.dirname(SCRIPT_DIR)
SOURCE_DIR = os.path.expanduser("~/wujilabs/launch-2026-05-01")

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


def main():
    targets = sys.argv[1:] if len(sys.argv) > 1 else ['en', 'zh']

    for lang in targets:
        if lang not in CONFIGS:
            print(f'Unknown target: {lang}. Use "en" or "zh".')
            sys.exit(1)

    print('Syncing thesis content...')
    for lang in targets:
        print(f'\n[{lang.upper()}]')
        sync(lang)

    print('\nDone. Run `bun run dev` to verify.')


if __name__ == '__main__':
    main()
