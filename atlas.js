/* Kiezatlas Potsdam: Karte, Fragen, Register, Grenzfall.
   Alle Zahlen kommen aus daten/*.js; hier steht keine Ergebniszahl von Hand. */
(function () {
"use strict";
var K = window.KIEZ_KENNZAHLEN, ST = window.KIEZ_STADTTEILE, Z = window.KIEZ_ZELLEN;
var A = window.KIEZ = {};                       // Seitenzustand für schaugrafik.js
var T = window.KIEZ_THEMEN;                     // gemeinsamer Themenkern (themen.js)
var fmt = T.fmt, fmt1 = T.fmt1;
var NB = " ";
var RUHIG = matchMedia("(prefers-reduced-motion: reduce)").matches;
var SCHMAL = matchMedia("(max-width:860px)").matches;
var FEIN = matchMedia("(hover:hover) and (pointer:fine)").matches;
var SCHWELLE = 1000;                            // Mindestgröße für Vergleiche von Anteilen (Methode, keine Ergebniszahl)

function el(tag, cls, text) { var e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; }
function setze(feld, wert) { document.querySelectorAll('[data-feld="' + feld + '"]').forEach(function (n) { n.textContent = wert; }); }
function q(feld, wert) { document.querySelectorAll('[data-q="' + feld + '"]').forEach(function (n) { n.textContent = wert; }); }
var rundEw = T.rundEw, proz = T.proz, kachel = T.kachel, name = T.name, esc = T.esc;

// ---------- Farben: ein Farbton je Stadtbezirk, heller und dunkler je Stadtteil (themen.js)
var proBezirk = T.proBezirk, FARBE = T.FARBE, BEZIRKFARBE = T.BEZIRKFARBE, TEIL = T.TEIL;

// ---------- Kopf: Stadtzahlen
var stand = new Date(K.stand_auswertung).toLocaleDateString("de-DE");
setze("stand", stand);
setze("import", K.stand_import ? new Date(K.stand_import).toLocaleString("de-DE", { dateStyle: "medium", timeStyle: "short" }) : "k. A.");
setze("anzahl-teile", String(ST.features.length));
setze("nr-erste", ST.features[0].properties.nr);
setze("nr-letzte", ST.features[ST.features.length - 1].properties.nr);
setze("flaeche-stadt", fmt1.format(K.stadt.flaeche_km2));
setze("zellen-stadt", fmt.format(K.stadt.zellen));
(function () {
  var box = document.getElementById("stadtzahlen"); if (box.children.length) return;
  K.stadt.kacheln.forEach(function (k) {
    var d = el("div"), dd = el("dd"), dt = el("dt", null, k.titel);
    if (k.anzeige === "summe") { dd.textContent = "rund " + rundEw(k.wert); dt.textContent = k.titel; }
    else { dd.textContent = fmt1.format(k.wert); dd.appendChild(el("small", null, "%")); }
    dd.title = k.quelle;
    d.appendChild(dt); d.appendChild(dd); box.appendChild(d);
  });
})();

// ---------- Themen der Karte (Themen, Klassen, Farben, Höhen aus themen.js)
var STUFEN = T.STUFEN, THEMEN = T.THEMEN, THEMA = T.THEMA, KLASSEN = T.KLASSEN;
function werte(feld) { return Z.features.map(function (f) { return f.properties[feld]; }).filter(function (v) { return v != null && !isNaN(v); }).sort(function (a, b) { return a - b; }); }
var hk = { k: 0 };                                 // Höhenfaktor, wird animiert
function grund(t) { return T.hoehe(t, { faktor: hk.k }); }
var farbe = T.farbe;

// ---------- Kennzahlen für die Fragen (alles live)
(function () {
  var feats = Z.features.slice().sort(function (a, b) { return b.properties.ew - a.properties.ew; });
  var top = feats[0].properties, ew = werte("ew");
  q("ew-max-teil", name(top.st)); q("ew-max", fmt.format(top.ew)); q("ew-median", fmt.format(ew[Math.floor(ew.length / 2)]));
  q("schwelle", fmt.format(SCHWELLE));
  var gross = Object.keys(K.stadtteile).filter(function (nr) { return kachel(K.stadtteile[nr], "einwohner").wert >= SCHWELLE; });
  function extrem(id, max) {
    return gross.slice().sort(function (a, b) { var x = kachel(K.stadtteile[a], id).wert, y = kachel(K.stadtteile[b], id).wert; return max ? y - x : x - y; })[0];
  }
  A.FRAGE = {};
  var ah = extrem("65p", true), at = extrem("65p", false);
  q("alt-hoch", name(ah)); q("alt-hoch-wert", proz(kachel(K.stadtteile[ah], "65p").wert));
  q("alt-tief", name(at)); q("alt-tief-wert", proz(kachel(K.stadtteile[at], "65p").wert));
  q("alt-stadt", proz(kachel(K.stadt, "65p").wert));
  A.FRAGE.alt = ah;
  var alle = Object.keys(K.stadtteile);
  var kz = alle.slice().sort(function (a, b) { return (kachel(K.stadtteile[b], "u18").zaehler || 0) - (kachel(K.stadtteile[a], "u18").zaehler || 0); })[0];
  var kk = kachel(K.stadtteile[kz], "u18");
  q("kind-teil", name(kz)); q("kind-zahl", fmt.format(kk.zaehler)); q("kind-nenner", fmt.format(kk.nenner)); q("kind-anteil", proz(kk.wert));
  var ka = extrem("u18", true);
  q("kind-anteilig", ka === kz ? "Es hat auch anteilig die meisten, unter den Stadtteilen mit mindestens " + fmt.format(SCHWELLE) + " Einwohnern."
    : "Anteilig liegt der Stadtteil " + name(ka) + " vorn, mit " + proz(kachel(K.stadtteile[ka], "u18").wert) + ", unter den Stadtteilen mit mindestens " + fmt.format(SCHWELLE) + " Einwohnern.");
  A.FRAGE.kind = kz;
  var ab = extrem("altbau", true);
  q("altbau-teil", name(ab)); q("altbau-wert", proz(kachel(K.stadtteile[ab], "altbau").wert)); q("altbau-stadt", proz(kachel(K.stadt, "altbau").wert));
  A.FRAGE.altbau = ab;
  var fh = extrem("fernwaerme", true), ft = extrem("fernwaerme", false);
  q("fern-stadt", proz(kachel(K.stadt, "fernwaerme").wert));
  q("fern-hoch", name(fh)); q("fern-hoch-wert", proz(kachel(K.stadtteile[fh], "fernwaerme").wert));
  q("fern-tief", name(ft)); q("fern-tief-wert", proz(kachel(K.stadtteile[ft], "fernwaerme").wert));
  A.FRAGE.fern = fh;
})();

// ---------- Geometrie-Helfer
function inRing(x, y, r) { var c = false; for (var i = 0, j = r.length - 1; i < r.length; j = i++) { var xi = r[i][0], yi = r[i][1], xj = r[j][0], yj = r[j][1]; if (((yi > y) !== (yj > y)) && (x < (xj - xi) * (y - yi) / (yj - yi) + xi)) c = !c; } return c; }
var polys = T.polys, umriss = T.umriss, GANZ = T.GANZ;
function inTeil(x, y, f) { return polys(f).some(function (p) { if (!inRing(x, y, p[0])) return false; for (var h = 1; h < p.length; h++) if (inRing(x, y, p[h])) return false; return true; }); }
function welcherTeil(x, y) { for (var i = 0; i < ST.features.length; i++) if (inTeil(x, y, ST.features[i])) return ST.features[i].properties.nr; return null; }

// ---------- Grenzfall: eine echte Beispielzelle aus den Daten finden
var GZ = (function () {
  var best = null;
  Z.features.forEach(function (f) {
    var p = f.properties; if (!p.ew || (best && p.ew <= best.p.ew)) return;
    var own = TEIL[p.st], ring = f.geometry.coordinates[0];
    for (var i = 0; i < 4; i++) {
      if (!inTeil(ring[i][0], ring[i][1], own)) { var nb = welcherTeil(ring[i][0], ring[i][1]); if (nb && nb !== p.st) { best = { f: f, p: p, nach: nb }; } break; }
    }
  });
  if (!best) return null;
  var r = best.f.geometry.coordinates[0], N = 24, zahl = {}, mitte = {};
  for (var a = 0; a < N; a++) for (var b = 0; b < N; b++) {
    var u = (a + 0.5) / N, v = (b + 0.5) / N;
    var x = (1 - u) * (1 - v) * r[0][0] + u * (1 - v) * r[1][0] + u * v * r[2][0] + (1 - u) * v * r[3][0];
    var y = (1 - u) * (1 - v) * r[0][1] + u * (1 - v) * r[1][1] + u * v * r[2][1] + (1 - u) * v * r[3][1];
    var t = welcherTeil(x, y) || "aussen"; zahl[t] = (zahl[t] || 0) + 1;
    mitte[t] = mitte[t] || [0, 0]; mitte[t][0] += x; mitte[t][1] += y;
  }
  Object.keys(mitte).forEach(function (k) { mitte[k][0] /= zahl[k]; mitte[k][1] /= zahl[k]; });
  var cx = (r[0][0] + r[1][0] + r[2][0] + r[3][0]) / 4, cy = (r[0][1] + r[1][1] + r[2][1] + r[3][1]) / 4;
  best.anteil = {}; Object.keys(zahl).forEach(function (k) { best.anteil[k] = zahl[k] / (N * N); });
  best.mitte = mitte; best.c = [cx, cy]; best.stichproben = N * N;
  return best;
})();
A.GZ = GZ;
if (GZ) {
  q("gz-ew", fmt.format(GZ.p.ew)); q("gz-a", name(GZ.p.st)); q("gz-b", name(GZ.nach)); q("gz-eigner", name(GZ.p.st));
}

// =====================================================================
// Karte
// =====================================================================
var LEER = { type: "FeatureCollection", features: [] };
var GRENZ_DATEN = GZ ? { type: "FeatureCollection", features: [
  { type: "Feature", geometry: GZ.f.geometry, properties: { art: "zelle" } },
  { type: "Feature", geometry: { type: "Point", coordinates: GZ.c }, properties: { art: "mitte" } }] } : LEER;
var Q_ZENSUS = 'Zensus 2022 © Statistische Ämter des Bundes und der Länder, <a href="https://www.govdata.de/dl-de/by-2-0">dl-de/by-2-0</a>, eigene Auswertung';
var map = new maplibregl.Map({
  container: "karte",
  style: {
    version: 8,
    sources: {
      basemap: { type: "raster", tileSize: 256, maxzoom: 18,
        tiles: ["https://sgx.geodatenzentrum.de/wmts_basemapde/tile/1.0.0/de_basemapde_web_raster_grau/default/GLOBAL_WEBMERCATOR/{z}/{y}/{x}.png"],
        attribution: 'Hintergrund © <a href="https://basemap.de">basemap.de / BKG</a>, <a href="https://www.govdata.de/dl-de/by-2-0">dl-de/by-2-0</a>' },
      dop: { type: "raster", tileSize: 256, maxzoom: 20,
        tiles: ["https://isk.geobasis-bb.de/mapproxy/dop20c/service/wms?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&LAYERS=bebb_dop20c&STYLES=&CRS=EPSG:3857&BBOX={bbox-epsg-3857}&WIDTH=256&HEIGHT=256&FORMAT=image/jpeg"],
        attribution: 'Luftbild © GeoBasis-DE/LGB, <a href="https://www.govdata.de/dl-de/by-2-0">dl-de/by-2-0</a>' },
      zellen: { type: "geojson", data: Z, attribution: Q_ZENSUS },
      teile: { type: "geojson", data: ST, promoteId: "nr", attribution: "Stadtteile © Landeshauptstadt Potsdam, dl-zero-de/2.0" },
      gebaeude: { type: "geojson", data: LEER, attribution: 'Gebäude © GeoBasis-DE/LGB, <a href="https://www.govdata.de/dl-de/by-2-0">dl-de/by-2-0</a> (Daten geändert)' },
      grenze: { type: "geojson", data: GRENZ_DATEN }
    },
    layers: [
      { id: "papier", type: "background", paint: { "background-color": "#e6e9e4" } },
      { id: "basemap", type: "raster", source: "basemap", paint: { "raster-opacity": 0.6, "raster-saturation": -1, "raster-opacity-transition": { duration: 600 } } },
      { id: "dop", type: "raster", source: "dop", layout: { visibility: "none" } },
      { id: "teile-flaeche", type: "fill", source: "teile", paint: { "fill-color": ["get", "farbe"], "fill-opacity": 0.72, "fill-opacity-transition": { duration: 700 } } },
      { id: "zellen-flach", type: "fill", source: "zellen", layout: { visibility: "none" }, paint: { "fill-color": "rgba(255,255,255,0.35)", "fill-outline-color": "rgba(19,33,42,0.55)" } },
      { id: "zellen-3d", type: "fill-extrusion", source: "zellen", layout: { visibility: "none" },
        paint: { "fill-extrusion-color": STUFEN[2], "fill-extrusion-height": 0, "fill-extrusion-opacity": 0.94, "fill-extrusion-vertical-gradient": true } },
      { id: "gebaeude2d", type: "fill", source: "gebaeude", minzoom: 14, paint: { "fill-color": "#24363b", "fill-opacity": 0.4 } },
      { id: "gebaeude3d", type: "fill-extrusion", source: "gebaeude", layout: { visibility: "none" },
        paint: { "fill-extrusion-color": "#aebfbf", "fill-extrusion-height": ["get", "h"], "fill-extrusion-opacity": 0.95, "fill-extrusion-vertical-gradient": true } },
      { id: "teile-linie", type: "line", source: "teile", paint: { "line-color": "#ffffff", "line-width": 1.2, "line-opacity": 0.9 } },
      { id: "teile-grenze", type: "line", source: "teile", layout: { visibility: "none" }, paint: { "line-color": "#6a2c82", "line-width": 3 } },
      { id: "teile-wahl", type: "line", source: "teile", paint: { "line-color": "#6a2c82", "line-width": ["case", ["boolean", ["feature-state", "gewaehlt"], false], 3.2, 0] } },
      { id: "grenz-zelle", type: "line", source: "grenze", filter: ["==", ["get", "art"], "zelle"], layout: { visibility: "none" }, paint: { "line-color": "#13212a", "line-width": 3, "line-dasharray": [2, 1] } },
      { id: "grenz-mitte", type: "circle", source: "grenze", filter: ["==", ["get", "art"], "mitte"], layout: { visibility: "none" }, paint: { "circle-radius": 7, "circle-color": "#13212a", "circle-stroke-color": "#fff", "circle-stroke-width": 2 } }
    ]
  },
  bounds: GANZ, fitBoundsOptions: { padding: SCHMAL ? 16 : 40 },
  maxZoom: 19, maxPitch: 70, attributionControl: false, cooperativeGestures: !FEIN, scrollZoom: !FEIN, fadeDuration: RUHIG ? 0 : 300,
  locale: { "NavigationControl.ZoomIn": "Vergrößern", "NavigationControl.ZoomOut": "Verkleinern",
    "NavigationControl.ResetBearing": "Nach Norden ausrichten", "AttributionControl.ToggleAttribution": "Quellen ein- oder ausblenden",
    "CooperativeGesturesHandler.MobileHelpText": "Mit zwei Fingern die Karte bewegen",
    "CooperativeGesturesHandler.WindowsHelpText": "Strg + Mausrad zum Zoomen", "CooperativeGesturesHandler.MacHelpText": "⌘ + Mausrad zum Zoomen" }
});
map.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), "top-right");
map.addControl(new maplibregl.ScaleControl({ unit: "metric" }), "bottom-left");
map.addControl(new maplibregl.AttributionControl({ compact: true }), "bottom-right");
window.KIEZ_KARTE = map;

