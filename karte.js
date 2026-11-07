/* Kiezatlas Potsdam: freie Karte. Nichts bewegt sich von selbst; Kamera ändert sich nur auf ausdrücklichen Wunsch.
   Zustand steht im Hash (teilbar), z. B. karte.html#thema=fern&st=13&3d=1&k=13.2/52.40/13.05/50/-10 */
(function () {
"use strict";
var K = window.KIEZ_KENNZAHLEN, ST = window.KIEZ_STADTTEILE, Z = window.KIEZ_ZELLEN;
var T = window.KIEZ_THEMEN, fmt = T.fmt, fmt1 = T.fmt1, NB = "\u00a0";
var RUHIG = matchMedia("(prefers-reduced-motion: reduce)").matches, SCHMAL = matchMedia("(max-width:860px)").matches, FEIN = matchMedia("(hover:hover) and (pointer:fine)").matches;
function el(t, c, x) { var e = document.createElement(t); if (c) e.className = c; if (x != null) e.textContent = x; return e; }
var rundEw = T.rundEw, proz = T.proz, name = T.name, kachel = T.kachel, esc = T.esc;

// ---------- Farben und Themen: gemeinsamer Kern in themen.js (wie auf der Startseite)
var FARBE = T.FARBE, BEZIRKFARBE = T.BEZIRKFARBE, TEIL = T.TEIL, STUFEN = T.STUFEN;
var THEMEN = T.THEMEN, THEMA = T.THEMA, HASHTHEMA = T.HASH, KLASSEN = T.KLASSEN;
var farbe = T.farbe, umriss = T.umriss, GANZ = T.GANZ;
// „3D-Häuser“ ohne gewählten Stadtteil und ohne Stadtteil unter der Kartenmitte: Innenstadt
var HAUS_ERSATZ = "41";

// ---------- Zustand aus dem Hash
var S = { thema: "stadtteile", nr: "", d3: false, luft: false, geb: false, kam: null };
// Gebäude hat erst „3D-Häuser“ eingeschaltet: beim Ausschalten wieder aus. Steht im Link als 3d=1 ohne geb=1
// (hashSchreiben schreibt geb=1 nur für Gebäude, die unabhängig von 3D an sind), damit die Kopplung die Rundreise übersteht
var gebDurch3D = false;
(function () {
  function dek(x) { try { return decodeURIComponent(x); } catch (e) { return ""; } }   // verstümmelte Links nicht tödlich
  var h = {}; location.hash.replace(/^#/, "").split("&").forEach(function (p) { var kv = p.split("="); if (kv[0]) h[dek(kv[0])] = dek(kv[1] || ""); });
  if (HASHTHEMA[h.thema]) S.thema = HASHTHEMA[h.thema];
  if (h.st && K.stadtteile[h.st]) S.nr = h.st;
  S.d3 = h["3d"] === "1"; S.luft = h.luft === "1"; S.geb = h.geb === "1" || S.d3;   // 3D heißt Häuser (auch in alten Links)
  gebDurch3D = S.d3 && h.geb !== "1";
  if (h.k) { var k = h.k.split("/").map(Number); if (k.length >= 3 && k.every(function (x) { return !isNaN(x); })) S.kam = { zoom: k[0], center: [k[2], k[1]], pitch: k[3] || 0, bearing: k[4] || 0 }; }
})();
function hashSchreiben() {
  if (!bereit) return;
  var c = map.getCenter(), teile = ["thema=" + THEMA[S.thema].h];
  if (S.nr) teile.push("st=" + S.nr);
  if (S.d3) teile.push("3d=1"); if (S.luft) teile.push("luft=1"); if (S.geb && !(S.d3 && gebDurch3D)) teile.push("geb=1");
  teile.push("k=" + [map.getZoom().toFixed(2), c.lat.toFixed(5), c.lng.toFixed(5), Math.round(map.getPitch()), Math.round(map.getBearing())].join("/"));
  try { history.replaceState(null, "", "#" + teile.join("&")); } catch (e) { /* file:// in manchen Browsern */ }
}

// ---------- Karte
var LEER = { type: "FeatureCollection", features: [] }, bereit = false;
var start = S.kam ? { center: S.kam.center, zoom: S.kam.zoom, pitch: S.kam.pitch, bearing: S.kam.bearing } : { bounds: GANZ, fitBoundsOptions: { padding: SCHMAL ? 16 : 40 } };
var map = new maplibregl.Map(Object.assign({
  container: "karte",
  style: T.grundkarte({ version: 8, sources: {
      basemap: { type: "raster", tileSize: 256, maxzoom: 18, tiles: ["https://sgx.geodatenzentrum.de/wmts_basemapde/tile/1.0.0/de_basemapde_web_raster_grau/default/GLOBAL_WEBMERCATOR/{z}/{y}/{x}.png"],
        attribution: 'Hintergrund © <a href="https://www.bkg.bund.de">GeoBasis-DE / BKG</a> (2026) <a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>' },
      dop: { type: "raster", tileSize: 256, maxzoom: 20, tiles: ["https://isk.geobasis-bb.de/mapproxy/dop20c/service/wms?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&LAYERS=bebb_dop20c&STYLES=&CRS=EPSG:3857&BBOX={bbox-epsg-3857}&WIDTH=256&HEIGHT=256&FORMAT=image/jpeg"],
        attribution: 'Luftbild © GeoBasis-DE/LGB, <a href="https://www.govdata.de/dl-de/by-2-0">dl-de/by-2-0</a>' },
      zellen: { type: "geojson", data: Z, attribution: 'Zensus 2022 © Statistische Ämter des Bundes und der Länder, <a href="https://www.govdata.de/dl-de/by-2-0">dl-de/by-2-0</a>, eigene Auswertung' },
      teile: { type: "geojson", data: ST, promoteId: "nr", attribution: "Stadtteile © Landeshauptstadt Potsdam, dl-de/zero-2-0" },
      gebaeude: { type: "geojson", data: LEER, attribution: 'Gebäude © GeoBasis-DE/LGB, <a href="https://www.govdata.de/dl-de/by-2-0">dl-de/by-2-0</a> (Daten geändert)' } },
    layers: [
      { id: "papier", type: "background", paint: { "background-color": "#e6e9e4" } },
      { id: "basemap", type: "raster", source: "basemap", paint: { "raster-opacity": 0.6, "raster-saturation": -1 } },
      { id: "dop", type: "raster", source: "dop", layout: { visibility: "none" } },
      { id: "teile-flaeche", type: "fill", source: "teile", paint: { "fill-color": ["get", "farbe"], "fill-opacity": 0.72 } },
      { id: "zellen-2d", type: "fill", source: "zellen", layout: { visibility: "none" }, paint: { "fill-color": STUFEN[2], "fill-opacity": 0.85 } },
      // zellen-3d: bleibt als Ebene bestehen, ist aber immer aus; 3D zeigt nur Häuser (Andre 07.11.)
      { id: "zellen-3d", type: "fill-extrusion", source: "zellen", layout: { visibility: "none" }, paint: { "fill-extrusion-color": STUFEN[2], "fill-extrusion-height": 0, "fill-extrusion-opacity": 0.94, "fill-extrusion-vertical-gradient": true } },
      { id: "gebaeude2d", type: "fill", source: "gebaeude", layout: { visibility: "none" }, paint: { "fill-color": "#24363b", "fill-opacity": 0.45 } },
      { id: "gebaeude3d", type: "fill-extrusion", source: "gebaeude", layout: { visibility: "none" }, paint: { "fill-extrusion-color": "#aebfbf", "fill-extrusion-height": ["get", "h"], "fill-extrusion-opacity": 0.95, "fill-extrusion-vertical-gradient": true } },
      { id: "teile-linie", type: "line", source: "teile", paint: { "line-color": "#ffffff", "line-width": 1.2, "line-opacity": 0.9 } },
      { id: "teile-wahl", type: "line", source: "teile", paint: { "line-color": "#6a2c82", "line-width": ["case", ["boolean", ["feature-state", "gewaehlt"], false], 3.2, 0] } }
    ] }),
  maxZoom: 19, maxPitch: 70, attributionControl: false, fadeDuration: RUHIG ? 0 : 300, cooperativeGestures: false,
  locale: { "GeolocateControl.FindMyLocation": "Meinen Standort zeigen", "GeolocateControl.LocationNotAvailable": "Standort nicht verfügbar", "NavigationControl.ZoomIn": "Vergrößern", "NavigationControl.ZoomOut": "Verkleinern", "NavigationControl.ResetBearing": "Nach Norden ausrichten", "AttributionControl.ToggleAttribution": "Quellen ein- oder ausblenden" }
}, start));
map.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), "top-right");
map.addControl(new maplibregl.GeolocateControl({ positionOptions: { enableHighAccuracy: false, timeout: 10000 }, trackUserLocation: false, showAccuracyCircle: false, fitBoundsOptions: { maxZoom: 15 } }), "top-right");   // „Wo bin ich?“ (Audit K30): Position bleibt im Browser
map.addControl(new maplibregl.ScaleControl({ unit: "metric" }), "bottom-left");
window.KIEZ_KARTE = map;
var nummern = ST.features.map(function (f) { var e = el("div", "teilnr", f.properties.nr); e.setAttribute("aria-hidden", "true"); return new maplibregl.Marker({ element: e }).setLngLat([f.properties.lx, f.properties.ly]); });

function anwenden() {
  if (!bereit) return;
  var t = THEMA[S.thema], gitter = t.id !== "stadtteile";
  // Stadtteilfläche tritt zurück, solange Gebäude stehen (sonst viel Farbe unter den Häusern)
  map.setPaintProperty("teile-flaeche", "fill-opacity", gitter ? 0 : S.geb ? 0.2 : 0.72);
  nummern.forEach(function (m) { if (!gitter) m.addTo(map); else m.remove(); });
  // keine Zellsäulen mehr: Zellen liegen immer flach, 3D gilt den Gebäuden
  map.setLayoutProperty("zellen-3d", "visibility", "none");
  map.setLayoutProperty("zellen-2d", "visibility", gitter ? "visible" : "none");
  if (gitter) {
    map.setFilter("zellen-2d", ["!=", ["get", t.id], null]);
    map.setPaintProperty("zellen-2d", "fill-color", farbe(t)); map.setPaintProperty("zellen-2d", "fill-opacity", S.geb ? 0.55 : 0.85);
  }
  map.setLayoutProperty("dop", "visibility", S.luft ? "visible" : "none");
  T.grundLuft(map, S.luft);
  map.setLayoutProperty("gebaeude3d", "visibility", S.geb && S.d3 ? "visible" : "none");
  map.setLayoutProperty("gebaeude2d", "visibility", S.geb && !S.d3 ? "visible" : "none");
  if (S.geb) gebaeudeLaden();
  document.querySelectorAll('#thema input').forEach(function (r) { r.checked = r.value === S.thema; });
  document.getElementById("dreid").checked = S.d3; document.getElementById("luftbild").checked = S.luft; document.getElementById("gebaeude").checked = S.geb;
  legende(t); status(); hashSchreiben();
}
var gewaehlt = "";
function waehle(nr) {
  if (bereit && gewaehlt) map.setFeatureState({ source: "teile", id: gewaehlt }, { gewaehlt: false });
  gewaehlt = S.nr = nr || "";
  if (bereit && gewaehlt) map.setFeatureState({ source: "teile", id: gewaehlt }, { gewaehlt: true });
  steckbrief(); trefferMarkieren();
  document.getElementById("griff-name").textContent = S.nr ? S.nr + " " + name(S.nr) : "Ganz Potsdam";
  document.getElementById("zoom-teil").querySelector(".knopf__text").textContent = S.nr ? "Auf Stadtteil zoomen" : "Ganz Potsdam zeigen";
  if (S.geb) gebaeudeLaden(); else if (bereit) map.getSource("gebaeude").setData(LEER);
  anwenden();
}
var HINWEIS_TEIL = "Gebäude gibt es je Stadtteil: bitte zuerst einen Stadtteil wählen.";
function gebaeudeLaden() {
  if (!bereit) return;
  var nr = S.nr, hin = document.getElementById("teilen-hinweis");
  if (!nr) { map.getSource("gebaeude").setData(LEER); hin.textContent = HINWEIS_TEIL; return; }
  if (hin.textContent === HINWEIS_TEIL) hin.textContent = "";   // Stadtteil gewählt: Hinweis erledigt
  var v = "KIEZ_GEB_" + nr;
  if (window[v]) { map.getSource("gebaeude").setData(window[v]); return; }
  var s = document.createElement("script"); s.src = KIEZ_THEMEN.v("daten/gebaeude/" + nr + ".js");
  s.onload = function () { if (S.nr === nr && window[v]) map.getSource("gebaeude").setData(window[v]); };
  document.body.appendChild(s);
}
function status() {
  var t = THEMA[S.thema];
  document.getElementById("kartenstatus").textContent = "Karte zeigt: " + t.name + (S.nr ? ", ausgewählt " + S.nr + " " + name(S.nr) : ", ganz Potsdam") + (S.d3 ? ", 3D" : ", 2D") + (S.luft ? ", mit Luftbild" : "") + (S.geb ? ", mit Gebäuden" : "") + ".";
}
function legende(t) {
  var L = document.getElementById("legende"); L.innerHTML = "";
  L.appendChild(el("p", "legende__titel", t.name + (t.einheit ? " (" + t.einheit + ")" : "")));
  if (t.id === "stadtteile") {
    var bz = el("div", "bezirke");
    Object.keys(BEZIRKFARBE).forEach(function (b) { var s = el("span"), i = el("i"); i.style.background = BEZIRKFARBE[b]; s.appendChild(i); s.appendChild(document.createTextNode("Bezirk " + b)); bz.appendChild(s); });
    L.appendChild(bz); L.appendChild(el("p", "legende__q", "Ein Farbton je Stadtbezirk (erste Ziffer der Stadtteilnummer). Stadtteile © Landeshauptstadt Potsdam, dl-de/zero-2-0."));
    return;
  }
  var s = KLASSEN[t.id], st = el("div", "stufen"); st.setAttribute("aria-hidden", "true");
  STUFEN.slice(0, s.grenzen.length + 1).forEach(function (f) { var x = el("span"); x.style.background = f; x.style.height = "100%"; st.appendChild(x); });
  L.appendChild(st);
  var m = el("div", "marken"), r = function (v) { return t.einheit === "Personen" ? fmt.format(Math.round(v)) : fmt1.format(v); };
  m.appendChild(el("span", null, r(s.min))); s.grenzen.forEach(function (g) { m.appendChild(el("span", null, r(g))); }); m.appendChild(el("span", null, r(s.max))); L.appendChild(m);
  if (t.nenner) { var g = el("p", "legende__grau"); g.appendChild(el("i")); g.appendChild(document.createTextNode("Weniger als 10 " + (t.nenner === "a_ges" ? "Personen" : "Wohnungen") + ", Wert zu unscharf")); L.appendChild(g); }
  L.appendChild(el("p", "legende__q", (s.fest ? "Stufen zu 20 Prozentpunkten. " : "Stufen: Fünftel aller Zellen. ") + t.quelle + ", 15.05.2022."));
}

// ---------- Bedienung
var themaBox = document.getElementById("thema");
THEMEN.forEach(function (t) { var l = el("label", "chip"), r = document.createElement("input"); r.type = "radio"; r.name = "thema"; r.value = t.id; l.appendChild(r); l.appendChild(el("span", null, t.kurz)); l.title = t.name; themaBox.appendChild(l); });
themaBox.addEventListener("change", function (e) { S.thema = e.target.value; anwenden(); });
// Stadtteil an einem Punkt (Strahlverfahren, Löcher beachtet). Nicht über queryRenderedFeatures: bei den
// Zensus-Themen ist die Stadtteilfläche unsichtbar (Deckkraft 0) und wird dort nicht getroffen.
function inRing(r, x, y) { var c = false; for (var i = 0, j = r.length - 1; i < r.length; j = i++) { var a = r[i], b = r[j]; if ((a[1] > y) !== (b[1] > y) && x < (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1]) + a[0]) c = !c; } return c; }
function teilAn(x, y) {
  for (var i = 0; i < ST.features.length; i++) {
    var f = ST.features[i], u = umriss(f);
    if (x < u[0][0] || x > u[1][0] || y < u[0][1] || y > u[1][1]) continue;
    if (T.polys(f).some(function (p) { return inRing(p[0], x, y) && !p.slice(1).some(function (h) { return inRing(h, x, y); }); })) return f.properties.nr;
  }
  return "";
}
// „3D-Häuser“: ein Klick zeigt Gebäude als Körper. Ohne gewählten Stadtteil nimmt die Seite den unter der
// Kartenmitte (aus der Nähe), sonst die Innenstadt, und fliegt zu seinen Häusern. Nur auf Klick, nie beim Laden.
// Häuser stehen nur für den gewählten Stadtteil: nah heran wie auf der Bauzeiten-Seite (Zoom 16,2, Handy 15,6),
// in seine dichtesten Zellen oder, wenn die Kartenmitte schon in ihm liegt, dorthin; schon nah und mittendrin nur neigen
var HAUS_ZOOM = 16.2, HAUS_ZOOM_SCHMAL = 15.6;
// Ziel für die Häuser eines Stadtteils: Mitte seiner dichtesten Zellen (Summe von ew im Umkreis von rund 170 m), nicht
// sein Namenspunkt; der liegt bei manchen Stadtteilen über Feld, Park oder Wasser (Gegenprobe 07.11.: 32, 83 ohne ein Haus im Bild)
function dichteMitte(nr) {
  var m = [];
  Z.features.forEach(function (f) { var p = f.properties, v = +p.ew; if (p.st === nr && v > 0) { var c = f.geometry.coordinates[0]; m.push([(c[0][0] + c[2][0]) / 2, (c[0][1] + c[2][1]) / 2, v]); } });
  var best = null, max = 0;
  m.forEach(function (a) { var s = 0; m.forEach(function (b) { if (Math.abs(a[0] - b[0]) < 0.0025 && Math.abs(a[1] - b[1]) < 0.0016) s += b[2]; }); if (s > max) { max = s; best = a; } });
  return best ? [best[0], best[1]] : null;
}
function zuDenHaeusern() {
  if (!S.nr || !TEIL[S.nr]) return;
  var c = map.getCenter(), hier = map.getZoom() >= 13 ? teilAn(c.lng, c.lat) : "";
  if (map.getZoom() >= 14 && hier === S.nr) { if (S.d3 && map.getPitch() < 20) map.jumpTo({ pitch: 50 }); return; }
  var ziel = hier === S.nr ? [c.lng, c.lat] : dichteMitte(S.nr) || [TEIL[S.nr].properties.lx, TEIL[S.nr].properties.ly], o = { center: ziel,
    zoom: matchMedia("(max-width:860px)").matches ? HAUS_ZOOM_SCHMAL : HAUS_ZOOM, pitch: S.d3 ? 50 : map.getPitch(), bearing: map.getBearing() };
  if (RUHIG) map.jumpTo(o); else map.flyTo(Object.assign(o, { duration: 1400, easing: function (t) { return 1 - Math.pow(1 - t, 4); } }));
}
document.getElementById("dreid").addEventListener("change", function (e) {
  S.d3 = e.target.checked;
  if (!S.d3) { if (gebDurch3D) S.geb = false; gebDurch3D = false; anwenden(); if (map.getPitch() > 0) map.jumpTo({ pitch: 0 }); return; }
  gebDurch3D = !S.geb; S.geb = true;
  // Kartenmitte nur, wenn schon nah (ab Zoom 13, wie auf der Bauzeiten-Seite); im Überblick läge sie in Bornim
  if (!S.nr) { var c = map.getCenter(); waehle((map.getZoom() >= 13 && teilAn(c.lng, c.lat)) || HAUS_ERSATZ); } else anwenden();
  zuDenHaeusern();
});
document.getElementById("luftbild").addEventListener("change", function (e) { S.luft = e.target.checked; anwenden(); });
// ohne Gebäude keine 3D-Häuser: Gebäude aus schaltet auch 3D aus
document.getElementById("gebaeude").addEventListener("change", function (e) {
  S.geb = e.target.checked; gebDurch3D = false;
  if (!S.geb && S.d3) { S.d3 = false; if (map.getPitch() > 0) map.jumpTo({ pitch: 0 }); }
  anwenden();
});
document.getElementById("zoom-teil").addEventListener("click", function () {
  var opt = { padding: SCHMAL ? { top: 70, bottom: 30, left: 16, right: 16 } : 40, maxZoom: 15.5, pitch: map.getPitch(), bearing: map.getBearing() };
  var b = S.nr ? umriss(TEIL[S.nr]) : GANZ;
  if (RUHIG) map.fitBounds(b, Object.assign(opt, { animate: false })); else map.fitBounds(b, Object.assign(opt, { duration: 700 }));
  if (SCHMAL) seite(false);
});
document.getElementById("link-teilen").addEventListener("click", function () {
  hashSchreiben();
  var url = location.href, hin = document.getElementById("teilen-hinweis");
  function ok() { hin.textContent = "Link kopiert. Er öffnet genau diese Ansicht."; }
  function zeigen() { hin.textContent = "Link: " + url; }
  if (navigator.clipboard && window.isSecureContext) navigator.clipboard.writeText(url).then(ok, zeigen); else zeigen();
});

