# RoadRupee — Design

Editorial, trustworthy: a data newsroom meets a modern dashboard. A ward officer or a citizen should understand the page in ten seconds and know what to do next.

## Principles
1. **Number first.** Lead with one big computed figure, then evidence beneath it.
2. **Fair wording.** Say "worth checking", "likely justified", "needs context". Never "fraud", "scam", "corrupt", "guilty". Every flag shows its evidence (work order ids) and the rule that raised it.
3. **Context beside blame.** Scorecards always show observed *and* expected values.
4. **Tokens only.** No hard-coded colours, sizes or fonts in components. Everything comes from the tokens below.

## Tokens (CSS variables in `frontend/app/globals.css`)
| Token | Value | Use |
|---|---|---|
| `--bg` | `#FAF7F2` | page background (warm off-white) |
| `--surface` | `#FFFFFF` | cards |
| `--ink` | `#1B1F23` | body text |
| `--muted` | `#5F6B76` | secondary text (AA on `--bg`) |
| `--border` | `#E4DED3` | hairlines |
| `--accent` | `#0F5C5C` | the ONE accent (deep teal): links, buttons, focus |
| `--accent-soft` | `#DCEBEA` | accent tint backgrounds |
| `--scale-1..5` | `#B2182B` `#E08A3C` `#F2C75C` `#6FB3A8` `#1F7A7A` | colour-blind-safe data scale, red → amber → teal |
| `--scale-none` | `#E9E5DC` | no data |

Data scale: ordered by lightness as well as hue, so it survives deuteranopia and greyscale. Never encode meaning by colour alone: always add a label, value or icon.

For the choropleth, **red = more money that didn't hold**; teal = less.

## Type
- Inter (via `next/font`), `font-variant-numeric: tabular-nums` on every number.
- Scale: hero 56/60 (mobile 36/40), h2 24, body 16, caption 13. Headlines use tight tracking.

## Money formatting (`frontend/lib/format.ts`)
- Indian digit grouping: `₹12,34,567`.
- ≥ ₹1 Cr → `₹3.07 Cr`; ≥ ₹1 L → `₹45 L` (drop trailing zeros); otherwise full grouped rupees.
- Percentages to one decimal place at most.

## Layout
- Max width 1100px, 8px spacing grid, cards radius 12px, one soft shadow level.
- Mobile first: cards stack, the map goes full width, 44px minimum tap targets.

## States (every data component)
- **Loading:** skeleton blocks that keep the final layout (no spinners alone).
- **Empty:** a sentence saying what is missing and what to try.
- **Error:** plain message plus a "Try again" button. Never show a stack trace.

## Accessibility
- Contrast ≥ 4.5:1 for text. Visible focus ring in `--accent`.
- Map has a text alternative: a ranked table of wards below it.
- Respect `prefers-reduced-motion` (the animated complaint trail falls back to a static list).

## Language
UI strings are English. Claude-written summaries and the complaint trace can answer in EN / HI / MR; those are generated, not hard-coded.