// Stadtteilnummern als leise Beschriftung (HTML, keine Glyphen-Server nötig)
var nummern = ST.features.map(function (f) {
  var e = el("div", "teilnr", f.properties.nr); e.setAttribute("aria-hidden", "true");
  return new maplibregl.Marker({ element: e }).setLngLat([f.properties.lx, f.properties.ly]);
});
function zeigeNummern(an) { nummern.forEach(function (m) { if (an) m.addTo(map); else m.remove(); }); }

// ---------- Zustand: eine Funktion für Fragen und freie Bedienung
var S = { nr: "", thema: "stadtteile", luftbild: false, geb3d: false, grenze: false };
var bereit = false, wartend = null;
function geladen() { return bereit; }

function setzeHoehe() { var t = THEMA[S.thema]; if (t && t.id !== "stadtteile") map.setPaintProperty("zellen-3d", "fill-extrusion-height", grund(t)); }
var hoeheTween = null;
function hoeheAuf(ziel, dauer) {
  if (hoeheTween) hoeheTween.kill();
  if (RUHIG || SCHMAL || !window.gsap) { hk.k = ziel; setzeHoehe(); return; }   // Handy: ohne Höhen-Tween, spart Rechenlast
  hoeheTween = gsap.to(hk, { k: ziel, duration: dauer, ease: "expo.out", onUpdate: setzeHoehe });
}

