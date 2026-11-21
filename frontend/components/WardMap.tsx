"use client";

import type { Feature, FeatureCollection } from "geojson";
import type { Layer, PathOptions } from "leaflet";
import { useMemo } from "react";
import { GeoJSON, MapContainer } from "react-leaflet";
import { inr, pct } from "@/lib/format";
import type { Ward } from "@/lib/api";
import { binFor, cssVar } from "@/lib/scale";

type Props = { geo: FeatureCollection; wards: Ward[]; cityPct: number };

export default function WardMap({ geo, wards, cityPct }: Props) {
  const byCode = useMemo(() => new Map(wards.map((w) => [w.ward_code, w])), [wards]);

  const style = (f?: Feature): PathOptions => {
    const w = byCode.get(f?.properties?.ward_code);
    const fill = w ? cssVar(binFor(w.failed_pct, cityPct).token) : cssVar("--scale-none");
    return { fillColor: fill, fillOpacity: 0.9, color: cssVar("--surface"), weight: 1.5 };
  };

  const onEach = (f: Feature, layer: Layer) => {
    const w = byCode.get(f.properties?.ward_code);
    if (!w) return;
    const el = document.createElement("div");
    const title = document.createElement("strong");
    title.textContent = `Ward ${w.ward_code} · ${w.ward_name}`;
    const body = document.createElement("div");
    body.textContent =
      `${inr(w.failed_spend_inr)} didn't hold (${pct(w.failed_pct)} of ${inr(w.spend_inr)}). ` +
      `Budget ${inr(w.budget_inr)}.`;
    el.append(title, body);
    layer.bindTooltip(el, { sticky: true });
  };

  return (
    <MapContainer
      bounds={[[18.89, 72.77], [19.28, 73.0]]}
      zoomControl
      scrollWheelZoom={false}
      className="h-[560px] w-full rounded-xl border"
      attributionControl={false}
    >
      <GeoJSON data={geo} style={style} onEachFeature={onEach} />
    </MapContainer>
  );
}