// Suche und Liste
var trefferBox = document.getElementById("treffer"), suche = document.getElementById("suche");
function trefferBauen() {
  var q = suche.value.trim().toLowerCase(); trefferBox.innerHTML = "";
  var alle = [{ nr: "", name: "Ganz Potsdam" }].concat(ST.features.map(function (f) { return { nr: f.properties.nr, name: f.properties.name }; }));
  alle.filter(function (x) { return !q || (x.nr + " " + x.name).toLowerCase().indexOf(q) > -1; }).forEach(function (x) {
    var li = el("li"), b = el("button", "treffer"); b.type = "button"; b.dataset.nr = x.nr;
    var i = el("i"); i.style.background = x.nr ? FARBE[x.nr] : "#13212a"; b.appendChild(i);
    b.appendChild(el("b", null, x.nr || "")); b.appendChild(el("span", null, x.name));
    if (x.nr) b.appendChild(el("span", "nur-sr", ", rund " + rundEw(kachel(K.stadtteile[x.nr], "einwohner").wert) + " Einwohner"));
    // Gebäude an: Wahl aus der Liste fliegt zu den Häusern (sie stehen nur für den gewählten Stadtteil)
    b.addEventListener("click", function () { waehle(x.nr); if (x.nr && S.geb && bereit) { zuDenHaeusern(); if (SCHMAL) seite(false); } });
    li.appendChild(b); trefferBox.appendChild(li);
  });
  trefferMarkieren();
}
function trefferMarkieren() { trefferBox.querySelectorAll(".treffer").forEach(function (b) { b.setAttribute("aria-pressed", String(b.dataset.nr === S.nr)); }); }
suche.addEventListener("input", trefferBauen);
suche.addEventListener("keydown", function (e) { if (e.key === "Enter") { var f = trefferBox.querySelector(".treffer"); if (f) { e.preventDefault(); f.click(); } } });