function themaAnwenden(id, alt) {
  var t = THEMA[id], gitter = id !== "stadtteile";
  map.setPaintProperty("teile-flaeche", "fill-opacity", gitter || S.grenze ? 0 : 0.72);
  zeigeNummern(!gitter && !S.grenze);
  var dreiZellen = gitter && !S.geb3d && !S.grenze;
  map.setLayoutProperty("zellen-3d", "visibility", dreiZellen ? "visible" : "none");
  map.setLayoutProperty("zellen-flach", "visibility", S.grenze ? "visible" : "none");
  if (gitter) {
    map.setFilter("zellen-3d", ["!=", ["get", id], null]);
    map.setPaintProperty("zellen-3d", "fill-extrusion-color", farbe(t));
    if (id !== alt || hk.k < 0.99) { hk.k = 0; setzeHoehe(); hoeheAuf(1, 1.1); }
  }
  legende(t);
  document.querySelectorAll('#thema input').forEach(function (r) { r.checked = r.value === id; });
}

function kamera(art, opt) {
  opt = opt || {};
  var pad = SCHMAL ? { top: 70, bottom: 70, left: 16, right: 16 } : { top: 90, bottom: 60, left: 40, right: 60 };
  var pitch = opt.pitch != null ? opt.pitch : 0, bearing = opt.bearing || 0, ziel;
  if (art === "stadt") { ziel = map.cameraForBounds(GANZ, { padding: pad, bearing: bearing }); if (pitch > 20) ziel.zoom += SCHMAL ? 0.35 : 0.55; }
  else if (art === "teil" && S.nr) { ziel = map.cameraForBounds(umriss(TEIL[S.nr]), { padding: pad, maxZoom: opt.maxZoom || 15, bearing: bearing }); }
  else if (art === "zelle" && GZ) ziel = { center: GZ.c, zoom: SCHMAL ? 15.6 : 16.4 };
  if (!ziel) return;
  if (opt.zoomPlus) ziel.zoom += opt.zoomPlus;
  var cam = { center: ziel.center, zoom: ziel.zoom, pitch: pitch, bearing: bearing };
  if (RUHIG) map.jumpTo(cam); else map.easeTo(Object.assign(cam, { duration: opt.dauer || 1500, easing: function (x) { return 1 - Math.pow(1 - x, 4); } }));
}

var gewaehlt = "";
function waehle(nr) {
  nr = nr || "";
  if (gewaehlt && bereit) map.setFeatureState({ source: "teile", id: gewaehlt }, { gewaehlt: false });
  gewaehlt = S.nr = nr;
  if (gewaehlt && bereit) map.setFeatureState({ source: "teile", id: gewaehlt }, { gewaehlt: true });
  zeigeZahlen(nr);
  if (S.geb3d || (bereit && map.getZoom() >= 14)) gebaeudeLaden(nr);
  legende(THEMA[S.thema]);
}
A.waehle = function (nr) { waehle(nr); };

function gebaeudeLaden(nr) {
  if (!bereit) return;
  if (!nr) { map.getSource("gebaeude").setData(LEER); return; }
  var v = "KIEZ_GEB_" + nr;
  if (window[v]) { map.getSource("gebaeude").setData(window[v]); return; }
  var s = document.createElement("script"); s.src = KIEZ_THEMEN.v("daten/gebaeude/" + nr + ".js");
  s.onload = function () { if (gewaehlt === nr && window[v]) map.getSource("gebaeude").setData(window[v]); status(); };
  document.body.appendChild(s);
}

function setzeLuftbild(an) {
  S.luftbild = an; document.getElementById("luftbild").checked = an;
  map.setLayoutProperty("dop", "visibility", an ? "visible" : "none");
  map.setLayoutProperty("basemap", "visibility", an ? "none" : "visible");
}
function setzeGebaeude3d(an) {
  S.geb3d = an; document.getElementById("dreid").checked = an;
  map.setLayoutProperty("gebaeude3d", "visibility", an ? "visible" : "none");
  map.setLayoutProperty("gebaeude2d", "visibility", an ? "none" : "visible");
  if (an) gebaeudeLaden(S.nr);
  themaAnwenden(S.thema, S.thema);
}
function setzeGrenze(an) {
  S.grenze = an;
  ["teile-grenze", "grenz-zelle", "grenz-mitte"].forEach(function (l) { map.setLayoutProperty(l, "visibility", an ? "visible" : "none"); });
}

