# Design System — wujilabs.dev

Source of truth for visual decisions on wujilabs.dev. Always read this before changing UI, fonts, color, spacing, or aesthetic direction. In QA mode, flag any code that contradicts this file.

Extracted 2026-05-27 via `/design-consultation` from the locked decisions in `/plan-design-review` (mockup at `~/.gstack/projects/WujiLabs-wujilabs.dev/designs/landing-phase1-20260526/variant-A-final-nochips.html`). Inputs: existing `src/styles/global.css`, self-hosted font bundle at `/fonts/fonts.css`, household strategy at `~/wujilabs/strategy/current-strategy.md`, content seeds at `~/wujilabs/site/content-seeds.md`.

---

## Product context

- **What this is:** Public surface of the Wuji Labs household — umbrella landing + founding thesis (EN/ZH) + practice/project pages + bilingual journal + mailing list.
- **Who it's for:** Three concurrent reader cohorts, served by one surface:
  1. Operator-firm buyers landing on `/wuji-labs` for the bundled offering (collaboration spaces + coaching + tools training)
  2. CEC-aligned readers landing on `/cec` for the human-side household positioning
  3. Thesis-aligned readers (aligned-angel candidates, builders, peers) landing on `/`, `/thesis`, `/journal/` for the substrate claim
- **Space/industry:** AI infrastructure + life coaching + indie tooling — household practice, not a SaaS startup.
- **Project type:** Hybrid — umbrella landing + content pages + ongoing journal. Not an app UI; not a marketing funnel; closer to a publishing imprint with one strong claim.

## The memorable thing

A visitor's first three seconds should land *"this is a publication, not a SaaS site"* — warm parchment, serif type, restrained whitespace, no decorative chrome. The interactive 4-dimension toggle is the only interactivity above the fold; everything else reads. The voice is share-what-I-know, anti-FOMO, observational — calibrated against Stoa / iA Writer / Bear / thoughtful therapist sites, not against SaaS landing pages.

---

## Aesthetic Direction

- **Direction:** Type-led publishing imprint with monastic restraint
- **Decoration level:** Minimal — typography and whitespace do all the work; no icons-in-circles, no decorative blobs, no gradient backgrounds, no shadows
- **Mood:** Calm, contemplative, sovereign. The site demonstrates the thesis it argues by being unhurried and self-respecting; it does not assert authority through visual loudness
- **Reference posture:** iA Writer, Bear, Tot, The Stoa, How to Live, Mindstone, well-made therapist sites. Specifically NOT: standard SaaS landing pages, dashboard UI kits, Linear-clone aesthetics

## Voice & marketing constraints

Per `~/wujilabs/site/content-seeds.md` "Marketing-voice constraints":

- **No FOMO copy** (no "limited", "before it's gone", "x companies signed up", countdown timers, early-client/founding-rate framing)
- **No pathologizing the reader** — they might be doing fine; the pitch is "another option if you want it," not "you need fixing"
- **No urgency manufactured around AI hype** — AI may disrupt, may not; the reader's call from their own ground
- **No status-filtering** — never "high-earning", "for executives", "for serious firms only"; describe the pain, let anyone self-identify
- **No master/servant language about AI** — "build with AI," "collaborate with AI," not "have AI do the work for you"
- **The editing question:** "would I say this to a thoughtful friend who's considering whether they have the problem we solve?" If not, rewrite

## Bilingual respect

Chinese characters are never subordinated to English on the same page. Chinese serif (Noto Serif SC) sits at the same weight as English serif (Source Serif 4); the `无忌` seal opens the landing in the brand's native script before the Latin wordmark. Journal entries pair ZH title (primary, full color) above EN title (secondary `--text-2`), not the other way around.

---

## Typography

- **Display / Hero:** **Source Serif 4** — variable font, `ital 0..1`, `opsz 8..60`, `wght 400/600/700`. Used for wordmark, page H1, card titles. Self-hosted at `/fonts/sourceserif4/*.woff2`.
- **Body:** **Source Serif 4** at 400, line-height 1.7. The same family as display — consistency over contrast for a publication feel.
- **Chinese body:** **Noto Serif SC** — `wght 400/600/700`. Pairs with Source Serif 4 in the same `font-family` declaration. Self-hosted with Google's Unicode-range subsetting preserved (Chinese chunks load only as needed; ~80 small woff2 files split by Unicode block).
- **UI / Utility / Nav:** **Source Sans 3** — `wght 400/600`. Used for nav links, toggle buttons, section labels, captions, form controls, footer.
- **Chinese UI / Utility:** **Noto Sans SC** — `wght 400`. Pairs with Source Sans 3 in the same `font-family` declaration.
- **Code:** **JetBrains Mono** — `wght 400`. Inline `<code>` and `<pre>` blocks.
- **Self-hosted:** All five families ship via `/fonts/fonts.css` — see `scripts/fetch-fonts.py` for the build. Chinese subsetting is preserved (~80 chunks for Noto Serif SC + ~80 for Noto Sans SC), so a page with only Latin characters never downloads CJK woff2 files. Self-hosting also bypasses Google Fonts blocking in mainland China — critical for the bilingual readership.

