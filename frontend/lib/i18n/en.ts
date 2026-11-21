/** English UI strings: the source of truth. Add a key here first; hi.ts / mr.ts may lag (they fall back to English). */
export const en = {
  // common
  "common.retry": "Try again",
  "common.error": "We couldn't load this just now.",
  "common.close": "Close",
  "common.csv": "Download data (CSV)",
  "common.print": "Print",
  "common.share": "Share",
  "common.openWard": "Open full ward report",
  "common.back": "Back",
  "common.synthetic": "All data is synthetic and all contractors are fictional.",
  "common.fairNote": "These are worth checking, not conclusions about anyone.",

  // nav
  "nav.audit": "Audit",
  "nav.scorecards": "Scorecards",
  "nav.next": "Next rupee",
  "nav.ask": "Ask",
  "nav.language": "Language",

  // hero
  "hero.eyebrow": "MUMBAI MONSOON ROADS 2025",
  "hero.rest": "of {total} in repairs didn't hold for 30 days.",
  "hero.bar.caption": "₹{n} of every ₹100 cracked and fell away",
  "hero.trace.title": "Trace my complaint",
  "hero.trace.help": "Paste it in Marathi, Hindi, Hinglish or English, or type a complaint ID.",
  "hero.trace.button": "Trace",
  "hero.trace.aria": "Complaint text or complaint ID",
  "hero.trace.soon": "Complaint tracing is being built today. Check back soon.",
  "hero.trace.error": "Something went wrong. Please try again.",
  "map.higher": "Higher share didn't hold",
  "map.better": "Held better",
  "map.note":
    "Share of each ward's repair spend on fixes reopened within 30 days. Click a ward for details. Ward boundaries are approximate.",

  // home
  "entry.trace.title": "Trace my complaint",
  "entry.trace.desc": "Follow a complaint to the repair, the contractor and the result.",
  "entry.trace.cta": "Trace it",
  "entry.explore.title": "Explore your ward",
  "entry.explore.desc": "Search by ward or locality, in English or Devanagari.",
  "entry.explore.cta": "Find my ward",
  "entry.officer.title": "I'm a ward officer",
  "entry.officer.desc": "Open your ward's plan, items worth checking and data downloads.",
  "entry.officer.cta": "Pick my ward",
  "stat.warranty.label": "Paid for repairs still under the contractor's warranty",
  "stat.warranty.note":
    "{n} surface repairs the original contractor may owe at no cost. Another {m} on warranty roads is worth reviewing.",
  "stat.rate.label": "Billed above the standard rate",
  "stat.rate.note":
    "Extra charged on {n} jobs billed over 1.5× the standard rate. Normal ±30% variation is not counted.",
  "stat.fatal.label": "Fatal accidents linked to potholes, waterlogging and open chambers",
  "stat.fatal.note": "Plus {n} accidents with grievous injuries.",
  "home.glance.title": "Wards at a glance",
  "home.glance.sub":
    "Share of each ward's own repair spend that didn't hold. Tap a ward for its full report.",
  "tile.didnthold": "didn't hold",

  // ward picker
  "picker.title.explore": "Find your ward",
  "picker.title.officer": "Pick your ward",
  "picker.placeholder": "Type a ward or locality (e.g. Dadar, दादर)",
  "picker.hint": "Works in English and Devanagari.",
  "picker.empty": "No match. Try a nearby locality or the ward letter.",
  "picker.ward": "Ward {code}",

  // verdict
  "verdict.better": "better than expected",
  "verdict.expected": "about as expected",
  "verdict.worse": "worse than expected",

  // ward page
  "ward.tab.money": "Where did the money go?",
  "ward.tab.held": "Did the fixes hold?",
  "ward.tab.check": "What's worth checking?",
  "ward.tab.next": "Where should the next rupee go?",
  "ward.budget": "Budget vs spent",
  "ward.spentOf": "{spent} of {budget}",
  "ward.left": "{amount} left",
  "ward.over": "{amount} over budget",
  "ward.didnthold": "{amount} didn't hold ({pct})",
  "ward.summary.title": "Claude's summary of this ward",
  "ward.officer.badge": "Officer view",
  "ward.notFound": "We couldn't find that ward.",
  "ward.notFound.hint": "Pick a ward from the home page.",
} as const;

export type Key = keyof typeof en;