// zustand({nr, thema, luftbild, geb3d, grenze, kamera, pitch, bearing})
function zustand(z) {
  if (!bereit) { wartend = z; return; }
  var alt = S.thema;
  if ("grenze" in z) setzeGrenze(!!z.grenze);
  if ("luftbild" in z) setzeLuftbild(!!z.luftbild);
  if ("nr" in z) waehle(z.nr);
  if ("geb3d" in z && z.geb3d !== S.geb3d) { S.thema = z.thema || S.thema; setzeGebaeude3d(!!z.geb3d); }
  if (z.thema) { S.thema = z.thema; themaAnwenden(z.thema, alt); }
  if (z.kamera) kamera(z.kamera, z);
  status();
}
A.zustand = zustand;

function status() {
  var t = THEMA[S.thema], s = "Karte zeigt: " + t.name + (S.nr ? ", ausgewählt " + S.nr + " " + name(S.nr) : ", ganz Potsdam") +
    (S.geb3d ? ", Gebäude in 3D" : "") + (S.luftbild ? ", mit Luftbild" : "") + (S.grenze ? ", Beispielzelle auf der Grenze" : "") + ".";
  document.getElementById("kartenstatus").textContent = s;
}

// ---------- Legende
function legende(t) {
  var L = document.getElementById("legende"); L.innerHTML = "";
  L.appendChild(el("p", "legende__titel", S.grenze ? "Zelle auf der Grenze" : t.name + (t.einheit ? " (" + t.einheit + ")" : "")));
  var aus = el("p", "legende__auswahl");
  if (S.nr) { aus.appendChild(document.createTextNode("Ausgewählt: ")); aus.appendChild(el("b", null, S.nr + " " + name(S.nr))); }
  else aus.textContent = "Ganz Potsdam";
  L.appendChild(aus);
  if (S.grenze) {
    L.appendChild(el("p", "legende__q", "Gestrichelt: die Beispielzelle, 100 × 100 m. Punkt: ihr Mittelpunkt. Violett: Stadtteilgrenze."));
    return;
  }
  if (t.id === "stadtteile") {
    var bz = el("div", "bezirke");
    Object.keys(BEZIRKFARBE).forEach(function (b) { var s = el("span"), i = el("i"); i.style.background = BEZIRKFARBE[b]; s.appendChild(i); s.appendChild(document.createTextNode("Bezirk " + b)); bz.appendChild(s); });
    L.appendChild(bz);
    L.appendChild(el("p", "legende__q", "Ein Farbton je Stadtbezirk (erste Ziffer der Stadtteilnummer). Stadtteile © Landeshauptstadt Potsdam, dl-zero-de/2.0."));
    return;
  }
  var s = KLASSEN[t.id], st = el("div", "stufen");
  st.setAttribute("aria-hidden", "true");
  STUFEN.slice(0, s.grenzen.length + 1).forEach(function (f, i, arr) { var x = el("span"); x.style.background = f; x.style.height = (30 + 70 * (i + 1) / arr.length) + "%"; st.appendChild(x); });
  L.appendChild(st);
  var m = el("div", "marken"), r = function (v) { return t.einheit === "Personen" ? fmt.format(Math.round(v)) : fmt1.format(v); };
  m.appendChild(el("span", null, r(s.min))); s.grenzen.forEach(function (g) { m.appendChild(el("span", null, r(g))); }); m.appendChild(el("span", null, r(s.max)));
  L.appendChild(m);
  if (t.nenner) { var g = el("p", "legende__grau"); g.appendChild(el("i")); g.appendChild(document.createTextNode("Weniger als 10 " + (t.nenner === "a_ges" ? "Personen" : "Wohnungen"))); L.appendChild(g); }
  L.appendChild(el("p", "legende__q", "Farbe und Höhe zeigen denselben Wert. " + (s.fest ? "Stufen zu 20 Prozentpunkten. " : "Stufen: Fünftel aller Zellen. ") + t.quelle + ", 15.05.2022."));
}

// ---------- Werkzeugleiste
var themaBox = document.getElementById("thema");
THEMEN.forEach(function (t) {
  var l = el("label", "chip"), r = document.createElement("input");
  r.type = "radio"; r.name = "thema"; r.value = t.id; r.checked = t.id === "stadtteile";
  l.appendChild(r); l.appendChild(el("span", null, t.kurz)); l.title = t.name; themaBox.appendChild(l);
});
themaBox.addEventListener("change", function (e) {
  var id = e.target.value, z = { thema: id, grenze: false };
  if (id !== "stadtteile" && map.getPitch() < 20 && !S.geb3d) { z.kamera = S.nr ? "teil" : "stadt"; z.pitch = 50; z.bearing = -14; }
  zustand(z);
});
document.getElementById("luftbild").addEventListener("change", function (e) { zustand({ luftbild: e.target.checked }); });
document.getElementById("dreid").addEventListener("change", function (e) {
  var an = e.target.checked, z = { geb3d: an, grenze: false };
  if (an && !S.nr) z.nr = A.FRAGE.altbau;
  if (an) { z.kamera = "teil"; z.pitch = 58; z.bearing = -20; z.zoomPlus = 0.6; z.maxZoom = 16; }
  zustand(z);
});

// ---------- Klicks in der Karte
function zeile(t, a) { return "<tr><td>" + t + "</td><td>" + a + "</td></tr>"; }
function zz(v) { return v == null ? "k. A." : fmt.format(v); }
map.on("click", function (e) {
  var lay = ["gebaeude3d", "gebaeude2d"].filter(function (l) { return map.getLayoutProperty(l, "visibility") !== "none"; });
  var g = map.queryRenderedFeatures(e.point, { layers: lay });
  if (g.length) {
    var gp = g[0].properties;
    new maplibregl.Popup({ maxWidth: "270px" }).setLngLat(e.lngLat).setHTML(
      "<b>" + esc(gp.f || "Gebäude") + "</b><table class='pop-tab'>" +
      zeile("Geschosse", gp.gs == null || gp.gs === "null" ? "k. A." : esc(gp.gs)) +
      zeile("Höhe (genähert)", fmt1.format(gp.h) + " m") + "</table>" +
      "<div class='pop-q'>ALKIS vereinfacht, Höhe = Geschosse × 3 m. © GeoBasis-DE/LGB, dl-de/by-2-0</div>").addTo(map);
    return;
  }
  var zl = ["zellen-3d", "zellen-flach"].filter(function (l) { return map.getLayoutProperty(l, "visibility") !== "none"; });
  var c = zl.length ? map.queryRenderedFeatures(e.point, { layers: zl }) : [];
  if (c.length) {
    var p = c[0].properties, n = function (k) { var v = p[k]; return (v === undefined || v === "null" || v === null) ? null : Number(v); };
    new maplibregl.Popup({ maxWidth: "290px" }).setLngLat(e.lngLat).setHTML(
      "<b>Gitterzelle 100 × 100 m</b><br>" + esc(p.st + " " + name(p.st)) + "<table class='pop-tab'>" +
      zeile("Einwohner", zz(n("ew"))) + zeile("Durchschnittsalter", n("d_alter") == null ? "k. A." : fmt1.format(n("d_alter"))) +
      zeile("unter 18", proz(n("q_u18"))) + zeile("65 und älter", proz(n("q_65p"))) + zeile("Wohnungen", zz(n("w_ges"))) +
      zeile("davon vor 1949", proz(n("q_v1949"))) + zeile("mit Fernwärme", proz(n("q_fern"))) + "</table>" +
      "<div class='pop-q'>Zensus 2022, 15.05.2022, © Statistische Ämter des Bundes und der Länder, dl-de/by-2-0. Kleine Werte sind durch die Geheimhaltung unscharf, Anteile können darum über 100 % liegen.</div>").addTo(map);
    return;
  }
  var t = map.queryRenderedFeatures(e.point, { layers: ["teile-flaeche"] });
  if (t.length) zustand({ nr: t[0].properties.nr === gewaehlt ? "" : t[0].properties.nr });
});
var schild = document.getElementById("schild");
map.on("mousemove", function (e) {
  var t = map.queryRenderedFeatures(e.point, { layers: ["teile-flaeche"] });
  map.getCanvas().style.cursor = t.length ? "pointer" : "";
  if (t.length && FEIN) {
    var nr = t[0].properties.nr;
    schild.textContent = nr + " " + name(nr) + ": rund " + rundEw(kachel(K.stadtteile[nr], "einwohner").wert) + " Einwohner";
    schild.style.left = e.point.x + "px"; schild.style.top = e.point.y + "px"; schild.style.display = "block";
  } else schild.style.display = "none";
});
map.on("mouseout", function () { schild.style.display = "none"; });
map.on("zoomend", function () { if (S.nr && map.getZoom() >= 14) gebaeudeLaden(S.nr); });

