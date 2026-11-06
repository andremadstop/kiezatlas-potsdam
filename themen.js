/* Kiezatlas Potsdam: gemeinsamer Themenkern aller Seiten (Vertrag: daten/schema/themen.md).
   Zeichnet nichts. Nachladen nur per <script>, nie per fetch (file://). name() braucht KIEZ_KENNZAHLEN. */
(function () {
"use strict";
var ST = window.KIEZ_STADTTEILE, Z = window.KIEZ_ZELLEN, NB = "\u00a0";
var fmt = new Intl.NumberFormat("de-DE"), fmt1 = new Intl.NumberFormat("de-DE", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
function rundEw(v) { return fmt.format(v >= 1000 ? Math.round(v / 100) * 100 : Math.round(v / 10) * 10); }
function proz(v) { return v == null ? "k. A." : fmt1.format(v) + NB + "%"; }
function name(nr) { return nr ? window.KIEZ_KENNZAHLEN.stadtteile[nr].name : "Potsdam"; }
function kachel(G, id) { return (G.kacheln || []).filter(function (k) { return k.id === id; })[0]; }
function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }

// ---------- Themen in Chip-Reihenfolge; h = Hash-Schlüssel, bleibt stabil
var THEMEN = [
  { id: "stadtteile", h: "stadtteile", kurz: "Stadtteile", name: "Stadtteile" },
  { id: "ew", h: "ew", kurz: "Einwohner", name: "Einwohner je Zelle", einheit: "Personen", quelle: "Zensus 2022, Bevölkerungszahl" },
  { id: "d_alter", h: "alter", kurz: "Alter", name: "Durchschnittsalter", einheit: "Jahre", nenner: "a_ges", quelle: "Zensus 2022, Durchschnittsalter" },
  { id: "q_u18", h: "u18", kurz: "unter 18", name: "Anteil unter 18 Jahre", einheit: "%", nenner: "a_ges", quelle: "Zensus 2022, Alter in 5 Altersklassen" },
  { id: "q_65p", h: "65p", kurz: "65 und älter", name: "Anteil 65 Jahre und älter", einheit: "%", nenner: "a_ges", quelle: "Zensus 2022, Alter in 5 Altersklassen" },
  { id: "q_v1949", h: "vor1949", kurz: "vor 1949", name: "Wohnungen in Gebäuden vor 1949", einheit: "%", nenner: "w_ges", quelle: "Zensus 2022, Baujahresklassen" },
  { id: "q_fern", h: "fern", kurz: "Fernwärme", name: "Wohnungen mit Fernwärme", einheit: "%", nenner: "w_ges", quelle: "Zensus 2022, Energieträger der Heizung" }
];
var THEMA = {}, HASH = {};
function aufnehmen(t) { THEMA[t.id] = t; if (t.h) HASH[t.h] = t.id; }
THEMEN.forEach(aufnehmen);

// ---------- Farben und Klassen
var STUFEN = ["--k1", "--k2", "--k3", "--k4", "--k5"].map(function (v) { return getComputedStyle(document.documentElement).getPropertyValue(v).trim(); });
var GRAU = "#d5d8d3";
// Prozent: feste Grenzen; sonst Quintile über die Werte, doppelte Grenzen entfallen
function klassen(t, features) {
  if (t.einheit === "%") return { grenzen: [20, 40, 60, 80], min: 0, max: 100, fest: true };
  var w = (features || (Z ? Z.features : [])).map(function (f) { return f.properties[t.id]; })
    .filter(function (v) { return v != null && !isNaN(v); }).sort(function (a, b) { return a - b; });
  var g = [];
  [0.2, 0.4, 0.6, 0.8].map(function (p) { return w[Math.min(w.length - 1, Math.floor(p * w.length))]; })
    .forEach(function (v) { if (!g.length || v > g[g.length - 1]) g.push(v); });
  return w.length ? { grenzen: g, min: w[0], max: w[w.length - 1] } : { grenzen: [], min: 0, max: 0, leer: true };
}
var KLASSEN = {};
if (Z) THEMEN.slice(1).forEach(function (t) { KLASSEN[t.id] = klassen(t); });
// ohne Werte (Ebene noch nicht eingemischt): einfarbig, nicht gemerkt
function kl(t, k) { if (k || KLASSEN[t.id]) return k || KLASSEN[t.id]; var s = klassen(t); if (!s.leer) KLASSEN[t.id] = s; return s; }
function klasse(t, v, k) { var s = kl(t, k), i = 0; while (i < s.grenzen.length && v >= s.grenzen[i]) i++; return Math.min(i, 4); }
function unscharf(t, p) { return t.nenner ? (p[t.nenner] == null || p[t.nenner] < 10) : false; }
function farbe(t, k) {
  var s = kl(t, k), e = ["step", ["get", t.id], STUFEN[0]];
  s.grenzen.forEach(function (g, i) { e.push(g, STUFEN[Math.min(i + 1, 4)]); });
  if (!s.grenzen.length) e = STUFEN[0];
  return t.nenner ? ["case", ["<", ["coalesce", ["get", t.nenner], 0], 10], GRAU, e] : e;
}
// opt: faktor (Standard 1), hoch (1100 m), klassen
function hoehe(t, opt) {
  opt = opt || {};
  var v = ["get", t.id], s = kl(t, opt.klassen), H0 = opt.hoch || 1100, f = opt.faktor == null ? 1 : opt.faktor, rel;
  if (t.id === "ew") rel = ["sqrt", ["/", v, s.max || 1]];
  else if (t.einheit === "%") rel = ["/", ["min", 100, v], 100];
  else rel = ["max", 0, ["/", ["-", v, s.min], s.max - s.min || 1]];
  var flach = t.nenner ? ["<", ["coalesce", ["get", t.nenner], 0], 10] : false;
  function bei(H) { var h = ["*", f * H, rel]; return flach ? ["case", flach, 3, h] : h; }
  return ["interpolate", ["linear"], ["zoom"], 10, bei(H0 * 1.3), 12, bei(H0 * 0.45), 13, bei(H0 * 0.18), 14, bei(H0 * 0.075), 16, bei(H0 * 0.03)];
}

// ---------- Geometrie
function polys(f) { return f.geometry.type === "Polygon" ? [f.geometry.coordinates] : f.geometry.coordinates; }
function umriss(f) { var a = [180, 90, -180, -90]; polys(f).forEach(function (p) { p[0].forEach(function (c) { a[0] = Math.min(a[0], c[0]); a[1] = Math.min(a[1], c[1]); a[2] = Math.max(a[2], c[0]); a[3] = Math.max(a[3], c[1]); }); }); return [[a[0], a[1]], [a[2], a[3]]]; }

// ---------- Stadtteile: ein Farbton je Bezirk, heller und dunkler je Stadtteil
var TOENE = { 1: 28, 2: 205, 3: 150, 4: 350, 5: 265, 6: 95, 7: 185, 8: 45 };
var proBezirk = {}, FARBE = {}, BEZIRKFARBE = {}, TEIL = {}, GANZ = null;
if (ST) {
  ST.features.forEach(function (f) { var b = f.properties.bezirk; (proBezirk[b] = proBezirk[b] || []).push(f.properties.nr); TEIL[f.properties.nr] = f; });
  ST.features.forEach(function (f) {
    var b = f.properties.bezirk, l = proBezirk[b], i = l.indexOf(f.properties.nr), n = l.length;
    FARBE[f.properties.nr] = "hsl(" + TOENE[b] + ",30%," + (n > 1 ? 72 - 28 * i / (n - 1) : 58).toFixed(0) + "%)";
    BEZIRKFARBE[b] = "hsl(" + TOENE[b] + ",30%,52%)";
    f.properties.farbe = FARBE[f.properties.nr];
  });
  GANZ = (function () { var a = [180, 90, -180, -90]; ST.features.forEach(function (f) { var u = umriss(f); a[0] = Math.min(a[0], u[0][0]); a[1] = Math.min(a[1], u[0][1]); a[2] = Math.max(a[2], u[1][0]); a[3] = Math.max(a[3], u[1][1]); }); return [[a[0], a[1]], [a[2], a[3]]]; })();
}

// ---------- Nachladen; gleichzeitige Aufrufe für dieselbe Datei laden einmal
var wartend = {};
function melden(text) {
  var m = document.getElementById("ladestatus");
  if (!m) { m = document.createElement("p"); m.id = "ladestatus"; m.className = "nur-sr"; m.setAttribute("aria-live", "polite"); document.body.appendChild(m); }
  m.textContent = text;
}
// Cache-Busting: Die Deploy-Kopie (skripte/deploy_kopie.py) setzt window.KIEZ_V; dann hängt jede nachgeladene
// Datei ?v=<Stand> an. Im Repo und per file:// bleibt KIEZ_V leer, die Pfade bleiben unverändert.
function v(src) { return window.KIEZ_V && src.indexOf("?") < 0 ? src + "?v=" + window.KIEZ_V : src; }
function laden(src, global, fertig) {
  var w = src + " " + global;
  if (window[global] != null) { fertig(window[global]); return; }
  if (wartend[w]) { wartend[w].push(fertig); return; }
  var l = wartend[w] = [fertig], s = document.createElement("script");
  function ende(wert) { delete wartend[w]; l.forEach(function (f) { f(wert); }); }
  s.src = v(src); s.async = true;
  s.onload = function () { var d = window[global]; if (d == null) melden("Daten aus " + src + " sind unvollständig."); ende(d == null ? null : d); };
  s.onerror = function () { melden("Daten aus " + src + " ließen sich nicht laden."); ende(null); };
  document.head.appendChild(s);
}

// ---------- Ebenen-Register
var EBENEN = [], EBENE = {};
var ebenen = {
  registrieren: function (e) {
    if (EBENE[e.id]) return EBENE[e.id];
    EBENE[e.id] = e; EBENEN.push(e);
    // vergebene id oder h bleiben beim alten Thema (geteilte Links)
    (e.themen || []).forEach(function (t) { if (THEMA[t.id] || HASH[t.h]) return; t.ebene = e.id; THEMEN.push(t); aufnehmen(t); });
    return e;
  },
  liste: function () { return EBENEN.slice(); },
  // art: Schlüssel in werte (erreichbar: kita …) oder Liste oben (jahre_zellen: gebaeude …)
  zellwerte: function (id, art) {
    var e = EBENE[id], d = e && window[e.global], f = Z ? Z.features : [];
    var l = d && (d.werte && d.werte[art] || d[art]);
    var ok = Array.isArray(l) && d.anzahl === f.length && l.length === f.length &&
      f.length && d.erste_id === f[0].properties.id && d.letzte_id === f[f.length - 1].properties.id;
    if (!ok) { melden("Die Werte der Ebene " + id + " passen nicht zu den Zellen der Karte."); return null; }
    return l;
  }
};

window.KIEZ_THEMEN = {
  THEMEN: THEMEN, THEMA: THEMA, HASH: HASH,
  STUFEN: STUFEN, GRAU: GRAU,
  KLASSEN: KLASSEN, klassen: klassen, klasse: klasse,
  farbe: farbe, hoehe: hoehe, unscharf: unscharf,
  polys: polys, umriss: umriss, GANZ: GANZ,
  TEIL: TEIL, FARBE: FARBE, BEZIRKFARBE: BEZIRKFARBE, proBezirk: proBezirk,
  fmt: fmt, fmt1: fmt1, rundEw: rundEw, proz: proz, name: name, kachel: kachel, esc: esc,
  ebenen: ebenen, laden: laden, v: v
};
})();
