/* Kiezatlas Potsdam: Bauzeiten (B5, Zweig 1). Zensus 2022, Gebäude mit Wohnraum je 100-m-Zelle nach Bauzeit.
   Eine Datei für drei Seiten (body data-seite: karte | methode | daten). Daten nur per <script> (file://),
   alle Zahlen im Text werden hier aus daten/jahre_zellen.js gerechnet, keine ist von Hand eingesetzt.
   Keine Gebäudefärbung: Zweig 1 zeigt Zellen, nie einzelne Gebäude. */
(function () {
"use strict";
var T = window.KIEZ_THEMEN, K = window.KIEZ_KENNZAHLEN, Z = window.KIEZ_ZELLEN, ST = window.KIEZ_STADTTEILE;
var SEITE = document.body.getAttribute("data-seite");
var RUHIG = matchMedia("(prefers-reduced-motion: reduce)").matches;
var SCHMAL = matchMedia("(max-width:860px)").matches;
var FEIN = matchMedia("(hover:hover) and (pointer:fine)").matches;
var fmt = T.fmt, esc = T.esc, NB = " ";

// Bauzeit-Palette: vom Grenzviolett über ein gedämpftes Mittel zum Tiefblau (DESIGN.md, k5). Kein Farbton zwischen 20° und 70°.
var PALETTE = ["#42194d", "#613878", "#756092", "#8c87a9", "#74a1aa", "#428293", "#226174", "#1c4a5b"];
var STUFEN = T.STUFEN, GRENZEN = [20, 40, 60, 80];
var WENIG = 5;            // unter 5 Gebäuden je Zelle: Anteile sehr unsicher, blass gezeichnet
var MINDEST = 50;         // Gebiete mit weniger Gebäuden bekannter Bauzeit kommen in keine Rangliste
// Raumebene: heute die 32 Stadtteile. Planungsräume folgen, sobald die Datei der Stadt da ist (Handdownload H1).
var RAUM = { id: "stadtteile", einzahl: "Stadtteil", mehrzahl: "Stadtteile", feld: "st" };

function el(t, c, x) { var e = document.createElement(t); if (c) e.className = c; if (x != null) e.textContent = x; return e; }
function setze(k, w) { document.querySelectorAll('[data-j="' + k + '"]').forEach(function (n) { n.textContent = w; }); }
function rund(v) { if (v == null) return "k. A."; if (v > 0 && v < 10) return "unter 10"; return T.rundEw(v); }
function pz(v) { if (v == null) return "k. A."; if (v > 0 && v < 1) return "unter 1" + NB + "%"; return fmt.format(Math.round(v)) + NB + "%"; }
function meldung(text) { var m = document.getElementById("j-fixture"); if (m) { m.hidden = false; m.textContent = text; } }

// ---------- Daten laden und prüfen
var D = null, KL = [], N = 0, G = [], A = [], V = [], STAT = null;
function slug(s) { return s.replace(/^vor /, "vor_").replace(/^ab /, "ab_").replace(/–/g, "_").replace(/\s+/g, "_"); }
function jahre(s) { return (s.match(/\d{4}/g) || []).map(Number); }
// Name einer Spanne aus den Klassennamen, z. B. „1949 bis 1990“, „vor 1949“, „ab 1991“
function spanneName(von, bis) {
  if (von === bis) return KL[von];
  if (von === 0 && bis === KL.length - 1) return "alle Bauzeiten";
  var u = jahre(KL[von]), o = jahre(KL[bis]);
  if (von === 0) return "vor " + (o[o.length - 1] + 1);
  if (bis === KL.length - 1) return "ab " + u[0];
  return u[0] + " bis " + o[o.length - 1];
}

function annehmen(d) {
  if (!d) { meldung("Die Bauzeit-Daten (daten/jahre_zellen.js) ließen sich nicht laden."); return false; }
  D = d; KL = d.klassen; N = d.anzahl;
  if (d.fixture) meldung("Beispieldaten: Diese Ansicht zeigt unechte Werte zum Bauen der Seite, keine Aussage über Potsdam.");
  if (Z) {
    T.ebenen.registrieren({ id: "jahre_zellen", datei: "daten/jahre_zellen.js", global: "KIEZ_JAHRE_ZELLEN", art: "zellwert", themen: [] });
    G = T.ebenen.zellwerte("jahre_zellen", "gebaeude"); A = T.ebenen.zellwerte("jahre_zellen", "anteile"); V = T.ebenen.zellwerte("jahre_zellen", "vorherrschend");
    if (!G || !A || !V) { meldung("Die Bauzeit-Daten passen nicht zu den Zellen der Karte; die Seite zeigt nichts an."); return false; }
  } else { G = d.gebaeude; A = d.anteile; V = d.vorherrschend; }
  STAT = rechnen();
  return true;
}

// Stadt- und Gebietswerte. Genähert: Anteile je Zelle mal Gebäudezahl der Zelle, Summe je Gebiet.
// Zellen ohne bekannte Klassen zählen zur Gebäudezahl, nicht zur Mischung (gk).
function leer() { var c = []; for (var k = 0; k < KL.length; k++) c.push(0); return { g: 0, gk: 0, z: 0, c: c }; }
function rechnen() {
  var s = { stadt: leer(), raum: {}, zellen: 0, geheim: 0, gleich: 0, wenig: 0, gemischt: 0, mitKlassen: 0 };
  for (var i = 0; i < N; i++) {
    var g = G[i], a = A[i];
    if (g == null) continue;
    s.zellen++; if (g < WENIG) s.wenig++;
    var nr = Z ? Z.features[i].properties[RAUM.feld] : null, r = null;
    if (nr) r = s.raum[nr] = s.raum[nr] || leer();
    [s.stadt, r].forEach(function (x) { if (x) { x.g += g; x.z++; } });
    if (!a) { s.geheim++; continue; }
    s.mitKlassen++;
    if (V[i] == null) s.gleich++;
    if (Math.max.apply(null, a) < 50) s.gemischt++;
    var summe = a.reduce(function (p, q) { return p + q; }, 0) || 1;
    [s.stadt, r].forEach(function (x) { if (!x) return; x.gk += g; a.forEach(function (v, k) { x.c[k] += g * v / summe; }); });
  }
  return s;
}
function anteil(r, von, bis) { if (!r || !r.gk) return null; var c = 0; for (var k = von; k <= bis; k++) c += r.c[k]; return 100 * c / r.gk; }
// hochgerechnet auf alle Gebäude des Gebiets (auch in Zellen ohne Klassen)
function anzahl(r, von, bis) { var p = anteil(r, von, bis); return p == null ? null : r.g * p / 100; }
function rangliste(von, bis, n) {
  return Object.keys(STAT.raum).filter(function (nr) { return STAT.raum[nr].gk >= MINDEST; })
    .map(function (nr) { return { nr: nr, p: anteil(STAT.raum[nr], von, bis) }; })
    .sort(function (a, b) { return b.p - a.p; }).slice(0, n || 3);
}
function aufzaehlung(l) {
  var t = l.map(function (x) { return T.name(x.nr) + " (" + pz(x.p) + ")"; });
  return t.length > 1 ? t.slice(0, -1).join(", ") + " und " + t[t.length - 1] : t.join("");
}

// ---------- Zahlen in den Text (alle Seiten)
var QUELLE_KURZ = "";
function zahlenFuellen() {
  var s = STAT, q = D.quellen[Object.keys(D.quellen)[0]];
  QUELLE_KURZ = "Zensus 2022, Stichtag " + new Date(q.stand || "2022-05-15").toLocaleDateString("de-DE");
  setze("stand", new Date(D.stand).toLocaleDateString("de-DE"));
  setze("quelle", q.quelle); setze("vermerk", q.vermerk); setze("beschriftung", D.beschriftung);
  setze("zellen-alle", fmt.format(N)); setze("zellen", fmt.format(s.zellen)); setze("zellen-ohne", fmt.format(N - s.zellen));
  setze("gebaeude", rund(s.stadt.g)); setze("mitklassen", fmt.format(s.mitKlassen));
  setze("geheim", fmt.format(s.geheim)); setze("gleich", fmt.format(s.gleich)); setze("wenig", fmt.format(s.wenig));
  setze("wenig-grenze", String(WENIG)); setze("mindest", String(MINDEST));
  setze("geheim-g", rund(s.stadt.g - s.stadt.gk)); setze("geheim-p", pz(100 * (s.stadt.g - s.stadt.gk) / s.stadt.g));
  setze("klassen-zahl", String(KL.length)); setze("klassen-liste", KL.join(", "));
  setze("raum-name", RAUM.einzahl); setze("raum-mehrzahl", RAUM.mehrzahl);
  setze("raum-zahl", String(Z ? Object.keys(s.raum).length : Object.keys(K.stadtteile).length));
  [[1, 0, 0], [2, 2, 3], [3, 4, KL.length - 1], [4, 6, KL.length - 1]].forEach(function (f) {
    setze("f" + f[0] + "-n", rund(anzahl(s.stadt, f[1], f[2]))); setze("f" + f[0] + "-p", pz(anteil(s.stadt, f[1], f[2])));
    if (Z) setze("f" + f[0] + "-top", aufzaehlung(rangliste(f[1], f[2])));
  });
  setze("f5-m", fmt.format(s.gemischt)); setze("f5-z", fmt.format(s.mitKlassen));
  setze("f6-geheim", fmt.format(s.geheim)); setze("f6-wenig", fmt.format(s.wenig));
  var v = document.getElementById("j-vermerk");
  if (v) v.textContent = D.beschriftung + ". " + q.quelle + ". " + q.vermerk + ". Stand der Auswertung " + new Date(D.stand).toLocaleDateString("de-DE") + ".";
}

// Schichtband: Anteile der Klassen als ein Streifen (Startseite der Bauzeiten, Steckbrief, Liste)
function schicht(box, r, mitText) {
  box.innerHTML = "";
  KL.forEach(function (n, k) {
    var p = anteil(r, k, k) || 0, s = el("span", "j-schicht__teil");
    s.style.flexGrow = String(p); s.style.background = PALETTE[k];
    if (mitText) s.title = n + ": " + pz(p);
    box.appendChild(s);
  });
}

if (SEITE === "karte") T.laden("daten/jahre_zellen.js", "KIEZ_JAHRE_ZELLEN", function (d) { if (annehmen(d)) karte(); else window.KIEZ_BEREIT = true; });
else T.laden("daten/jahre_zellen.js", "KIEZ_JAHRE_ZELLEN", function (d) { if (annehmen(d)) { zahlenFuellen(); if (SEITE === "daten") daten(); if (SEITE === "methode") methode(); } window.KIEZ_BEREIT = true; });

// =====================================================================================
// Seite „Bauzeiten“: Karte, Leiste, Fragen, Vergleich
// =====================================================================================
function karte() {
  zahlenFuellen();
  var S = { ansicht: "ueberblick", von: 0, bis: 0, d3: false, luft: false, nr: "" };
  var hashDa = false;
  (function () {
    var h = {}; location.hash.replace(/^#/, "").split("&").forEach(function (p) { var kv = p.split("="); if (kv[0]) h[decodeURIComponent(kv[0])] = decodeURIComponent(kv[1] || ""); });
    var max = KL.length - 1, ok = function (x) { return /^\d$/.test(x) && +x <= max; };
    if (h.ansicht === "spanne" || h.ansicht === "ueberblick") { S.ansicht = h.ansicht; hashDa = true; }
    if (ok(h.von) && ok(h.bis) && +h.von <= +h.bis) { S.von = +h.von; S.bis = +h.bis; hashDa = true; }
    S.d3 = h["3d"] === "1"; S.luft = h.luft === "1";
    if (h.st && T.TEIL[h.st]) S.nr = h.st;
  })();

  // Eigenschaften an die Zellen: j_g Gebäude, j_s Zustand (0 keine, 1 Klassen geheim, 2 Gleichstand, 3 Klasse), j_a0…7, j_v, j_w
  Z.features.forEach(function (f, i) {
    var p = f.properties, g = G[i], a = A[i];
    p.j_g = g == null ? 0 : g;
    p.j_s = g == null ? 0 : !a ? 1 : V[i] == null ? 2 : 3;
    p.j_v = V[i] == null ? -1 : V[i];
    p.j_w = g != null && g < WENIG ? 1 : 0;
    for (var k = 0; k < KL.length; k++) p["j_a" + k] = a ? a[k] : 0;
  });

  // Stadtschicht im Auftakt, Kopfzahlen
  schicht(document.getElementById("j-stadtschicht"), STAT.stadt, true);
  var marken = document.getElementById("j-stadtmarken");
  KL.forEach(function (n, k) { var li = el("li"), i = el("i"); i.style.background = PALETTE[k]; li.appendChild(i); li.appendChild(el("span", null, n)); li.appendChild(el("b", null, pz(anteil(STAT.stadt, k, k)))); marken.appendChild(li); });
  var zahlen = document.getElementById("j-zahlen");
  [["Gebäude mit Wohnraum", "rund " + rund(STAT.stadt.g)], ["Zellen mit Gebäuden", fmt.format(STAT.zellen)], ["vor 1949 gebaut", pz(anteil(STAT.stadt, 0, 1))], ["seit 1991 gebaut", pz(anteil(STAT.stadt, 4, KL.length - 1))]]
    .forEach(function (z) { var d = el("div"); d.appendChild(el("dt", null, z[0])); d.appendChild(el("dd", null, z[1])); zahlen.appendChild(d); });
  document.getElementById("j-zahlen-quelle").textContent = D.beschriftung + ". Anteile genähert aus den Zellen, Zahlen gerundet. " + D.quellen[Object.keys(D.quellen)[0]].vermerk + ".";

  // ---------- Karte
  var LEER = { type: "FeatureCollection", features: [] }, bereit = false;
  var start = { bounds: T.GANZ, fitBoundsOptions: { padding: SCHMAL ? 12 : 40 } };
  var map = new maplibregl.Map(Object.assign({
    container: "karte",
    style: { version: 8, transition: { duration: RUHIG ? 0 : 450, delay: 0 }, sources: {
        basemap: { type: "raster", tileSize: 256, maxzoom: 18, tiles: ["https://sgx.geodatenzentrum.de/wmts_basemapde/tile/1.0.0/de_basemapde_web_raster_grau/default/GLOBAL_WEBMERCATOR/{z}/{y}/{x}.png"],
          attribution: 'Hintergrund © <a href="https://basemap.de">basemap.de / BKG</a>, <a href="https://www.govdata.de/dl-de/by-2-0">dl-de/by-2-0</a>' },
        dop: { type: "raster", tileSize: 256, maxzoom: 20, tiles: ["https://isk.geobasis-bb.de/mapproxy/dop20c/service/wms?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&LAYERS=bebb_dop20c&STYLES=&CRS=EPSG:3857&BBOX={bbox-epsg-3857}&WIDTH=256&HEIGHT=256&FORMAT=image/jpeg"],
          attribution: 'Luftbild © GeoBasis-DE/LGB, <a href="https://www.govdata.de/dl-de/by-2-0">dl-de/by-2-0</a>' },
        zellen: { type: "geojson", data: Z, attribution: 'Zensus 2022 © Statistische Ämter des Bundes und der Länder, <a href="https://www.govdata.de/dl-de/by-2-0">dl-de/by-2-0</a>, Daten verändert (eigene Berechnung)' },
        teile: { type: "geojson", data: ST, promoteId: "nr", attribution: "Stadtteile © Landeshauptstadt Potsdam, dl-zero-de/2.0" } },
      layers: [
        { id: "papier", type: "background", paint: { "background-color": "#e6e9e4" } },
        { id: "basemap", type: "raster", source: "basemap", paint: { "raster-opacity": 0.55, "raster-saturation": -1 } },
        { id: "dop", type: "raster", source: "dop", layout: { visibility: "none" }, paint: { "raster-saturation": -0.6 } },
        { id: "zellen-2d", type: "fill", source: "zellen", filter: ["==", ["get", "j_s"], 3], paint: { "fill-color": PALETTE[0], "fill-opacity": 0.9, "fill-outline-color": "rgba(250,251,248,0.4)" } },
        { id: "zellen-muster", type: "fill", source: "zellen", filter: ["==", ["get", "j_s"], 1], paint: { "fill-color": "#fafbf8", "fill-opacity": 0.95 } },
        { id: "zellen-3d", type: "fill-extrusion", source: "zellen", layout: { visibility: "none" }, paint: { "fill-extrusion-color": PALETTE[0], "fill-extrusion-height": 0, "fill-extrusion-opacity": 0.94, "fill-extrusion-vertical-gradient": true } },
        { id: "teile-linie", type: "line", source: "teile", paint: { "line-color": "#13212a", "line-width": 0.8, "line-opacity": 0.4 } },
        { id: "teile-wahl", type: "line", source: "teile", paint: { "line-color": "#6a2c82", "line-width": ["case", ["boolean", ["feature-state", "gewaehlt"], false], 3.2, 0] } }
      ] },
    maxZoom: 18, maxPitch: 70, attributionControl: false, fadeDuration: RUHIG ? 0 : 300, cooperativeGestures: false,
    locale: { "NavigationControl.ZoomIn": "Vergrößern", "NavigationControl.ZoomOut": "Verkleinern", "NavigationControl.ResetBearing": "Nach Norden ausrichten", "AttributionControl.ToggleAttribution": "Quellen ein- oder ausblenden" }
  }, start));
  map.scrollZoom.disable();
  map.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), "top-right");
  map.addControl(new maplibregl.AttributionControl({ compact: true }), "bottom-right");
  window.KIEZ_KARTE = map;

  // Muster für Zustände, die keine Bauzeit-Farbe haben dürfen: Schraffur (Klassen geheim), Punkte (Gleichstand)
  function muster(art) {
    var n = 8, c = document.createElement("canvas"); c.width = c.height = n;
    var x = c.getContext("2d"); x.fillStyle = "rgba(250,251,248,0.92)"; x.fillRect(0, 0, n, n); x.fillStyle = "#13212a";
    if (art === "schraffur") { for (var i = 0; i < n; i++) { x.fillRect(i, n - 1 - i, 1, 1); } }
    else { x.fillRect(1, 1, 2, 2); x.fillRect(5, 5, 2, 2); }
    return { width: n, height: n, data: new Uint8Array(x.getImageData(0, 0, n, n).data.buffer) };
  }

  function summe() { var e = ["+", 0]; for (var k = S.von; k <= S.bis; k++) e.push(["get", "j_a" + k]); return e; }
  function farbeUeberblick() { var e = ["match", ["get", "j_v"]]; PALETTE.forEach(function (c, k) { e.push(k, c); }); e.push("#fafbf8"); return e; }
  function farbeSpanne() { var e = ["step", summe(), STUFEN[0]]; GRENZEN.forEach(function (g, i) { e.push(g, STUFEN[i + 1]); }); return e; }
  function hoeheAus(anz) { return ["interpolate", ["linear"], ["zoom"], 10, ["*", anz, 42], 12, ["*", anz, 15], 14, ["*", anz, 5], 16, ["*", anz, 2]]; }

  function anwenden() {
    if (!bereit) return;
    var sp = S.ansicht === "spanne";
    var farbe = sp ? farbeSpanne() : farbeUeberblick();
    var filt = sp ? [">=", ["get", "j_s"], 2] : ["==", ["get", "j_s"], 3];
    var deck = ["case", ["==", ["get", "j_w"], 1], 0.38, 0.9];
    map.setFilter("zellen-2d", filt); map.setFilter("zellen-3d", filt);
    map.setPaintProperty("zellen-2d", "fill-color", farbe); map.setPaintProperty("zellen-2d", "fill-opacity", deck);
    map.setPaintProperty("zellen-3d", "fill-extrusion-color", farbe);
    map.setPaintProperty("zellen-3d", "fill-extrusion-height", hoeheAus(sp ? ["*", ["get", "j_g"], ["/", summe(), 100]] : ["get", "j_g"]));
    map.setFilter("zellen-muster", sp ? ["==", ["get", "j_s"], 1] : ["any", ["==", ["get", "j_s"], 1], ["==", ["get", "j_s"], 2]]);
    map.setPaintProperty("zellen-muster", "fill-pattern", ["match", ["get", "j_s"], 2, "j-punkte", "j-schraffur"]);
    map.setLayoutProperty("zellen-3d", "visibility", S.d3 ? "visible" : "none");
    map.setLayoutProperty("zellen-2d", "visibility", S.d3 ? "none" : "visible");
    map.setLayoutProperty("dop", "visibility", S.luft ? "visible" : "none");
    map.setLayoutProperty("basemap", "visibility", S.luft ? "none" : "visible");
    leisteZeigen(); listeZeigen(); hashSchreiben();
  }
  function hashSchreiben() {
    if (!bereit) return;
    var t = ["ansicht=" + S.ansicht];
    if (S.ansicht === "spanne") t.push("von=" + S.von, "bis=" + S.bis);
    if (S.d3) t.push("3d=1"); if (S.luft) t.push("luft=1"); if (S.nr) t.push("st=" + S.nr);
    try { history.replaceState(null, "", "#" + t.join("&")); } catch (e) { /* file:// in manchen Browsern */ }
  }
  function kamera(b, neigen) {
    var o = { padding: SCHMAL ? { top: 60, bottom: 150, left: 12, right: 12 } : { top: 90, bottom: 210, left: 40, right: 70 }, pitch: neigen ? 50 : 0, bearing: 0 };
    if (RUHIG) { o.animate = false; map.fitBounds(b, o); } else { o.duration = 1400; o.easing = function (t) { return 1 - Math.pow(1 - t, 4); }; map.fitBounds(b, o); }
  }
  function huelle(nrs) {
    var a = [180, 90, -180, -90];
    nrs.forEach(function (nr) { var u = T.umriss(T.TEIL[nr]); a[0] = Math.min(a[0], u[0][0]); a[1] = Math.min(a[1], u[0][1]); a[2] = Math.max(a[2], u[1][0]); a[3] = Math.max(a[3], u[1][1]); });
    return [[a[0], a[1]], [a[2], a[3]]];
  }
  function dreiD(an) {
    S.d3 = an; document.getElementById("j-dreid").checked = an;
    if (an && map.getPitch() < 20) map.jumpTo({ pitch: 50 });
    if (!an && map.getPitch() > 0) map.jumpTo({ pitch: 0, bearing: 0 });
  }

  // ---------- Kartenleiste: acht Klassen, zwei Regler
  var kbox = document.getElementById("j-klassen"), von = document.getElementById("j-von"), bis = document.getElementById("j-bis");
  von.max = bis.max = String(KL.length - 1);
  kbox.style.setProperty("--n", KL.length);
  document.getElementById("j-regler").style.setProperty("--n", KL.length);
  var maxP = Math.max.apply(null, KL.map(function (n, k) { return anteil(STAT.stadt, k, k) || 0; })) || 1;
  var knoepfe = KL.map(function (n, k) {
    var b = el("button", "j-klasse"); b.type = "button"; b.setAttribute("aria-pressed", "false");
    var balken = el("span", "j-klasse__balken"), i = el("i"); i.style.background = PALETTE[k]; i.style.height = (100 * (anteil(STAT.stadt, k, k) || 0) / maxP).toFixed(1) + "%";
    balken.appendChild(i); b.appendChild(balken);
    var name = el("span", "j-klasse__name"), teile = n.split("–");
    name.appendChild(document.createTextNode(teile[0] + (teile.length > 1 ? "–" : ""))); if (teile.length > 1) { name.appendChild(document.createElement("wbr")); name.appendChild(document.createTextNode(teile[1])); }
    b.appendChild(name);
    b.setAttribute("aria-label", n + ", " + pz(anteil(STAT.stadt, k, k)) + " der Gebäude in Potsdam. Nur diese Bauzeit zeigen.");
    b.addEventListener("click", function () { stopp(); S.ansicht = "spanne"; S.von = S.bis = k; anwenden(); });
    kbox.appendChild(b); return b;
  });
  function regler(e) {
    stopp();
    var v = +von.value, w = +bis.value;
    if (v > w) { if (e && e.target === von) w = v; else v = w; }
    S.von = v; S.bis = w; S.ansicht = "spanne"; anwenden();
  }
  von.addEventListener("input", regler); bis.addEventListener("input", regler);
  document.querySelectorAll('#j-ansicht input').forEach(function (r) { r.addEventListener("change", function () { stopp(); S.ansicht = r.value; anwenden(); }); });
  document.getElementById("j-dreid").addEventListener("change", function (e) { dreiD(e.target.checked); anwenden(); });
  document.getElementById("j-luft").addEventListener("change", function (e) { S.luft = e.target.checked; anwenden(); });

  function leisteZeigen() {
    var sp = S.ansicht === "spanne";
    von.value = String(S.von); bis.value = String(S.bis);
    von.setAttribute("aria-valuetext", KL[S.von]); bis.setAttribute("aria-valuetext", KL[S.bis]);
    knoepfe.forEach(function (b, k) { b.setAttribute("aria-pressed", sp && k >= S.von && k <= S.bis ? "true" : "false"); });
    var rg = document.getElementById("j-regler"); rg.classList.toggle("ist-aus", !sp); rg.style.setProperty("--von", S.von); rg.style.setProperty("--bis", S.bis);
    document.getElementById("zeitleiste").classList.toggle("ist-ueberblick", !sp);
    document.querySelectorAll('#j-ansicht input').forEach(function (r) { r.checked = r.value === S.ansicht; });
    document.getElementById("j-dreid").checked = S.d3; document.getElementById("j-luft").checked = S.luft;
    var name = spanneName(S.von, S.bis);
    setze("spanne-name", name);
    var st = document.getElementById("j-status");
    st.textContent = sp ? "Anteil " + name + " je Zelle" + (S.d3 ? ", Höhe: Zahl dieser Gebäude" : "") : "Bauzeit mit den meisten Gebäuden je Zelle" + (S.d3 ? ", Höhe: Zahl der Gebäude" : "");
    document.getElementById("kartenstatus").textContent = "Karte zeigt: " + st.textContent + (S.nr ? ", ausgewählt " + S.nr + " " + T.name(S.nr) : "") + ".";
    var L = document.getElementById("j-legende"); L.innerHTML = "";
    if (sp) {
      var stf = el("span", "j-legende__stufen"); stf.setAttribute("aria-hidden", "true");
      STUFEN.forEach(function (c) { var x = el("i"); x.style.background = c; stf.appendChild(x); });
      var m = el("span", "j-legende__marken"); [0].concat(GRENZEN, [100]).forEach(function (g) { m.appendChild(el("span", null, String(g))); });
      var box = el("span", "j-legende__skala"); box.appendChild(stf); box.appendChild(m); L.appendChild(box);
      L.appendChild(el("span", "j-legende__text", "Prozent der Gebäude in der Zelle"));
    }
    [["j-legende__muster j-legende__muster--schraffur", "Klassen geheim gehalten"], sp ? null : ["j-legende__muster j-legende__muster--punkte", "zwei Klassen gleichauf"], ["j-legende__muster j-legende__muster--blass", "unter " + WENIG + " Gebäuden, sehr unsicher"]]
      .forEach(function (x) { if (!x) return; var s = el("span", "j-legende__eintrag"), i = el("i", x[0]); i.setAttribute("aria-hidden", "true"); s.appendChild(i); s.appendChild(document.createTextNode(x[1])); L.appendChild(s); });
    L.appendChild(el("span", "j-legende__quelle", D.beschriftung + ". " + QUELLE_KURZ + "."));
  }

  // ---------- Nacheinander zeigen (nur ohne reduzierte Bewegung)
  var spiel = null, spielKnopf = document.getElementById("j-abspielen");
  if (!RUHIG) spielKnopf.hidden = false;
  spielKnopf.setAttribute("aria-pressed", "false");
  function stopp() { if (spiel) { clearInterval(spiel); spiel = null; spielKnopf.setAttribute("aria-pressed", "false"); spielKnopf.querySelector(".j-abspielen__text").textContent = "Nacheinander"; } }
  spielKnopf.addEventListener("click", function () {
    if (spiel) { stopp(); return; }
    S.ansicht = "spanne"; S.von = 0; S.bis = 0; anwenden();
    spielKnopf.setAttribute("aria-pressed", "true"); spielKnopf.querySelector(".j-abspielen__text").textContent = "Anhalten";
    spiel = setInterval(function () { if (S.bis >= KL.length - 1) { stopp(); return; } S.bis++; anwenden(); }, 1300);
  });

  // ---------- Zelle anklicken: alle Klassen mit Quelle
  var popup = new maplibregl.Popup({ closeButton: true, maxWidth: "290px", focusAfterOpen: false });
  function zellText(p) {
    var h = "<b>" + fmt.format(p.j_g) + " Gebäude mit Wohnraum</b><br><span class=\"pop-q\">" + esc(T.name(p.st)) + ", Zelle " + esc(p.id.replace(/^CRS3035RES100m/, "")) + "</span>";
    if (p.j_s === 1) h += "<p class=\"pop-q\">Die Bauzeiten dieser Zelle sind geheim gehalten (auf Null geändert).</p>";
    else {
      h += "<table class=\"pop-tab\"><tbody>";
      KL.forEach(function (n, k) { h += "<tr><td><i class=\"j-punkt\" style=\"background:" + PALETTE[k] + "\"></i>" + esc(n) + "</td><td>" + (p["j_a" + k] ? T.fmt1.format(p["j_a" + k]) + NB + "%" : "–") + "</td></tr>"; });
      h += "</tbody></table>";
      if (p.j_s === 2) h += "<p class=\"pop-q\">Zwei oder mehr Klassen liegen gleichauf.</p>";
      if (p.j_w) h += "<p class=\"pop-q\">Unter " + WENIG + " Gebäuden: Anteile sehr unsicher.</p>";
    }
    return h + "<p class=\"pop-q\">" + esc(D.beschriftung) + ". „–“: null oder geheim gehalten. " + esc(QUELLE_KURZ) + ", Daten verändert (eigene Berechnung).</p>";
  }
  ["zellen-2d", "zellen-3d", "zellen-muster"].forEach(function (id) {
    map.on("click", id, function (e) { var f = e.features[0]; if (!f) return; popup.setLngLat(e.lngLat).setHTML(zellText(f.properties)).addTo(map); });
    map.on("mouseenter", id, function () { map.getCanvas().style.cursor = "pointer"; });
    map.on("mouseleave", id, function () { map.getCanvas().style.cursor = ""; schild.style.display = "none"; });
    if (FEIN) map.on("mousemove", id, function (e) {
      var p = e.features[0].properties;
      schild.textContent = fmt.format(p.j_g) + " Gebäude, " + (p.j_s === 1 ? "Klassen geheim" : p.j_s === 2 ? "Gleichstand" : "meist " + KL[p.j_v]);
      schild.style.display = "block"; schild.style.left = e.point.x + "px"; schild.style.top = e.point.y + "px";
    });
  });
  var schild = document.getElementById("schild");

  // ---------- Fragen: jede stellt die Karte ein
  var FRAGEN = {
    0: { ansicht: "ueberblick", d3: false },
    1: { ansicht: "spanne", von: 0, bis: 0, d3: false, top: true },
    2: { ansicht: "spanne", von: 2, bis: 3, d3: false, top: true },
    3: { ansicht: "spanne", von: 4, bis: KL.length - 1, d3: true, top: true },
    4: { ansicht: "spanne", von: 6, bis: KL.length - 1, d3: false, top: true },
    5: { ansicht: "ueberblick", d3: false },
    6: { ansicht: "ueberblick", d3: false }
  };
  var aktiv = -1, geblaettert = !hashDa;
  function schritt(n) {
    if (n === aktiv) return; aktiv = n;
    document.querySelectorAll("[data-schritt]").forEach(function (f) { f.classList.toggle("ist-aktiv", +f.getAttribute("data-schritt") === n); });
    var f = FRAGEN[n]; if (!f || !geblaettert) return;
    stopp(); S.ansicht = f.ansicht; if (f.von != null) { S.von = f.von; S.bis = f.bis; }
    dreiD(!!f.d3);
    anwenden();
    kamera(f.top ? huelle(rangliste(S.von, S.bis).map(function (x) { return x.nr; })) : T.GANZ, f.d3);
  }
  window.addEventListener("scroll", function () { geblaettert = true; }, { once: true, passive: true });
  // Auslöseband: am Desktop die Bildschirmmitte; auf dem Handy liegt die Bühne oben über dem Text,
  // dort zählt nur der sichtbare Lesebereich darunter (sonst stellt sich die Karte um, bevor die Frage lesbar ist)
  var beob = null, beobZeit = 0;
  function beobachten() {
    if (beob) beob.disconnect();
    var rm = "-45% 0px -45% 0px", schmal = matchMedia("(max-width:860px)").matches;
    if (schmal) {
      var bh = document.getElementById("buehne").getBoundingClientRect().height, rest = Math.max(innerHeight - bh, 80);
      rm = "-" + Math.round(bh + rest * 0.2) + "px 0px -" + Math.round(rest * 0.45) + "px 0px";
    }
    beob = new IntersectionObserver(function (es) {
      es.forEach(function (e) { if (e.isIntersecting) schritt(+e.target.closest("[data-schritt]").getAttribute("data-schritt")); });
    }, { rootMargin: rm });
    // Handy: der Titel der Frage löst aus, nicht ihr Kasten (dessen Oberkante liegt eine Zeile über dem Titel)
    document.querySelectorAll("[data-schritt]").forEach(function (f) { beob.observe(schmal ? f.querySelector(".frage__titel, h1") || f : f); });
  }
  window.addEventListener("resize", function () { clearTimeout(beobZeit); beobZeit = setTimeout(beobachten, 200); }, { passive: true });

  // ---------- Vergleich der Gebiete
  var sortierung = "nr", liste = document.getElementById("j-liste"), zeilen = {};
  Object.keys(STAT.raum).sort(function (a, b) { return a - b; }).forEach(function (nr) {
    var li = el("li"), b = el("button", "j-zeile"); b.type = "button"; b.setAttribute("aria-pressed", "false");
    b.appendChild(el("span", "j-zeile__nr", nr)); b.appendChild(el("span", "j-zeile__name", T.name(nr)));
    var sch = el("span", "j-schicht j-zeile__schicht"); sch.setAttribute("aria-hidden", "true"); schicht(sch, STAT.raum[nr]); b.appendChild(sch);
    b.appendChild(el("span", "nur-sr j-zeile__spanne")); b.appendChild(el("span", "j-zeile__wert"));
    b.addEventListener("click", function () { waehle(S.nr === nr ? "" : nr); });
    li.appendChild(b); liste.appendChild(li); zeilen[nr] = { li: li, b: b };
  });
  document.querySelectorAll('input[name="sortierung"]').forEach(function (r) { r.addEventListener("change", function () { sortierung = r.value; listeZeigen(); }); });
  function listeZeigen() {
    var nrs = Object.keys(zeilen);
    nrs.forEach(function (nr) {
      var r = STAT.raum[nr], p = anteil(r, S.von, S.bis), w = zeilen[nr].b.querySelector(".j-zeile__wert");
      w.textContent = r.gk < MINDEST ? "wenige" : pz(p); w.title = r.gk < MINDEST ? "Weniger als " + MINDEST + " Gebäude mit bekannter Bauzeit, kein Vergleichswert" : "";
      zeilen[nr].b.querySelector(".j-zeile__spanne").textContent = ", " + spanneName(S.von, S.bis) + ":";
      zeilen[nr].b.setAttribute("aria-pressed", S.nr === nr ? "true" : "false");
    });
    if (sortierung === "anteil") nrs.sort(function (a, b) {
      var ra = STAT.raum[a], rb = STAT.raum[b], pa = ra.gk < MINDEST ? -1 : anteil(ra, S.von, S.bis), pb = rb.gk < MINDEST ? -1 : anteil(rb, S.von, S.bis);
      return pb - pa || a - b;
    }); else nrs.sort(function (a, b) { return a - b; });
    nrs.forEach(function (nr) { liste.appendChild(zeilen[nr].li); });
    steckbrief();
  }
  function steckbrief() {
    var r = S.nr ? STAT.raum[S.nr] : STAT.stadt, tb = document.querySelector("#j-sb-tabelle tbody");
    document.getElementById("j-sb-name").textContent = S.nr ? S.nr + " " + T.name(S.nr) : "Potsdam";
    document.getElementById("j-sb-art").textContent = S.nr ? RAUM.einzahl + ", Bezirk " + T.TEIL[S.nr].properties.bezirk : "Ganze Stadt";
    document.getElementById("j-sb-g").textContent = "Rund " + rund(r.g) + " Gebäude mit Wohnraum in " + fmt.format(r.z) + " Zellen";
    tb.innerHTML = "";
    KL.forEach(function (n, k) {
      var tr = el("tr"), th = el("th"), i = el("i", "j-punkt"); th.scope = "row"; i.style.background = PALETTE[k]; i.setAttribute("aria-hidden", "true");
      th.appendChild(i); th.appendChild(document.createTextNode(n));
      if (S.ansicht === "spanne" && k >= S.von && k <= S.bis) tr.className = "ist-gewaehlt";
      tr.appendChild(th); tr.appendChild(el("td", null, rund(anzahl(r, k, k)))); tr.appendChild(el("td", null, pz(anteil(r, k, k)))); tb.appendChild(tr);
    });
    var ohne = r.g - r.gk;
    document.getElementById("j-sb-hinweis").textContent = "Genähert: Anteile je Zelle mit ihrer Gebäudezahl gewichtet und auf alle Gebäude hochgerechnet; Zahlen gerundet. " +
      (ohne > 0 ? "Rund " + rund(ohne) + " Gebäude stehen in Zellen mit geheim gehaltenen Klassen und gehen nur in die Gesamtzahl ein. " : "") +
      (r.gk < MINDEST ? "Weniger als " + MINDEST + " Gebäude mit bekannter Bauzeit: Die Anteile sind sehr unsicher. " : "Die Geheimhaltung verändert kleine Werte; Summen über viele Zellen sind deshalb nur ungefähr. ") +
      QUELLE_KURZ + ", " + D.beschriftung.charAt(0).toLowerCase() + D.beschriftung.slice(1) + ".";
    document.getElementById("j-sb-karte").querySelector(".knopf__text").textContent = S.nr ? "Auf der Karte zeigen" : "Ganz Potsdam auf der Karte";
  }
  var gewaehlt = "";
  function waehle(nr) {
    if (gewaehlt) map.setFeatureState({ source: "teile", id: gewaehlt }, { gewaehlt: false });
    gewaehlt = S.nr = nr || "";
    if (gewaehlt) map.setFeatureState({ source: "teile", id: gewaehlt }, { gewaehlt: true });
    listeZeigen(); leisteZeigen(); hashSchreiben();
  }
  document.getElementById("j-sb-karte").addEventListener("click", function () {
    var ziel = document.getElementById("frage-7");
    ziel.scrollIntoView({ behavior: RUHIG ? "auto" : "smooth", block: "start" });
    kamera(S.nr ? huelle([S.nr]) : T.GANZ, S.d3);
  });

  map.on("load", function () {
    map.addImage("j-schraffur", muster("schraffur")); map.addImage("j-punkte", muster("punkte"));
    // Quellenbox eingeklappt wie in atlas.js/karte.js (Knopf „i“ öffnet sie; Quellen stehen auch in Legende und Fuß)
    var att = document.querySelector("#karte .maplibregl-ctrl-attrib"); if (att) att.classList.remove("maplibregl-compact-show");
    bereit = true;
    if (S.d3) map.jumpTo({ pitch: 50 });
    if (S.nr) { gewaehlt = S.nr; map.setFeatureState({ source: "teile", id: S.nr }, { gewaehlt: true }); }
    anwenden();
    beobachten();
    window.KIEZ_JAHRE = { S: S, schritt: schritt, anwenden: anwenden, map: map };
    window.KIEZ_BEREIT = true;
  });
}

// =====================================================================================
// Seite „Methode“: nur Zahlen aus der Datei
// =====================================================================================
function methode() {
  var tb = document.querySelector("#j-m-klassen tbody"); if (!tb) return;
  KL.forEach(function (n, k) {
    var tr = el("tr"), th = el("th"), i = el("i", "j-punkt"); th.scope = "row"; i.style.background = PALETTE[k]; i.setAttribute("aria-hidden", "true");
    th.appendChild(i); th.appendChild(document.createTextNode(n));
    tr.appendChild(th); tr.appendChild(el("td", null, pz(anteil(STAT.stadt, k, k)))); tr.appendChild(el("td", null, rund(anzahl(STAT.stadt, k, k)))); tb.appendChild(tr);
  });
}

// =====================================================================================
// Seite „Daten“: Dateien entstehen im Browser aus jahre_zellen.js (+ zellen.js), ohne Netz
// =====================================================================================
function daten() {
  var q = D.quellen[Object.keys(D.quellen)[0]], tag = D.stand;
  var spalten = KL.map(function (n) { return "anteil_" + slug(n); });
  setze("spalten", spalten.join(", "));
  function csvWert(v) { if (v == null) return ""; var s = String(v); return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s; }
  function speichern(name, typ, text) {
    var blob = new Blob([text], { type: typ }), a = document.createElement("a");
    a.href = URL.createObjectURL(blob); a.download = name; document.body.appendChild(a); a.click();
    setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 1000);
    var m = document.getElementById("j-d-status"); if (m) m.textContent = name + " gespeichert (" + fmt.format(Math.round(blob.size / 1024)) + " KB).";
  }
  function zelle(i) {
    var a = A[i], o = { gitter_id: Z.features[i].properties.id, stadtteil: Z.features[i].properties.st, gebaeude: G[i] };
    spalten.forEach(function (s, k) { o[s] = a ? a[k] : null; });
    o.vorherrschend = V[i] == null ? null : KL[V[i]]; o.klassen_geheim = G[i] != null && !a ? 1 : 0;
    return o;
  }
  var knoepfe = {
    "j-d-zellen-csv": function () {
      var kopf = ["gitter_id", "stadtteil", "gebaeude"].concat(spalten, ["vorherrschend", "klassen_geheim"]), z = [kopf.join(",")];
      for (var i = 0; i < N; i++) { if (G[i] == null) continue; var o = zelle(i); z.push(kopf.map(function (k) { return csvWert(o[k]); }).join(",")); }
      speichern("kiezatlas-bauzeiten-zellen-" + tag + ".csv", "text/csv;charset=utf-8", z.join("\n") + "\n");
    },
    "j-d-zellen-geojson": function () {
      var fc = { type: "FeatureCollection", name: "kiezatlas_bauzeiten_zellen", beschriftung: D.beschriftung, stand: D.stand, quelle: q.quelle, lizenz: q.lizenz, vermerk: q.vermerk, lizenztext: "https://www.govdata.de/dl-de/by-2-0", features: [] };
      for (var i = 0; i < N; i++) { if (G[i] == null) continue; fc.features.push({ type: "Feature", geometry: Z.features[i].geometry, properties: zelle(i) }); }
      speichern("kiezatlas-bauzeiten-zellen-" + tag + ".geojson", "application/geo+json", JSON.stringify(fc));
    },
    "j-d-raum-csv": function () {
      var kopf = ["nr", "name", "gebaeude_rund", "zellen", "gebaeude_ohne_klassen_rund"].concat(spalten, ["vergleichbar"]), z = [kopf.join(",")];
      Object.keys(STAT.raum).sort(function (a, b) { return a - b; }).forEach(function (nr) {
        var r = STAT.raum[nr], o = { nr: nr, name: T.name(nr), gebaeude_rund: Math.round(r.g / 10) * 10, zellen: r.z, gebaeude_ohne_klassen_rund: Math.round((r.g - r.gk) / 10) * 10, vergleichbar: r.gk >= MINDEST ? 1 : 0 };
        spalten.forEach(function (s, k) { var p = anteil(r, k, k); o[s] = p == null ? null : Math.round(p); });
        z.push(kopf.map(function (k) { return csvWert(o[k]); }).join(","));
      });
      speichern("kiezatlas-bauzeiten-" + RAUM.id + "-" + tag + ".csv", "text/csv;charset=utf-8", z.join("\n") + "\n");
    },
    "j-d-liesmich": function () {
      var t = ["Kiezatlas Potsdam: Bauzeiten, Stand " + D.stand, "",
        D.beschriftung + ".", "", "Quelle: " + q.quelle, "Lizenz: " + q.lizenz + ", Lizenztext https://www.govdata.de/dl-de/by-2-0",
        "Namensnennung bei Weitergabe: " + q.vermerk, "", "Hinweise:", D.hinweis, "",
        "Spalten anteil_*: Prozent an der Summe der Klassen der Zelle, auf 0,1 gerundet; leer = alle Klassen geheim gehalten.",
        "vorherrschend: Klasse mit den meisten Gebäuden; leer bei Gleichstand oder geheimen Klassen.",
        "Datei je " + RAUM.einzahl + ": Anteile genähert (Zellanteile mit der Gebäudezahl gewichtet), ganze Prozent; Gebäudezahlen auf 10 gerundet;",
        "vergleichbar = 0 heißt weniger als " + MINDEST + " Gebäude mit bekannter Bauzeit.",
        "Keine Daten aus OpenStreetMap, keine Adressen, keine Angaben zu einzelnen Gebäuden.", "Koordinaten der GeoJSON-Datei: WGS 84 (EPSG:4326). GeoPackage (bauzeiten.gpkg): ETRS89 / UTM Zone 33N (EPSG:25833), gleiche Werte, Tabelle hinweis mit Quelle und Lizenz."];
      speichern("LIESMICH-kiezatlas-bauzeiten.txt", "text/plain;charset=utf-8", t.join("\n") + "\n");
    }
  };
  Object.keys(knoepfe).forEach(function (id) { var b = document.getElementById(id); if (b) { b.disabled = false; b.addEventListener("click", knoepfe[id]); } });
}
})();