map.on("load", function () {
  bereit = true;
  var att = document.querySelector(".maplibregl-ctrl-attrib"); if (att) att.classList.remove("maplibregl-compact-show");
  map.setLight({ anchor: "viewport", position: [1.4, 200, 35], intensity: 0.38, color: "#ffffff" });
  themaAnwenden("stadtteile");
  waehle("");
  if (wartend) { var w = wartend; wartend = null; zustand(w); }
  status();
  window.KIEZ_BEREIT = false;
  map.once("idle", function () { window.KIEZ_BEREIT = true; });
});

// =====================================================================
// Fragen: Schritte steuern die Karte
// =====================================================================
var SCHRITTE = {
  0: { nr: "", thema: "stadtteile", grenze: false, geb3d: false, luftbild: false, kamera: "stadt", pitch: 0, bearing: 0 },
  1: { nr: "", thema: "ew", grenze: false, geb3d: false, luftbild: false, kamera: "stadt", pitch: 52, bearing: -16 },
  2: { nr: A.FRAGE.alt, thema: "d_alter", grenze: false, geb3d: false, kamera: "stadt", pitch: 48, bearing: 12 },
  3: { nr: A.FRAGE.kind, thema: "q_u18", grenze: false, geb3d: false, kamera: "teil", pitch: 50, bearing: -24, maxZoom: 14 },
  4: { nr: A.FRAGE.altbau, thema: "q_v1949", grenze: false, geb3d: false, luftbild: false, kamera: "teil", pitch: 50, bearing: 18, maxZoom: 14.5 },
  5: { nr: A.FRAGE.fern, thema: "q_fern", grenze: false, geb3d: false, kamera: "teil", pitch: 50, bearing: -10, maxZoom: 14 },
  6: { nr: GZ ? GZ.p.st : "", thema: "stadtteile", grenze: true, geb3d: false, luftbild: false, kamera: "zelle", pitch: 0, bearing: 0 },
  7: { nr: "", thema: "ew", grenze: false, geb3d: false, luftbild: false, kamera: "stadt", pitch: 45, bearing: -8 },
  8: { nr: "", thema: "q_u18", grenze: false, geb3d: false, luftbild: false, kamera: "stadt", pitch: 48, bearing: -12 },
  9: { nr: "", thema: "q_v1949", grenze: false, geb3d: false, luftbild: false, kamera: "stadt", pitch: 48, bearing: 14 },
  10: { nr: "", thema: "ew", grenze: false, geb3d: false, kamera: "stadt", pitch: 52, bearing: -16 }
};
var aktiv = -1;
function schritt(i, zwingen) {
  if (i === aktiv && !zwingen) return;
  aktiv = i;
  document.querySelectorAll(".erzaehlung .frage").forEach(function (f) { f.classList.toggle("ist-aktiv", +f.dataset.schritt === i); });
  if (SCHRITTE[i]) zustand(Object.assign({}, SCHRITTE[i]));
}
A.schritt = schritt;
document.querySelectorAll("[data-zeige]").forEach(function (b) {
  b.addEventListener("click", function () {
    var i = +b.dataset.zeige, z = Object.assign({}, SCHRITTE[i]);
    if (b.dataset.gebaeude) { z.geb3d = true; z.pitch = 58; z.bearing = -20; z.zoomPlus = 0.8; z.maxZoom = 15.5; }
    if (b.dataset.luftbild) { z.luftbild = !S.luftbild; delete z.kamera; }
    aktiv = i; zustand(z);
    if (SCHMAL) document.getElementById("buehne").scrollIntoView({ behavior: RUHIG ? "auto" : "smooth", block: "start" });
  });
});

function scrollSteuerung() {
  if (!window.ScrollTrigger) {         // ohne GSAP: Beobachter
    var io = new IntersectionObserver(function (es) { es.forEach(function (e) { if (e.isIntersecting) schritt(+e.target.dataset.schritt); }); }, { rootMargin: "-45% 0px -45% 0px" });
    document.querySelectorAll(".erzaehlung .frage").forEach(function (f) { io.observe(f); });
    return;
  }
  gsap.registerPlugin(ScrollTrigger);
  var linie = SCHMAL ? "top 78%" : "top 55%", ende = SCHMAL ? "bottom 78%" : "bottom 55%";
  document.querySelectorAll(".erzaehlung .frage").forEach(function (f) {
    ScrollTrigger.create({ trigger: f, start: linie, end: ende, onToggle: function (s) { if (s.isActive) schritt(+f.dataset.schritt); } });
  });
  // Kopfleiste weicht beim Scrollen nach unten aus und kommt beim Hochscrollen zurück
  ScrollTrigger.create({ start: 0, end: "max", onUpdate: function (s) {
    document.documentElement.classList.toggle("kopf-weg", s.direction > 0 && s.scroll() > 200);
  } });
  // aktuelle Rubrik in der Navigation
  ["fragen", "stadtteile", "schaugrafik", "grenzfall", "methode"].forEach(function (id) {
    var a = document.querySelector('.nav[href="#' + id + '"]'), z = document.getElementById(id);
    if (!a || !z) return;
    ScrollTrigger.create({ trigger: id === "fragen" ? ".fragen" : z, start: "top 50%", end: "bottom 50%", onToggle: function (s) { if (s.isActive) a.setAttribute("aria-current", "true"); else a.removeAttribute("aria-current"); } });
  });
}

