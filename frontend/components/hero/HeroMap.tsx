"use client";

import type { Feature, FeatureCollection } from "geojson";
import L, { type Layer, type PathOptions } from "leaflet";
import { useEffect, useMemo, useRef } from "react";
import { GeoJSON, MapContainer, Marker, TileLayer } from "react-leaflet";
import type { Ward } from "@/lib/api";
import { inr, pct } from "@/lib/format";
import { BASEMAP } from "@/lib/basemap";
import { type Bins, cssVar } from "@/lib/scale";

type Props = {
  geo: FeatureCollection;
  wards: Ward[];
  bins: Bins;
  onSelect: (wardCode: string) => void;
};

export default function HeroMap({ geo, wards, bins, onSelect }: Props) {
  const byCode = useMemo(() => new Map(wards.map((w) => [w.ward_code, w])), [wards]);
  const bounds = useMemo(() => L.geoJSON(geo).getBounds(), [geo]);
  const labels = useMemo(
    () =>
      geo.features.map((f) => ({
        code: f.properties?.ward_code as string,
        pos: L.geoJSON(f).getBounds().getCenter(),
        icon: L.divIcon({ className: "ward-label", html: String(f.properties?.ward_code ?? ""), iconSize: [40, 16], iconAnchor: [20, 8] }),
      })),
    [geo],
  );
  const selectRef = useRef(onSelect);
  useEffect(() => {
    selectRef.current = onSelect;
  }, [onSelect]);

  const style = (f?: Feature): PathOptions => {
    const code = f?.properties?.ward_code as string | undefined;
    const bin = code ? bins.byCode.get(code) : undefined;
    return {
      fillColor: cssVar(bin?.token ?? "--scale-none"),
      fillOpacity: 0.8,
      color: cssVar("--surface"),
      weight: 1.5,
      className: code && bins.top3.includes(code) ? "ward-pulse" : undefined,
    };
  };

  const onEach = (f: Feature, layer: Layer) => {
    const code = f.properties?.ward_code as string;
    const w = byCode.get(code);
    if (!w) return;
    const el = document.createElement("div");
    const title = document.createElement("strong");
    title.textContent = `Ward ${w.ward_code} · ${w.ward_name}`;
    const body = document.createElement("div");
    body.textContent = `${inr(w.failed_spend_inr)} didn't hold — ${pct(w.failed_pct)} of this ward's repair spend`;
    el.append(title, body);
    layer.bindTooltip(el, { sticky: true });
    layer.on("click", () => selectRef.current(code));
  };

  return (
    <MapContainer
      bounds={bounds}
      boundsOptions={{ padding: [16, 16] }}
      scrollWheelZoom={false}
      zoomSnap={0.25}
      className="h-[360px] w-full rounded-2xl border shadow-sm sm:h-[440px] lg:h-[540px]"
    >
      <TileLayer url={BASEMAP.url} attribution={BASEMAP.attribution} maxZoom={BASEMAP.maxZoom} />
      <GeoJSON data={geo} style={style} onEachFeature={onEach} />
      {labels.map((l) => (
        <Marker key={l.code} position={l.pos} icon={l.icon} interactive={false} keyboard={false} />
      ))}
    </MapContainer>
  );
}
