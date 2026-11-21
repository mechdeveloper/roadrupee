/** Light basemap for the ward map. One place to change the provider.
 *
 *  CARTO Positron was the first choice, but CARTO's keyless tile endpoints now return an
 *  "API KEY REQUIRED" placeholder image. Esri's World Light Gray Base is the closest keyless
 *  equivalent (pale grey, no labels, lets the ward colours carry the message).
 *
 *  To switch back to CARTO once you have a key, set:
 *    url:  "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png?api_key=YOUR_KEY" (and subdomains "abcd")
 *    attribution: '© OpenStreetMap contributors © CARTO'
 *  Attribution below is required by the provider and is always shown on the map. */
export const BASEMAP = {
  name: "Esri World Light Gray",
  url: "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}",
  attribution:
    "Tiles &copy; Esri &mdash; Esri, HERE, Garmin, &copy; OpenStreetMap contributors, and the GIS user community",
  maxZoom: 16,
  subdomains: undefined as string | undefined,
} as const;