// ---------- Ruhezustand: die schräge Stadt dreht sich langsam, wenn niemand etwas tut
(function () {
  if (RUHIG || !FEIN || !window.gsap) return;
  var letzte = performance.now(), basis = null, sichtbar = true, t0 = 0;
  ["pointermove", "wheel", "keydown", "touchstart", "scroll"].forEach(function (ev) { addEventListener(ev, function () { letzte = performance.now(); basis = null; }, { passive: true }); });
  new IntersectionObserver(function (es) { sichtbar = es[0].isIntersecting; }).observe(document.getElementById("buehne"));
  gsap.ticker.add(function (t) {
    if (!bereit || !sichtbar || document.hidden) return;
    if (performance.now() - letzte < 2200 || map.isMoving() || map.getPitch() < 25) { basis = null; return; }
    if (basis === null) { basis = map.getBearing(); t0 = t; }
    map.setBearing(basis + Math.sin((t - t0) * 0.16) * 4);
  });
})();

// =====================================================================
// Steckbrief und Register
// =====================================================================
var sel = document.getElementById("gebiet");
sel.appendChild(new Option("Ganz Potsdam", ""));
ST.features.forEach(function (f) { sel.appendChild(new Option(f.properties.nr + " " + f.properties.name, f.properties.nr)); });
sel.addEventListener("change", function () { zustand({ nr: sel.value }); });
var kurzQuelle = function (qq) { var m = qq.match(/\(([^)]+)\)\s*$/); return "Zensus 2022, " + (m ? m[1] : ""); };
var TITEL = { alter: "Alter", baujahr: "Baujahr des Gebäudes", heizung: "Überwiegende Heizungsart", energie: "Energieträger der Heizung" };
A.TITEL = TITEL;

function zeigeZahlen(nr) {
  var G = nr ? K.stadtteile[nr] : K.stadt;
  setze("name", nr ? G.name : "Potsdam");
  setze("art", nr ? "Stadtteil " + nr + " der Landeshauptstadt Potsdam" : "Landeshauptstadt, " + ST.features.length + " Stadtteile");
  setze("flaeche", fmt1.format(G.flaeche_km2));
  setze("zellen", fmt.format(G.zellen));
  setze("gebaeude", G.gebaeude && G.gebaeude.anzahl ? fmt.format(G.gebaeude.anzahl) + " Gebäude laut ALKIS, davon " + fmt.format(G.gebaeude.wohngebaeude) + " Wohngebäude" : "keine Gebäude zugeordnet");
  sel.value = nr;
  var box = document.getElementById("kacheln"); box.innerHTML = "";
  G.kacheln.forEach(function (k) {
    var d = el("div", "kachel"), z = el("div", "zahl");
    if (k.anzeige === "summe") { d.appendChild(el("div", "vorsatz", "rund")); z.textContent = rundEw(k.wert); }
    else if (k.wert == null) z.textContent = "k. A.";
    else { z.textContent = fmt1.format(k.wert); z.appendChild(el("small", null, "%")); }
    d.appendChild(z); d.appendChild(el("div", "titel-k", k.titel));
    var qe = el("div", "quelle", kurzQuelle(k.quelle));
    qe.title = k.quelle + (k.nenner ? " Zähler " + fmt.format(k.zaehler) + ", Nenner " + fmt.format(k.nenner) + "." : "");
    d.appendChild(qe); box.appendChild(d);
  });
  var gp = (K.gegenprobe || {})[nr || "stadt"], gpEl = document.getElementById("gegenprobe"); gpEl.innerHTML = "";
  if (gp) {
    gpEl.appendChild(document.createTextNode("Gegenprobe: " + gp.art + " am " + gp.stichtag + ": " + fmt.format(gp.einwohner) + " ("));
    var a = el("a", null, gp.quelle); a.href = gp.url; gpEl.appendChild(a);
    gpEl.appendChild(document.createTextNode("). Anderer Stichtag und andere Zählweise als der Zensus, kleine Unterschiede sind zu erwarten."));
  }
  var vbox = document.getElementById("verteilungen"); vbox.innerHTML = "";
  ["alter", "baujahr", "heizung", "energie"].forEach(function (key) {
    var v = G.verteilungen[key], summe = v.insgesamt;
    var klassen = v.werte.reduce(function (s, b) { return s + b[1]; }, 0);
    var max = Math.max.apply(null, v.werte.map(function (w) { return w[1]; })) || 1;
    var d = el("div", "vert");
    d.appendChild(el("h4", null, TITEL[key]));
    d.appendChild(el("p", "einheit", v.einheit + " insgesamt " + fmt.format(summe) + (klassen !== summe ? "; Summe der Klassen " + fmt.format(klassen) + " (Geheimhaltung)" : "") + ". Anteile am Insgesamt."));
    var ul = el("ul", "balken");
    v.werte.forEach(function (w) {
      if ((key === "energie" || key === "heizung") && w[1] === 0) return;
      var li = el("li"), l = el("span", "l"); l.appendChild(el("span", null, w[0])); l.appendChild(el("span", null, summe ? fmt1.format(100 * w[1] / summe) + NB + "%" : "k. A."));
      var b = el("span", "b"), i = el("i"); i.style.width = (100 * w[1] / max).toFixed(1) + "%"; b.appendChild(i); b.setAttribute("aria-hidden", "true");
      li.appendChild(l); li.appendChild(b); ul.appendChild(li);
    });
    d.appendChild(ul); d.appendChild(el("p", "quelle", v.quelle)); vbox.appendChild(d);
    if (window.gsap && !RUHIG) gsap.from(d.querySelectorAll(".b i"), { scaleX: 0, duration: 0.8, ease: "expo.out", stagger: 0.03 });
  });
  document.querySelectorAll(".zeile").forEach(function (b) { b.setAttribute("aria-pressed", b.dataset.nr === nr ? "true" : "false"); });
}

