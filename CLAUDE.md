# wujilabs.dev

The household umbrella site for Wuji Labs — Astro 6 + Cloudflare Workers Static Assets, bilingual (EN + ZH), self-hosted fonts.

## Design System

**Always read `DESIGN.md` before making any visual or UI decisions.** All font choices, colors, spacing, layouts, motion, accessibility rules, and aesthetic direction are defined there. Do not deviate without explicit user approval. In QA mode, flag any code that doesn't match DESIGN.md.

The site has a single unified palette across landing + thesis + content pages (parchment `#f5f1eb` / dark `#1a1a1a` / link `#2a5db0` / rule `#ddd` light mode, with dark-mode mirror). Type-led publishing-imprint aesthetic. No decorative chrome, no gradient backgrounds, no hover-only UI. See DESIGN.md for the full token + layout + voice spec.

## Project structure

```
src/
  layouts/
    LandingLayout.astro   # Phase 1 — umbrella landing (4-dim toggle + 8 cards)
    ThesisLayout.astro    # Long-form thesis (EN + ZH)
    # ProjectLayout.astro — Phase 2 (wuji-labs, cec, projects/*, about)
    # JournalLayout.astro — Phase 3 (journal/[slug])
  pages/
    index.astro           # Landing
    thesis.astro          # /thesis (founding thesis EN)
    thesis-zh.astro       # /thesis-zh (founding thesis ZH)
  styles/
    global.css            # CSS variables + reset + base typography
  content/                # Astro content collections (when used)
public/
  fonts/                  # Self-hosted woff2 + fonts.css
  thesis.md               # Raw EN thesis markdown (served to LLMs)
  thesis-zh.md            # Raw ZH thesis markdown (served to LLMs)
  llms.txt                # Index for AI readers
  llms-full.txt           # Generated — full essay bundle for one-shot LLM context
  _headers                # Cloudflare cache + content-type headers
scripts/
  sync-content.py         # Sync thesis (and Phase 3+: journal) from source markdown
  fetch-fonts.py          # Download Google Fonts CSS + woff2s for self-hosting (CN-friendly)
  build-llms-full.py      # Concat public/llms.txt + linked .md files into llms-full.txt
astro.config.mjs
wrangler.jsonc            # Cloudflare deploy config
```

## Build pipeline

- `bun run dev` — Astro dev server at `http://localhost:4321/`
- `bun run build` — Runs `scripts/build-llms-full.py` then `astro build`. Output goes to `dist/`.
- `bun run sync` — `scripts/sync-content.py`; syncs thesis (and journal once Phase 3 lands) from source markdown into `public/` + `src/pages/`.
- Push to `main` → CI deploys to Cloudflare Workers via `wrangler-action`.

## Source-of-truth docs (off-repo)

- **Strategy / decisions:** `~/wujilabs/strategy/current-strategy.md` + `~/wujilabs/strategy/decisions-log.md`
- **Site reorg plan:** `~/wujilabs/site/reorg-plan.md` (structural scope + locked design decisions)
- **Content seeds:** `~/wujilabs/site/content-seeds.md` (per-page copy)
- **Office-hours design docs:** `~/.gstack/projects/wujilabs/cosimodw-main-design-*.md`
- **Approved landing mockup:** `~/.gstack/projects/WujiLabs-wujilabs.dev/designs/landing-phase1-20260526/variant-A-final-nochips.html`
- **Founding thesis (source):** `~/wujilabs/launch-2026-05-01/thesis-draft-{en,zh}.md`
- **Journal essays (source):** `~/wujilabs/journal/[YYYY-MM-DD]-[slug]-{en,zh}.md`

## Marketing voice constraints

See `DESIGN.md` "Voice & marketing constraints" section. The short form: **anti-FOMO, anti-pathologizing, no status-filtering, no master/servant language about AI.** If copy wouldn't pass the "would I say this to a thoughtful friend" test, rewrite.

## Skill routing

When the user's request matches an available skill, invoke it via the Skill tool. When in doubt, invoke the skill.

Key routing rules:
- Product ideas/brainstorming → invoke /office-hours
- Strategy/scope → invoke /plan-ceo-review
- Architecture → invoke /plan-eng-review
- Design system/plan review → invoke /design-consultation or /plan-design-review
- Full review pipeline → invoke /autoplan
- Bugs/errors → invoke /investigate
- QA/testing site behavior → invoke /qa or /qa-only
- Code review/diff check → invoke /review
- Visual polish → invoke /design-review
- Ship/deploy/PR → invoke /ship or /land-and-deploy
- Save progress → invoke /context-save
- Resume context → invoke /context-restore
- Author a backlog-ready spec/issue → invoke /spec