// Steckbrief
var TITEL = { alter: "Alter", baujahr: "Baujahr des Gebäudes", heizung: "Überwiegende Heizungsart", energie: "Energieträger der Heizung" };
function steckbrief() {
  var nr = S.nr, G = nr ? K.stadtteile[nr] : K.stadt;
  document.getElementById("sb-name").textContent = nr ? G.name : "Potsdam";
  document.getElementById("sb-art").textContent = (nr ? "Stadtteil " + nr + " der Landeshauptstadt Potsdam" : "Landeshauptstadt, " + ST.features.length + " Stadtteile") + ", " + fmt1.format(G.flaeche_km2) + " km²";
  var box = document.getElementById("kacheln"); box.innerHTML = "";
  G.kacheln.forEach(function (k) {
    var d = el("div", "kachel"), z = el("div", "zahl");
    if (k.anzeige === "summe") { d.appendChild(el("div", "vorsatz", "rund")); z.textContent = rundEw(k.wert); }
    else if (k.wert == null) z.textContent = "k. A.";
    else { z.textContent = fmt1.format(k.wert); z.appendChild(el("small", null, "%")); }
    d.appendChild(z); d.appendChild(el("div", "titel-k", k.titel));
    var m = k.quelle.match(/\(([^)]+)\)\s*$/), q = el("div", "quelle", "Zensus 2022, " + (m ? m[1] : "")); q.title = k.quelle; d.appendChild(q); box.appendChild(d);
  });
  document.getElementById("sb-fuss").textContent = "Grundlage: " + fmt.format(G.zellen) + " Gitterzellen zu 100 × 100 m, deren Mittelpunkt im Gebiet liegt; " +
    (G.gebaeude && G.gebaeude.anzahl ? fmt.format(G.gebaeude.anzahl) + " Gebäude laut ALKIS, davon " + fmt.format(G.gebaeude.wohngebaeude) + " Wohngebäude" : "keine Gebäude zugeordnet") + ". Stichtag des Zensus: 15. Mai 2022.";
  var gp = (K.gegenprobe || {})[nr || "stadt"], gpEl = document.getElementById("gegenprobe"); gpEl.innerHTML = "";
  if (gp) { gpEl.appendChild(document.createTextNode("Gegenprobe: " + gp.art + " am " + gp.stichtag + ": " + fmt.format(gp.einwohner) + " (")); var a = el("a", "link", gp.quelle); a.href = gp.url; gpEl.appendChild(a); gpEl.appendChild(document.createTextNode(").")); }
  var vb = document.getElementById("verteilungen"); vb.innerHTML = "";
  ["alter", "baujahr", "heizung", "energie"].forEach(function (key) {
    var v = G.verteilungen[key], max = Math.max.apply(null, v.werte.map(function (w) { return w[1]; })) || 1, d = el("div", "vert");
    d.appendChild(el("h3", null, TITEL[key])); d.appendChild(el("p", "einheit", v.einheit + " insgesamt " + fmt.format(v.insgesamt) + ". Anteile am Insgesamt."));
    var ul = el("ul", "balken");
    v.werte.forEach(function (w) {
      if ((key === "energie" || key === "heizung") && w[1] === 0) return;
      var li = el("li"), l = el("span", "l"); l.appendChild(el("span", null, w[0])); l.appendChild(el("span", null, v.insgesamt ? fmt1.format(100 * w[1] / v.insgesamt) + NB + "%" : "k. A."));
      var b = el("span", "b"), i = el("i"); i.style.width = (100 * w[1] / max).toFixed(1) + "%"; b.appendChild(i); b.setAttribute("aria-hidden", "true");
      li.appendChild(l); li.appendChild(b); ul.appendChild(li);
    });
    d.appendChild(ul); d.appendChild(el("p", "quelle", v.quelle)); vb.appendChild(d);
  });
}