var SORT = [
  { id: "nr", name: "Nummer", kachel: "einwohner" },
  { id: "einwohner", name: "Einwohner", kachel: "einwohner" },
  { id: "u18", name: "unter 18", kachel: "u18" },
  { id: "65p", name: "65 und älter", kachel: "65p" },
  { id: "altbau", name: "vor 1949", kachel: "altbau" },
  { id: "fernwaerme", name: "Fernwärme", kachel: "fernwaerme" }
];
var sortBox = document.getElementById("sortierung");
SORT.forEach(function (s, i) {
  var l = el("label", "chip"), r = document.createElement("input");
  r.type = "radio"; r.name = "sort"; r.value = s.id; r.checked = i === 0;
  l.appendChild(r); l.appendChild(el("span", null, s.name)); sortBox.appendChild(l);
});
function zeileBau(nr, s, max) {
  var k = kachel(K.stadtteile[nr], s.kachel), li = el("li"), b = el("button", "zeile"); b.type = "button"; b.dataset.nr = nr;
  b.setAttribute("aria-pressed", nr === gewaehlt ? "true" : "false");
  b.style.setProperty("--farbe", FARBE[nr]);
  b.appendChild(el("span", "zeile__nr", nr)); b.appendChild(el("span", "zeile__name", name(nr)));
  var bal = el("span", "zeile__balken"), i = el("i"); i.style.width = (k.wert == null ? 0 : 100 * k.wert / max).toFixed(1) + "%"; bal.appendChild(i); bal.setAttribute("aria-hidden", "true");
  b.appendChild(bal);
  var wert = el("span", "zeile__wert", k.anzeige === "summe" ? rundEw(k.wert) : proz(k.wert));
  wert.appendChild(el("span", "nur-sr", k.anzeige === "summe" ? " Einwohner, gerundet" : " " + k.titel));
  b.appendChild(wert);
  b.addEventListener("click", function () { zustand({ nr: nr === gewaehlt ? "" : nr }); });
  li.appendChild(b); return li;
}
function register(sortId) {
  var s = SORT.filter(function (x) { return x.id === sortId; })[0], box = document.getElementById("teile"); box.innerHTML = "";
  var nrs = Object.keys(K.stadtteile), max = Math.max.apply(null, nrs.map(function (n) { return kachel(K.stadtteile[n], s.kachel).wert || 0; })) || 1;
  if (s.id === "nr") {
    Object.keys(proBezirk).forEach(function (bz) {
      var g = el("div", "bezirk"), h = el("p", "bezirk__kopf"), i = el("i"); i.style.background = BEZIRKFARBE[bz];
      h.appendChild(i); h.appendChild(document.createTextNode("Stadtbezirk " + bz)); g.appendChild(h);
      var ul = el("ul", "teile"); proBezirk[bz].forEach(function (nr) { ul.appendChild(zeileBau(nr, s, max)); }); g.appendChild(ul); box.appendChild(g);
    });
  } else {
    var ul = el("ul", "teile");
    nrs.sort(function (a, b) { return (kachel(K.stadtteile[b], s.kachel).wert || 0) - (kachel(K.stadtteile[a], s.kachel).wert || 0); })
      .forEach(function (nr) { ul.appendChild(zeileBau(nr, s, max)); });
    box.appendChild(ul);
    if (window.gsap && !RUHIG) gsap.from(ul.querySelectorAll(".zeile__balken i"), { scaleX: 0, duration: 0.7, ease: "expo.out", stagger: 0.015 });
  }
}
sortBox.addEventListener("change", function (e) { register(e.target.value); });
register("nr");
zeigeZahlen("");
document.getElementById("sb-karte").addEventListener("click", function () {
  aktiv = 10; zustand({ nr: S.nr, thema: S.thema === "stadtteile" ? "ew" : S.thema, grenze: false, kamera: S.nr ? "teil" : "stadt", pitch: 50, bearing: -14, maxZoom: 15 });
  document.getElementById("buehne").scrollIntoView({ behavior: RUHIG ? "auto" : "smooth" });
  document.getElementById("frage-10").scrollIntoView({ behavior: RUHIG ? "auto" : "smooth", block: "center" });
});
document.getElementById("sb-grafik").addEventListener("click", function () {
  if (A.schauGebiet) A.schauGebiet(S.nr);
  document.getElementById("schaugrafik").scrollIntoView({ behavior: RUHIG ? "auto" : "smooth" });
});

// =====================================================================
// Grenzfall
// =====================================================================
(function () {
  var gf = K.grenzfall, kern = document.getElementById("grenz-kern");
  if (!gf) { kern.textContent = "Der Vergleich wird beim nächsten Lauf der Auswertung berechnet."; document.getElementById("grenz-mehr").hidden = true; return; }
  var gs = gf.stadt, ab = function (a, b) { return b ? 100 * (b - a) / a : 0; };
  var d = ab(gs.mittelpunkt, gs.flaechenanteilig);
  kern.textContent = "Ganz Potsdam: " + fmt.format(gs.mittelpunkt) + " Einwohner nach Mittelpunkt, " + fmt.format(gs.flaechenanteilig) +
    " nach Fläche (" + (d >= 0 ? "+" : "") + fmt1.format(d) + NB + "%). " + fmt.format(gs.grenzzellen) + " bewohnte Zellen mit " + fmt.format(gs.ew_in_grenzzellen) +
    " Einwohnern liegen auf der Stadtgrenze; bei " + fmt.format(gs.mittelpunkt_aussen_zellen) + " davon (" + fmt.format(gs.mittelpunkt_aussen_ew) + " Einwohner) liegt der Mittelpunkt knapp außerhalb.";
  var zeilen = Object.keys(gf.stadtteile).map(function (nr) { var g = gf.stadtteile[nr]; return { nr: nr, g: g, d: ab(g.mittelpunkt, g.flaechenanteilig) }; })
    .filter(function (x) { return x.g.mittelpunkt > 0; }).sort(function (a, b) { return Math.abs(b.d) - Math.abs(a.d); });
  if (zeilen.length) {
    var gr = zeilen[0], gp = gr.g.flaechenanteilig - gr.g.mittelpunkt;
    document.getElementById("grenz-lead").textContent = "Für ganz Potsdam ändert die Zählweise die Einwohnerzahl um " + (d >= 0 ? "+" : "\u2212") + fmt1.format(Math.abs(d)) + NB + "%. Im Stadtteil " + name(gr.nr) +
      " sind es " + (gr.d >= 0 ? "+" : "\u2212") + fmt1.format(Math.abs(gr.d)) + NB + "%, das sind " + fmt.format(Math.abs(gp)) + " Personen.";
  }
  var tb = document.querySelector("#grenz-tab tbody");
  zeilen.forEach(function (x, i) {
    var tr = el("tr"); if (i >= 8) tr.className = "zu";
    var th = el("th", null, x.nr + " " + name(x.nr)); th.scope = "row"; tr.appendChild(th);
    tr.appendChild(el("td", null, fmt.format(x.g.mittelpunkt)));
    tr.appendChild(el("td", null, fmt.format(x.g.flaechenanteilig)));
    tr.appendChild(el("td", x.d > 0 ? "pos" : x.d < 0 ? "neg" : "", (x.d >= 0 ? "+" : "−") + fmt1.format(Math.abs(x.d)) + NB + "%"));
    var pd = x.g.flaechenanteilig - x.g.mittelpunkt;
    tr.appendChild(el("td", null, (pd >= 0 ? "+" : "−") + fmt.format(Math.abs(pd))));
    tr.appendChild(el("td", null, fmt.format(x.g.grenzzellen)));
    tb.appendChild(tr);
  });
  var mehr = document.getElementById("grenz-mehr"), tab = document.getElementById("grenz-tab");
  if (zeilen.length <= 8) mehr.hidden = true;
  mehr.addEventListener("click", function () { var an = !tab.classList.contains("alle"); tab.classList.toggle("alle", an); mehr.setAttribute("aria-expanded", String(an)); mehr.textContent = an ? "Weniger zeigen" : "Alle Stadtteile zeigen"; });
})();

