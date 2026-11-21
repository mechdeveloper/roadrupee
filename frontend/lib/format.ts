const CR = 1e7;
const LAKH = 1e5;

const grouped = new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 });

function trim(n: number, digits: number): string {
  return n.toFixed(digits).replace(/\.?0+$/, "");
}

/** Indian ₹ formatting: ₹3.07 Cr, ₹45 L, ₹12,345. */
export function inr(value: number): string {
  const v = Math.abs(value);
  const sign = value < 0 ? "−" : "";
  if (v >= CR) return `${sign}₹${trim(v / CR, 2)} Cr`;
  if (v >= LAKH) return `${sign}₹${trim(v / LAKH, v / LAKH >= 100 ? 0 : 1)} L`;
  return `${sign}₹${grouped.format(v)}`;
}

export function pct(value: number, digits = 1): string {
  return `${trim(value, digits)}%`;
}

export function num(value: number): string {
  return grouped.format(value);
}