// Blatt auf dem Handy
var seiteEl = document.getElementById("seite"), griff = document.getElementById("seite-griff");
function seite(an) { seiteEl.classList.toggle("offen", an); griff.setAttribute("aria-expanded", String(an)); }
griff.addEventListener("click", function () { seite(!seiteEl.classList.contains("offen")); });
addEventListener("keydown", function (e) { if (e.key === "Escape" && seiteEl.classList.contains("offen") && SCHMAL) { seite(false); griff.focus(); } });

// ---------- Klicks in der Karte (keine Kamerabewegung)
function zeile(t, a) { return "<tr><td>" + t + "</td><td>" + a + "</td></tr>"; }
map.on("click", function (e) {
  // zweiter Klick eines Doppelklicks (der zoomt): nichts wählen, sonst wählte er den eben gewählten Stadtteil wieder ab
  if (e.originalEvent && e.originalEvent.detail > 1) return;
  var lay = ["gebaeude3d", "gebaeude2d"].filter(function (l) { return map.getLayoutProperty(l, "visibility") !== "none"; });
  var g = lay.length ? map.queryRenderedFeatures(e.point, { layers: lay }) : [];
  if (g.length) {
    var gp = g[0].properties;
    new maplibregl.Popup({ maxWidth: "270px" }).setLngLat(e.lngLat).setHTML("<b>" + esc(gp.f || "Gebäude") + "</b><table class='pop-tab'>" + zeile("Geschosse", gp.gs == null || gp.gs === "null" ? "k. A." : esc(gp.gs)) +
      zeile("Höhe", fmt1.format(gp.h) + " m") + "</table><div class='pop-q'>Höhe: " + (T.HQ[gp.hq] || "Herkunft unbekannt") + ". Umriss ALKIS vereinfacht. © GeoBasis-DE/LGB, dl-de/by-2-0</div>").addTo(map);
    return;
  }
  var zl = ["zellen-3d", "zellen-2d"].filter(function (l) { return map.getLayoutProperty(l, "visibility") !== "none"; });
  var c = zl.length ? map.queryRenderedFeatures(e.point, { layers: zl }) : [];
  if (c.length) {
    var p = c[0].properties, n = function (k) { var v = p[k]; return (v === undefined || v === "null" || v === null) ? null : Number(v); }, zz = function (v) { return v == null ? "k. A." : fmt.format(v); };
    new maplibregl.Popup({ maxWidth: "290px" }).setLngLat(e.lngLat).setHTML("<b>Gitterzelle 100 × 100 m</b><br>" + esc(p.st + " " + name(p.st)) + "<table class='pop-tab'>" +
      zeile("Einwohner", zz(n("ew"))) + zeile("Durchschnittsalter", n("d_alter") == null ? "k. A." : fmt1.format(n("d_alter"))) + zeile("unter 18", proz(n("q_u18"))) + zeile("65 und älter", proz(n("q_65p"))) +
      zeile("Wohnungen", zz(n("w_ges"))) + zeile("davon vor 1949", proz(n("q_v1949"))) + zeile("mit Fernwärme", proz(n("q_fern"))) + "</table>" +
      "<div class='pop-q'>Zensus 2022, 15.05.2022, © Statistische Ämter des Bundes und der Länder, dl-de/by-2-0. Kleine Werte sind durch die Geheimhaltung unscharf, Anteile können darum über 100 % liegen.</div>").addTo(map);
  }
  var t = map.queryRenderedFeatures(e.point, { layers: ["teile-flaeche"] });
  // Gebäude an: ein Klick wählt den gewählten Stadtteil nicht ab (ohne Stadtteil stünden keine Gebäude mehr)
  if (t.length && !c.length) { if (t[0].properties.nr !== S.nr) waehle(t[0].properties.nr); else if (!S.geb) waehle(""); }
  else if (t.length && c.length && t[0].properties.nr !== S.nr) waehle(t[0].properties.nr);
});
var schild = document.getElementById("schild");
map.on("mousemove", function (e) {
  var t = map.queryRenderedFeatures(e.point, { layers: ["teile-flaeche"] });
  map.getCanvas().style.cursor = t.length ? "pointer" : "";
  if (t.length && FEIN) { var nr = t[0].properties.nr; schild.textContent = nr + " " + name(nr) + ": rund " + rundEw(kachel(K.stadtteile[nr], "einwohner").wert) + " Einwohner"; schild.style.left = e.point.x + "px"; schild.style.top = e.point.y + "px"; schild.style.display = "block"; }
  else schild.style.display = "none";
});
map.on("mouseout", function () { schild.style.display = "none"; });
map.on("moveend", hashSchreiben);
map.on("load", function () {
  bereit = true;
  map.addControl(new maplibregl.AttributionControl({ compact: true }), "bottom-right");
  var att = document.querySelector(".maplibregl-ctrl-attrib"); if (att) att.classList.remove("maplibregl-compact-show");
  map.setLight({ anchor: "viewport", position: [1.4, 200, 35], intensity: 0.38, color: "#ffffff" });
  if (S.d3 && !S.kam && map.getPitch() < 20) map.jumpTo({ pitch: 50 });
  waehle(S.nr);
  window.KIEZ_BEREIT = false; map.once("idle", function () { window.KIEZ_BEREIT = true; });
});
trefferBauen(); steckbrief();
})();