// Beispielzelle als Zeichnung (SVG) aus den eigenen Geometrien
(function () {
  var box = document.getElementById("grenz-figur"), txt = document.getElementById("grenz-zelle-text"), cap = document.getElementById("grenz-cap");
  if (!GZ) { box.hidden = true; return; }
  var lat0 = GZ.c[1], kx = Math.cos(lat0 * Math.PI / 180) * 111320, ky = 110540, R = 105;   // Ausschnitt ± R Meter
  function P(c) { return [((c[0] - GZ.c[0]) * kx + R).toFixed(1), (R - (c[1] - GZ.c[1]) * ky).toFixed(1)]; }
  function pfad(f) { return polys(f).map(function (p) { return p.map(function (r) { return "M" + r.map(function (c) { return P(c).join(","); }).join("L") + "Z"; }).join(""); }).join(""); }
  var zelle = "M" + GZ.f.geometry.coordinates[0].map(function (c) { return P(c).join(","); }).join("L") + "Z";
  var A1 = GZ.p.st, B1 = GZ.nach, W = 2 * R;
  var nachbarn = Z.features.filter(function (f) { var c = f.geometry.coordinates[0][0]; return Math.abs(c[0] - GZ.c[0]) * kx < R + 120 && Math.abs(c[1] - GZ.c[1]) * ky < R + 120 && f !== GZ.f; })
    .map(function (f) { return "M" + f.geometry.coordinates[0].map(function (c) { return P(c).join(","); }).join("L") + "Z"; }).join("");
  var tA = Math.round(100 * (GZ.anteil[A1] || 0)), tB = Math.round(100 * (GZ.anteil[B1] || 0));
  var mA = P(GZ.mitte[A1] || GZ.c), mB = P(GZ.mitte[B1] || GZ.c), mc = P(GZ.c);
  var svg = '<svg viewBox="0 0 ' + W + ' ' + W + '" role="img" aria-label="Beispielzelle auf der Grenze zwischen ' + esc(name(A1)) + ' und ' + esc(name(B1)) + '">' +
    '<defs><clipPath id="gz-clip"><path d="' + zelle + '"/></clipPath><pattern id="gz-raster" width="10" height="10" patternUnits="userSpaceOnUse"><path d="M10 0H0V10" fill="none" stroke="#cdd1cc" stroke-width=".4"/></pattern></defs>' +
    '<rect width="' + W + '" height="' + W + '" fill="#fafbf8"/><rect width="' + W + '" height="' + W + '" fill="url(#gz-raster)"/>' +
    '<path d="' + pfad(TEIL[A1]) + '" fill="' + FARBE[A1] + '" fill-opacity=".28" fill-rule="evenodd"/>' +
    '<path d="' + pfad(TEIL[B1]) + '" fill="' + FARBE[B1] + '" fill-opacity=".28" fill-rule="evenodd"/>' +
    '<path d="' + nachbarn + '" fill="none" stroke="#13212a" stroke-opacity=".35" stroke-width=".6"/>' +
    '<g class="gz-ganz"><path d="' + zelle + '" fill="' + FARBE[A1] + '"/></g>' +
    '<g class="gz-teil" clip-path="url(#gz-clip)" opacity="0"><path d="' + pfad(TEIL[A1]) + '" fill="' + FARBE[A1] + '" fill-rule="evenodd"/><path d="' + pfad(TEIL[B1]) + '" fill="' + FARBE[B1] + '" fill-rule="evenodd"/></g>' +
    '<path d="' + zelle + '" fill="none" stroke="#13212a" stroke-width="1.6"/>' +
    '<path d="' + pfad(TEIL[A1]) + '" fill="none" stroke="#6a2c82" stroke-width="2.2" fill-rule="evenodd"/>' +
    '<g class="gz-mitte"><circle cx="' + mc[0] + '" cy="' + mc[1] + '" r="3.4" fill="#13212a" stroke="#fff" stroke-width="1.2"/></g>' +
    '<g class="gz-teil" opacity="0" font-family="Barlow Semi Condensed, sans-serif" font-weight="600" font-size="9" fill="#13212a" text-anchor="middle">' +
      '<text x="' + mA[0] + '" y="' + mA[1] + '" paint-order="stroke" stroke="#fff" stroke-width="2.5">' + tA + ' %</text>' +
      '<text x="' + mB[0] + '" y="' + mB[1] + '" paint-order="stroke" stroke="#fff" stroke-width="2.5">' + tB + ' %</text></g>' +
    '<g font-family="Barlow, sans-serif" font-size="6.6" fill="#13212a"><rect x="' + (W - 104) + '" y="' + (W - 34) + '" width="98" height="28" fill="#fafbf8" stroke="#cdd1cc" stroke-width=".5"/><rect x="' + (W - 99) + '" y="' + (W - 29) + '" width="7" height="7" fill="' + FARBE[A1] + '"/><text x="' + (W - 88) + '" y="' + (W - 23) + '">' + A1 + ' ' + esc(name(A1)) + '</text><rect x="' + (W - 99) + '" y="' + (W - 18) + '" width="7" height="7" fill="' + FARBE[B1] + '"/><text x="' + (W - 88) + '" y="' + (W - 12) + '">' + B1 + ' ' + esc(name(B1)) + '</text></g>' +
    '<g font-family="Barlow, sans-serif" font-size="6.4" fill="#4f5d64"><line x1="8" y1="' + (W - 10) + '" x2="58" y2="' + (W - 10) + '" stroke="#13212a" stroke-width="1"/><text x="8" y="' + (W - 14) + '">50 m</text></g>' +
    '</svg>';
  box.innerHTML = svg;
  cap.textContent = "Beispielzelle aus den Daten: die bewohnte Zelle mit den meisten Einwohnern, deren Fläche zwei Stadtteile berührt. Flächenanteile hier im Browser aus " + GZ.stichproben + " Stichpunkten geschätzt; die Tabelle rechnet PostGIS genau. Zensus 2022, © Statistische Ämter des Bundes und der Länder, dl-de/by-2-0; Stadtteile © Landeshauptstadt Potsdam, dl-zero-de/2.0.";
  function modus(m) {
    document.querySelectorAll(".umschalter__k").forEach(function (b) { b.setAttribute("aria-pressed", String(b.dataset.modus === m)); });
    var fl = m === "flaeche";
    box.querySelector(".gz-ganz").style.opacity = fl ? 0 : 1;
    box.querySelectorAll(".gz-teil").forEach(function (g) { g.style.opacity = fl ? 1 : 0; });
    box.querySelector(".gz-mitte").style.opacity = fl ? 0.35 : 1;
    txt.textContent = fl
      ? "Nach Fläche: etwa " + tA + NB + "% der Zelle liegen im Stadtteil " + name(A1) + ", " + tB + NB + "% im Stadtteil " + name(B1) + ". Von den " + fmt.format(GZ.p.ew) + " Einwohnern zählen dann rund " + fmt.format(Math.round(GZ.p.ew * tA / 100)) + " für den einen und " + fmt.format(Math.round(GZ.p.ew * tB / 100)) + " für den anderen."
      : "Nach Mittelpunkt: Der Mittelpunkt liegt im Stadtteil " + name(A1) + ", also zählen alle " + fmt.format(GZ.p.ew) + " Einwohner dieser Zelle dort, keiner im Stadtteil " + name(B1) + ".";
  }
  document.querySelectorAll(".umschalter__k").forEach(function (b) { b.addEventListener("click", function () { modus(b.dataset.modus); }); });
  modus("mittelpunkt");
})();

// ---------- Titel: Zeilen richten sich auf (einmal), dann Fragen-Steuerung
(function () {
  if (window.gsap && !RUHIG) {
    gsap.from(".titel__z > span", { yPercent: 105, duration: 1.1, ease: "expo.out", stagger: 0.08 });
    gsap.from(".stadtzahlen div", { y: 14, autoAlpha: 0, duration: 0.8, ease: "expo.out", stagger: 0.05, delay: 0.25 });
  }
  scrollSteuerung();
  schritt(0, true);
})();
})();
