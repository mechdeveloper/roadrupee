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
| `--scale-1..5` | `#B2182B` `#E39A4E` `#D8D3C7` `#86C1BA` `#1F7A7A` | map and table scale: warm red/amber = a higher share of repair spend didn't hold, teal = held better |
| `--scale-none` | `#EFECE5` | no data |
| `--hero-sky-top` / `--hero-sky-bottom` | `#E3EBF2` → `#FAF7F2` (`--bg`) | the soft monsoon gradient behind the hero, fading into the page |
| `--hero-muted` | `#4E5A66` | secondary text on the gradient |
| `--rain` | `rgba(60, 80, 105, 0.08)` | faint rain streaks |

**The map and swatches are coloured by the SHARE of a ward's repair spend that didn't hold (% failed spend), never by absolute ₹.** Absolute ₹ would only highlight the wards that spend the most, which is unfair. ₹ appears in the tooltip next to the share: "₹X didn't hold — Y% of this ward's repair spend". Bins are **rank-based quintiles of that share** across the 24 wards (highest fifth = deep red … lowest fifth = teal), so the scale always uses its full range and the same colour means the same thing on the map, the table and the legend. Legend: "Higher share didn't hold ← → Held better", with the % range of each bin.

Why this scale: we ran the palette validator on an early red→amber→yellow→teal ramp. It is not lightness-monotonic (yellow, the lightest step, sat in the middle), so in greyscale or with colour-vision deficiency dark red and dark teal looked alike. The current scale is lightness-symmetric: OKLab L = 0.49 (red), 0.74 (amber), 0.85 (neutral), 0.77 (light teal), 0.53 (teal), so each end is dark and the middle is light. Amber and light teal have similar lightness but sit on opposite sides of the blue–yellow axis, which colour-blind viewers keep. Colour is never the only signal: every ward has a tooltip value, a legend label and a row in the ranked table.

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

## Hero: light monsoon

The app stays **light**: a public audience, phones in daylight, and printing. No dark theme.

- **Background:** a very soft sky-blue-grey gradient (`--hero-sky-top` → `--hero-sky-bottom`) that blends into `--bg` so there is no hard edge below the hero. Full width, `min-height: 100svh` on desktop.
- **Rain:** a canvas behind the content, about 60 thin diagonal streaks at ~8% opacity, slow, 30 fps cap, device pixel ratio ≤ 1.5. It runs only while the hero is on screen and the tab is visible, and is **not rendered at all** under `prefers-reduced-motion`. Text never sits on anything stronger than the gradient plus the faint streaks.
- **Headline:** eyebrow "MUMBAI MONSOON ROADS 2025", then a count-up of the failed spend from `/api/summary` in `--scale-1` (deep red), then "of ₹13.43 Cr in repairs didn't hold for 30 days." (total also from the API). The count-up ends on exactly the formatted value.
- **Every ₹100 bar:** 100 tiles. The failed share (rounded from the API) cracks and drops away once, staggered over ~1.2 s, leaving dashed ghost slots. Caption: "₹23 of every ₹100 cracked and fell away" (number computed). Static final state under reduced motion.
- **Map:** large, on a light grey basemap (Esri World Light Gray; see `frontend/lib/basemap.ts`) with the provider's attribution always visible. CARTO Positron was the first choice, but CARTO's keyless tile endpoints now serve an "API KEY REQUIRED" placeholder, so switching back needs a CARTO key (two-line change in `basemap.ts`). Wards filled with the scale above at ~0.8 opacity with a white 1.5 px outline. The top 3 wards by share pulse gently (3 s, off under reduced motion). Hover tooltip, click opens the ward panel. Ward boundaries are approximate, and a note says so.
- **Trace my complaint:** a large (56 px) search in the hero. The placeholder rotates every ~3.5 s through a Marathi, a Hinglish, an English and a complaint-ID example (real rows from the dataset), and pauses while the box is focused or has text. The accessible name is fixed so screen readers don't hear the rotation.
- **Nav:** "₹ RoadRupee" wordmark plus Audit · Scorecards · Next rupee · Ask, 44 px targets.
- **Below the hero:** the three stat cards fade and slide up 12 px on scroll (staggered, once), then the ward ranking.
- **Mobile order:** headline → ₹100 bar → map → search.

### Contrast (WCAG, computed)
| Text | on `#E3EBF2` (hero top) | on `#FAF7F2` (hero bottom) |
|---|---|---|
| `--ink` `#1B1F23` | 13.8:1 | 15.5:1 |
| `--hero-muted` `#4E5A66` | 5.9:1 | 6.6:1 |
| `--scale-1` text `#B2182B` (headline number) | 5.7:1 | 6.4:1 |
| `--accent` `#0F5C5C` | 6.4:1 | 7.3:1 |
| white on `--accent` (buttons) | 7.8:1 | |

The older `--muted` (`#5F6B76`) is only 4.5:1 on the hero top, so hero copy uses `--hero-muted`.

### Ward panel (plain language)
Opened from a map click or a ranking row: a side sheet on desktop, a bottom sheet on mobile. Sections: **Budget vs spent**, **Repairs that didn't hold** (₹ and % of spend), a **better / about as expected / worse** comparison with the ward's rain and flooding (numbers in a "How we calculate this" tooltip), the **top 5 "worth checking" items** each with its work order ID as evidence, and **Download this ward's data (CSV)**.

### Plain-language labels (no internal rule names in the UI)
| Internal | Shown to people |
|---|---|
| OVER_RATE | Billed well above the standard rate |
| DOUBLE_BILL | Same repair billed twice within a week, no complaint linked |
| DLP_PAID | City paid for a repair the original contractor should cover |
| SLA_BREACH | Took more than twice the target time |
| REPEAT_FAILURE | Same fix by the same contractor failed again |
| DLP / warranty | "still under the contractor's warranty" |
| observed vs expected reopen | "compared to what we'd expect for this ward's rain and flooding" |