### Type scale

| Role | Size | Weight | Family |
|---|---|---|---|
| Hero wordmark | 2.5rem (40px) | 600 | Source Serif 4 |
| H1 (thesis) | 2rem (32px) | 700 | Source Serif 4 |
| H2 (section) | 1.5rem (24px) | 600 | Source Serif 4 |
| H3 (card title) | 1.15-1.2rem (18-19px) | 600 | Source Serif 4 |
| Substrate tagline | 1.25rem (20px) | 400 | Source Serif 4 |
| Body | 17px (landing) / 18px (thesis EN) / 17px (thesis ZH) | 400 | Source Serif 4 + Noto Serif SC |
| Body line-height | 1.7 (landing) / 1.8 (thesis EN) / 1.9 (thesis ZH) | — | — |
| UI / nav | 0.9-1rem (14-16px) | 400 | Source Sans 3 + Noto Sans SC |
| Section label | 0.78-0.8rem (12-13px), uppercase, letter-spacing 0.12-0.16em | 400 | Source Sans 3 |
| Meta / caption | 0.78-0.85rem (12-14px) | 400 | Source Sans 3 |
| Code | 0.9em relative | 400 | JetBrains Mono |

## Color

- **Approach:** Restrained. One palette for the entire site (landing + thesis + content + journal all share). One link accent. No per-section colors. No per-dimension colors. No decorative color.
- **Palette tokens** (CSS variables, defined in `src/styles/global.css`):

| Token | Light mode | Dark mode | Usage |
|---|---|---|---|
| `--bg` | `#f5f1eb` (warm parchment) | `#1a1a1a` (warm near-black) | Page background |
| `--text` | `#1a1a1a` | `#e0dcd7` | Primary body + headings |
| `--text-2` | `#666` | `#999` | Secondary body, muted text, italic framings |
| `--text-3` | `#777` | `#888` | Tertiary — dates, captions, footer copy (AA-compliant on body-sized text, ~4.7:1) |
| `--link` | `#2a5db0` (deep blue) | `#7ab3ef` (cool blue) | Links + interactive accents |
| `--rule` | `#ddd` | `#333` | Hairline separators, borders, input outlines |

- **Dark-mode strategy:** Automatic via `@media (prefers-color-scheme: dark)`. No manual toggle. Mirrors the existing thesis dark mode.
- **Semantic colors** (success / warning / error / info): not used yet. When introduced, derive from the existing palette — avoid the SaaS rainbow.

### Anti-slop palette rules

- No purple / violet / indigo backgrounds
- No gradient buttons or backgrounds
- No colored left-border on cards
- No icons-in-colored-circles
- No status-color bar across sections
- The single `--link` blue is the only chromatic accent — everything else is the parchment/text/rule neutral set

## Spacing

- **Base unit:** **8px** (`--space-unit: 8px`)
- **Density:** Generous on landing (whitespace is the breathing room); moderate on thesis (long-form reading); compact only in utility surfaces (form controls, section labels)
- **Pattern:** `calc(var(--space-unit) * N)` throughout. Common multipliers: `0.5, 1, 1.5, 2, 3, 4, 5, 6, 8, 10`. Avoid arbitrary px values outside this scale.
- **Content widths:** `--content-width-landing: 880px` (post-reorg, was 480px), `--content-width-thesis: 680px`.

## Layout

- **Approach:** Grid-disciplined for cards, editorial for prose. Both top-anchored, not vertically-centered.
- **Landing:** 2-column card grid (4×2 for 8 cards) on desktop, 1-column on mobile (`max-width: 720px`). Hero is top-left, not centered. Sections separated by single hairline `--rule`. No card backgrounds, no borders, no shadows — separator-only via whitespace and rules.
- **Thesis:** Single-column article container, `--content-width-thesis` (680px) max-width, generous vertical rhythm.
- **Header / nav:** Inline text links separated by middot. No logo bar. No persistent top-nav (each layout is standalone).
- **Footer:** Single row: `thesis · journal · about · subscribe · github · contact` + colophon line. Source Sans 3, `--text-3`.

### Responsive breakpoints

- `> 720px` — desktop layout, 2-col cards on landing
- `≤ 720px` — mobile layout, 1-col cards, larger tap targets (≥44px on toggle buttons, form controls, lang-pref labels), reduced page padding, smaller wordmark

### Border radius

- **Default: 0** — no rounded boxes. The site is type-led; corners stay sharp.
- **Form inputs / subscribe button:** `2px` — minimal softness for affordance, not bubbliness.
- **Never** uniform large radii on every element.

## Motion

