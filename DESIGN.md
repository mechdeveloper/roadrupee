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

## App structure: answer the questions people actually ask

The app is **ward-first and mobile-first**. A citizen or ward officer arrives with a question; each screen answers one.

### Site map and owners
| Route | Question it answers | Owner |
|---|---|---|
| `/` | Where did Mumbai's repair money go? Pick a question, a ward, or trace a complaint | tech lead |
| `/ward/[slug]` | One ward, four tabs (below). `?tab=money\|held\|check\|next`, `?mode=officer` | tech lead |
| `/flag/[id]` | Why was this flagged, and how do you know? (evidence page) | tech lead (evidence endpoint: another session) |
| `/contractor/[id]` | How is this contractor doing, fairly? | tech lead |
| `/trace` | What happened to my complaint? | **Student B** (backend and page; the route is a placeholder until then) |
| `/audit` `/scorecards` `/plan` `/ask` | placeholders, replaced by the owner's `page.tsx` | per CLAUDE.md roles |

Ward page tabs, titled as questions: **a) Where did the money go?** (money) · **b) Did the fixes hold?** (held) · **c) What's worth checking?** (check) · **d) Where should the next rupee go?** (next). A "Claude's summary of this ward" card sits above the tabs and renders `ward.ai_summary` (`{en, hi, mr}`) only when present; otherwise it is hidden.

`slug` = ward code lower-cased, `/` → `-` (`G/S` → `g-s`). It is a field on every ward in `/api/wards`.

### Rules every screen follows
1. **Headings are questions. Answers are plain sentences with one big number.** No internal rule names (DLP_PAID, OVER_RATE…) in the UI; use `lib/plain.ts`.
2. **One idea per card.** Generous spacing, 44 px minimum tap targets, every icon has a text label (lucide).
3. **Colour always means the same.** Red/amber = didn't hold / worth checking. Teal = held / fine. Grey = no data or neutral context (rain, volume, chart scaffolding). Never use red/amber or teal for decoration, and never rely on colour alone.
4. **Every number links to its evidence; every screen ends with an action** (download, print, draft an RTI, open the work order).
5. **Fair wording** everywhere: "worth checking", "compared with what we'd expect", never "fraud" or blame.
6. **Languages:** EN / हिं / मरा toggle in the nav. UI strings come from the dictionary in `frontend/lib/i18n/` and never inline. English is complete; a missing Hindi or Marathi key falls back to English. Data-driven text (flag reasons, Claude explanations) is translated later. Hindi and Marathi copy needs a native-speaker review.
7. **States:** skeleton loading that keeps the final layout, friendly empty states that say what to try, error states with a retry. Never a stack trace.
8. **Motion:** smooth but subtle; everything must respect `prefers-reduced-motion`.
9. **Charts:** Recharts, styled only with tokens, ₹ in Indian formatting (`lib/format.ts`), no chart junk (no 3D, no gradients, no dual axes), and a text or table alternative for every chart.
10. **Small samples are labelled.** Any share or rate built from fewer than 10 jobs (per contractor in a ward, per repair type) shows a neutral "Few jobs: rough guide" chip, and a verdict word ("better" / "worse") is only used when the confidence interval excludes what's expected. Bars compare shares, never raw totals: a longer bar means more work, not worse work.
11. **Placeholders are labelled.** When a backend is not ready (`501`), show clearly marked example data behind the same TypeScript type. Never present placeholder data as real.

### Ward page details
- **Header:** ward name and areas, budget-vs-spent bar, "₹X didn't hold (Y%)", and a better / about as expected / worse chip (`verdict()` in `lib/plain.ts`).
- **Money tab:** contractor bars on every screen width (spend with a held/failed split), each tapping through to `/contractor/[id]`. A flow chart (budget → contractors → repair types → held/failed) is a desktop-only extra.
- **Held tab:** one big sentence with actual vs expected, then a monsoon timeline: daily rain bars (grey), red-alert days highlighted, repair-failure dots on top. Each dot means "repair completed this day, failed within 30 days" (the data has no failure date). Rain data ends 30 Sep, so October shows "no rainfall data".
- **Check tab:** flag cards (plain title, ₹, work order id, Claude verdict chip when present), filter by type, each card opens `/flag/[id]`.
- **Next tab:** ranked road cards from `/api/plan` (see CLAUDE.md "Planner contract"), a budget bar that fills as items are selected, Print and Share.
- **Officer mode** (`?mode=officer`): same page, with Print plan and Download CSV as the primary buttons in a sticky action bar.