- **Approach:** Minimal-functional. Motion exists only to support meaning, never to decorate.
- **Allowed:**
  - `transition: opacity 200ms` on toggle filter state (off-dim cards drop to 0.22 opacity)
  - `transition: color 120ms` on links and hover states
- **Disallowed:**
  - Entrance animations
  - Scroll-driven effects
  - Hover-lift / scale / shadow expansion
  - Spinners (use static "loading…" text)
- **Reduced motion:** Honor `prefers-reduced-motion: reduce` if/when animation expands.

## Accessibility

- **Touch targets:** ≥44px on all interactive elements on mobile (WCAG 2.5.5).
- **Contrast:** WCAG AA minimum on body text (4.5:1). `--text-3` at `#777` lifts the previous `#999` meta color into compliance.
- **Focus visible:** `outline: 2px solid var(--link); outline-offset: 4px;` on keyboard-focused interactive elements. Never `outline: none` without a replacement.
- **Live regions:** Dim-toggle framings use `aria-live="polite"` so screen readers announce changes when the user clicks a dimension.
- **Semantic landmarks:** `<header>`, `<nav>`, `<main>`, `<article>`, `<footer>` used per their actual meaning.
- **`aria-pressed`** on toggle buttons (the toggle is a single-select group).
- **Lang attribute:** `<html lang="en">` or `<html lang="zh-Hans">` per page.
- **No hover-only UI:** all interactive affordances render visibly without hover. Mobile-first by construction.

## Layouts (Astro)

The codebase ships with these layouts under `src/layouts/`:

- **`LandingLayout.astro`** — Phase 1 deliverable. Top-anchored, 880px max-width, parchment palette. Hosts the 4-dim toggle + framings + 8-card grid + journal + signup + footer pattern.
- **`ThesisLayout.astro`** — long-form article container, 680px max-width, same palette, dark-mode parity. Used by `/thesis`, `/thesis-zh`.
- **`ProjectLayout.astro`** — Phase 2 deliverable, variant of ThesisLayout for `/wuji-labs`, `/cec`, `/about`, `/projects/*`. Same palette, slightly wider content area.
- **`JournalLayout.astro`** — Phase 3 deliverable, ThesisLayout + subscribe CTA at bottom. Used by `/journal/[slug]`.

All four layouts share the same `--bg / --text / --text-2 / --text-3 / --link / --rule` token set defined in `src/styles/global.css`.

## Decisions Log

| Date | Decision | Rationale |
|---|---|---|
| 2026-05-27 | DESIGN.md created via /design-consultation | Fast-path extraction from /plan-design-review locked decisions + existing `src/styles/global.css` — no new research needed; the locked mockup is the visual reference |
| 2026-05-27 | Unified landing + thesis palette | Pre-reorg: landing dark-only, thesis cream/dark. Post-reorg: one parchment-base palette across all surfaces. "Less geeky, more humanized" per founder direction |
| 2026-05-27 | `--text-3 #777` introduced | Third text tier for dates/captions/footer; bumped from `#999` for WCAG AA compliance |
| 2026-05-27 | 44px mobile touch targets | WCAG 2.5.5 + Apple HIG + Material; mobile-only via `@media (max-width: 720px)` to preserve desktop typographic quietness |
| 2026-05-27 | No per-dimension chips on landing cards | Iterated: chips-always-visible felt redundant; chips-on-demand felt fiddly; no-chips was cleanest. Dim membership reads from which cards stay lit when filtering |
| 2026-05-27 | Em-dash separator for compound card titles | `Wuji Labs Inc — Collaboration Spaces`, `CEC — Life & Leadership Coaching`. Matches site house style (hero subtitle uses em-dash too) |
| 2026-05-27 | Toggle hide mechanism: `opacity: 0.22 + pointer-events: none + 200ms transition` | Preserves bounding box (no grid reflow); falls back to all-cards-visible without JS |
| 2026-05-27 | No `arianna.run` link in footer | Already has its own card on the landing; footer is for utility nav, not artifact promotion |

## How to extend this system

- **New page surface:** Use one of the four layouts. If a new layout is needed, branch from `ThesisLayout` and keep the same token set. Never introduce a new palette per page.
- **New component:** Check if it can be a type block + whitespace. If yes, do that. If it needs a card-like surface, use the no-background / hairline-rule / no-shadow pattern from the landing cards.
- **New token:** Append to `:root` in `src/styles/global.css` with a clear semantic name. Update both light and dark mode blocks together.
- **New font:** Run `scripts/fetch-fonts.py` after updating its source list. Keep the bundle CN-friendly (no fonts.googleapis.com calls at render time).
- **New interactive UI:** Match the toggle pattern — persistent labels, no hover-only states, aria attributes, keyboard support. If you find yourself adding a tooltip, ask whether a persistent inline label would work first.
- **New copy:** Pass the marketing-voice checklist above. Read like a thoughtful friend, not a sales site.
