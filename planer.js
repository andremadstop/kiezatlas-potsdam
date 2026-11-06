/* Kiezatlas Potsdam: Planer-Seite (planer.html) und Methode (planer-methode.html).
   Daten nur per <script> (KIEZ_THEMEN.laden), nie per fetch (file://). Datenordner steht in <html data-daten>
   ("daten/"); mit planer.html?daten=fixtures zeigt die Seite die Beispieldateien aus daten/fixtures/ (Prüfung).
   <html data-odbl> nennt die veröffentlichten _odbl-Dateien; fehlt eine, sind Fußweg bzw. OSM-Arten gesperrt
   statt eine fehlende Datei anzufragen. Zustand im Hash, z. B.
   planer.html#ein=kita,gs&zu=kita&weg=luft&raum=pr&r=403&k=12.00/52.40000/13.06000/0/0
   Keine Kamerabewegung von selbst; Klicks in die Karte bewegen die Kamera nie. */
(function () {
"use strict";
var T = window.KIEZ_THEMEN, ST = window.KIEZ_STADTTEILE, PR = window.KIEZ_PLANUNGSRAEUME, NB = " ";
var FIXTURE = /(?:^|&)daten=fixtures(?:&|$)/.test(location.search.replace(/^\?/, ""));
var WURZEL = FIXTURE ? "daten/fixtures/" : document.documentElement.getAttribute("data-daten") || "daten/";
var ODBL = document.documentElement.getAttribute("data-odbl");   // null = keine Angabe: alle vorhanden
var SEITE = document.body.getAttribute("data-seite");
var fmt = T.fmt, fmt1 = T.fmt1, esc = T.esc, zahl2 = new Intl.NumberFormat("de-DE", { maximumFractionDigits: 2 });
var DLDE = "https://www.govdata.de/dl-de/by-2-0";
function el(t, c, x) { var e = document.createElement(t); if (c) e.className = c; if (x != null) e.textContent = x; return e; }
function $(id) { return document.getElementById(id); }

// ---------- Dateien (Verträge in daten/schema/); zellen.js ist Bestand und liegt immer unter daten/
var DATEI = {
  planer: { src: "planer.js", global: "KIEZ_PLANER" },
  planer_fuss: { src: "planer_fuss_odbl.js", global: "KIEZ_PLANER_FUSS", odbl: true },
  ein: { src: "einrichtungen.js", global: "KIEZ_EINRICHTUNGEN" },
  ein_odbl: { src: "einrichtungen_odbl.js", global: "KIEZ_EINRICHTUNGEN_ODBL", odbl: true },
  erreichbar: { src: "erreichbar.js", global: "KIEZ_ERREICHBAR" },
  erreichbar_fuss: { src: "erreichbar_fuss_odbl.js", global: "KIEZ_ERREICHBAR_FUSS", odbl: true },
  zellen: { src: "daten/zellen.js", global: "KIEZ_ZELLEN", bestand: true }
};
// Veröffentlicht? Dateien ohne ODbL immer; _odbl-Dateien nur, wenn <html data-odbl> sie nennt (oder Fixtures)
function da(n) { var d = DATEI[n]; return !d.odbl || FIXTURE || ODBL === null || ODBL.split(/[\s,]+/).indexOf(d.src) > -1; }
var FUSS_DA = da("erreichbar_fuss") && da("planer_fuss"), OSM_DA = da("ein_odbl");
function erlaubt(a) { return OSM_DA || !ART[a] || ART[a].g !== "versorgung"; }   // OSM-Arten nur mit einrichtungen_odbl.js
var beispielGesehen = false;
function holen(n, fertig) {
  var d = DATEI[n];
  T.laden(d.bestand ? d.src : WURZEL + d.src, d.global, function (x) {
    if (x && x.fixture && !beispielGesehen) { beispielGesehen = true; var b = $("beispiel"); if (b) b.hidden = false; }
    fertig(x);
  });
}

// ---------- Vermerke: Links im Vermerk anklickbar, dl-de mit Link zum Lizenztext
function vermerkKnoten(text) {
  var span = el("span"), teile = String(text).split(/(https?:\/\/[^\s),]+)/);
  teile.forEach(function (t, i) {
    if (i % 2) { var a = el("a", "link", t.indexOf("govdata.de/dl-de") > -1 || t.indexOf("opendatacommons") > -1 ? "Lizenztext" : t); a.href = t; span.appendChild(a); }
    else if (t) span.appendChild(document.createTextNode(t));
  });
  return span;
}
function vermerkHtml(text) { return vermerkKnoten(text).innerHTML; }
function vermerke(quellen) { return Object.keys(quellen || {}).map(function (k) { return quellen[k].vermerk; }); }

// ---------- Arten: Kurzschlüssel im Hash bleiben stabil; Symbol = Kreis mit Form- und Graustufenunterschied
// s: [Füllung, Rand, Radius, Randbreite]
var GRUPPEN = [
  { id: "bildung", titel: "Bildung und Betreuung", datei: "ein", hinweis: "Kitas und Schulen laut MBJS. Kreise außerhalb der Stadtgrenze sind blasser; sie zählen für die Entfernungen mit." },
  { id: "gemeinbedarf", titel: "Gemeinbedarf, nur Lage", datei: "ein", hinweis: "Aus ALKIS-Gebäudefunktionen und Flächennutzung: Lage ohne Kapazität." },
  { id: "versorgung", titel: "Nahversorgung und Gesundheit", datei: "ein_odbl", hinweis: "Aus OpenStreetMap (ODbL). Nur Lage und Entfernung, keine Aussage zur Versorgung: Ärzte plant die Kassenärztliche Vereinigung auf größeren Bereichen, OSM nennt keine Kapazität." }
];
var ART = {
  kita: { h: "kita", kurz: "Kita", name: "Kindertagesstätte", g: "bildung", s: ["#13212a", "#ffffff", 5, 1.5] },
  hort: { h: "hort", kurz: "Hort", name: "Hort", g: "bildung", s: ["#5d6b72", "#ffffff", 4.5, 1.5] },
  grundschule: { h: "gs", kurz: "Grundschule", name: "Grundschule", g: "bildung", s: ["#ffffff", "#13212a", 5.5, 2.5] },
  sek1: { h: "sek1", kurz: "Sekundarstufe I", name: "Schule mit Sekundarstufe I (Oberschule, Gesamtschule)", g: "bildung", s: ["#ffffff", "#5d6b72", 5, 2] },
  gymnasium: { h: "gym", kurz: "Gymnasium", name: "Gymnasium", g: "bildung", s: ["#9aa5a9", "#13212a", 5, 1.5] },
  foerderschule: { h: "fs", kurz: "Förderschule", name: "Förderschule", g: "bildung", s: ["#cdd1cc", "#13212a", 4.5, 1.5] },
  osz: { h: "osz", kurz: "Oberstufenzentrum", name: "Oberstufenzentrum, berufliche Schule", g: "bildung", s: ["#cdd1cc", "#5d6b72", 4.5, 1] },
  sonstige_schule: { h: "ss", kurz: "andere Schule", name: "andere Schule", g: "bildung", s: ["#e6e9e4", "#5d6b72", 4, 1] },
  feuerwehr: { h: "fw", kurz: "Feuerwehr", name: "Feuerwehr", g: "gemeinbedarf", s: ["#fafbf8", "#13212a", 5, 2] },
  bibliothek: { h: "bib", kurz: "Bibliothek", name: "Bibliothek, Bücherei", g: "gemeinbedarf", s: ["#fafbf8", "#13212a", 4, 1] },
  sport: { h: "sport", kurz: "Sport", name: "Sporthalle, Sportanlage, Bad", g: "gemeinbedarf", s: ["#fafbf8", "#5d6b72", 4.5, 1.5] },
  jugendfreizeit: { h: "jug", kurz: "Jugend", name: "Jugendfreizeit", g: "gemeinbedarf", s: ["#fafbf8", "#5d6b72", 4, 2.5] },
  seniorenfreizeit: { h: "sen", kurz: "Senioren", name: "Seniorenbegegnung", g: "gemeinbedarf", s: ["#fafbf8", "#808d92", 4, 2.5] },
  buerger_vereinshaus: { h: "bh", kurz: "Bürgerhaus", name: "Bürger- und Vereinshaus", g: "gemeinbedarf", s: ["#fafbf8", "#808d92", 5, 1] },
  sonstiger_gemeinbedarf: { h: "gb", kurz: "anderer Gemeinbedarf", name: "Gebäude für soziale, kulturelle oder öffentliche Zwecke", g: "gemeinbedarf", s: ["#fafbf8", "#9aa5a9", 3.5, 1] },
  arzt: { h: "arzt", kurz: "Arzt", name: "Arztpraxis", g: "versorgung", s: ["#13212a", "#fafbf8", 3.5, 1] },
  apotheke: { h: "apo", kurz: "Apotheke", name: "Apotheke", g: "versorgung", s: ["#5d6b72", "#fafbf8", 3.5, 1] },
  supermarkt: { h: "markt", kurz: "Lebensmittel", name: "Lebensmittelmarkt", g: "versorgung", s: ["#9aa5a9", "#13212a", 4, 1] },
  pflege: { h: "pflege", kurz: "Pflege", name: "Pflegeeinrichtung", g: "versorgung", s: ["#ffffff", "#5d6b72", 4, 1.5] },
  spielplatz: { h: "spiel", kurz: "Spielplatz", name: "Spielplatz", g: "versorgung", s: ["#cdd1cc", "#5d6b72", 3.5, 1] },
  gruen: { h: "gruen", kurz: "Grün", name: "öffentliche Grünfläche", g: "flaeche" }
};
var CODE = {};
Object.keys(ART).forEach(function (a) { CODE[ART[a].h] = a; });
function art(a) {
  if (!ART[a]) { ART[a] = { h: a, kurz: a.replace(/_/g, " "), name: a.replace(/_/g, " "), g: "bildung", s: ["#e6e9e4", "#13212a", 4, 1] }; CODE[a] = a; }
  return ART[a];
}
function wort(s) { return s == null ? "" : String(s).replace(/_/g, " "); }

// ---------- Kennzahlen lesbar machen
var KENNZAHL = {
  anteil_in_radius: function (w) { return "Anteil " + (w.zielgruppe || "der Einwohner") + " mit " + art(w.art).kurz + (w.richtwert ? " in " + zahl(w.richtwert.wert) + NB + w.richtwert.einheit : " in der Nähe"); },
  ew_je_einrichtung: function (w) { return "Einwohner je " + art(w.art).kurz; },
  plaetze_je_kind: function (w) { return "Plätze je Kind, " + art(w.art).kurz + (w.zielgruppe ? " (" + w.zielgruppe + ")" : ""); },
  plaetze_je_bedarf: function () { return "Plätze je Bedarfsplatz (Krippe, Kindergarten, Hort)"; },
  schueler_je_kind: function (w) { return "Grundschüler je Kind" + (w.zielgruppe ? " (" + w.zielgruppe + ")" : ""); },
  oepnv_erschliessung: function () { return "ÖPNV-Erschließung nach Nahverkehrsplan"; },
  oepnv_takt: function () { return "ÖPNV-Erschließung mit Soll-Takt"; },
  gruen_m2_je_ew: function () { return "Grünfläche je Einwohner"; }
};
function kennzahlText(w) { return KENNZAHL[w.kennzahl] ? KENNZAHL[w.kennzahl](w) : wort(w.kennzahl) + ", " + art(w.art).kurz; }
// Gleiche Kennzahl in Raumeinheit und gesamt (ganz Potsdam): Kennzahl, Art, Maßstab
function wertSchluessel(w) { return [w.kennzahl, w.art, w.richtwert ? w.richtwert.wert : "-"].join("|"); }
// „826 von 1.354“ mit Bedeutung von Zähler und Nenner (Audit K14); Personen und Bedarf sind laut Datei gerundet
function znKurz(w) { return w.zaehler == null || w.nenner == null ? "" : fmt.format(w.zaehler) + " von " + fmt.format(w.nenner); }
function znText(w) {
  if (!znKurz(w)) return "";
  return znKurz(w) + " (Zähler: " + (w.zaehler_text || "") + "; Nenner: " + (w.nenner_text || "") + ")";
}
function differenzText(w) {
  if (w.differenz == null) return "";
  return w.differenz < 0 ? "Rechnerisch fehlen " + fmt.format(-w.differenz) + " Plätze zum Bedarf." :
    "Rechnerisch " + fmt.format(w.differenz) + " Plätze mehr als der Bedarf.";
}
function zahl(v) { return v == null ? "k. A." : (Math.abs(v) < 10 && v % 1 ? zahl2 : fmt1).format(v).replace(/,0$/, ""); }
var METHODE = { luftlinie: "Luftlinie", fussweg: "Fußweg" };
// Flächenquoten je Raumeinheit haben keinen Entfernungsbezug: dort kein Etikett zur Messart
var OHNE_WEG = { plaetze_je_kind: 1, plaetze_je_bedarf: 1, schueler_je_kind: 1, ew_je_einrichtung: 1 };
function wegText(w) { return OHNE_WEG[w.kennzahl] ? "" : (METHODE[w.methode] || w.methode); }
// Status: amtlich mit Richtwert = amtlicher Maßstab; amtlich ohne Richtwert = nur amtliche Daten
function statusText(w) { return w.status === "orientierung" ? "Orientierung, kein Richtwert" : w.richtwert ? "amtlicher Maßstab" : "amtliche Daten, kein Maßstab"; }
function statusKlasse(w) { return w.status === "orientierung" ? "orientierung" : w.richtwert ? "amtlich" : "daten"; }
var NUR_LAGE = { arzt: 1, apotheke: 1, pflege: 1, spielplatz: 1, supermarkt: 1 };

if (SEITE === "methode") { methode(); return; }
if (SEITE !== "karte") return;

// ======================================================================= Planer-Karte
var RUHIG = matchMedia("(prefers-reduced-motion: reduce)").matches, SCHMAL = matchMedia("(max-width:860px)").matches;
var KL_M = { grenzen: [300, 500, 1000, 2000], min: 0, max: 3000 }, KL_MIN = { grenzen: [5, 10, 15, 20], min: 0, max: 30 };
var ZU_START = ["kita", "hort", "grundschule", "gruen"];

// ---------- Zustand aus dem Hash
// Raumebene: Planungsräume, sobald ihre Grenzen da sind (daten/planungsraeume.js); die Beispieldaten rechnen auf Stadtteilen
var S = { ein: ["kita", "grundschule"], zu: "", weg: "luft", raum: PR && !FIXTURE ? "pr" : "st", r: "", kam: null };
(function () {
  var h = {};
  function dek(x) { try { return decodeURIComponent(x); } catch (e) { return ""; } }   // verstümmelte Links nicht tödlich
  location.hash.replace(/^#/, "").split("&").forEach(function (p) { var kv = p.split("="); if (kv[0]) h[dek(kv[0])] = dek(kv[1] || ""); });
  // nur bekannte Kurzschlüssel; Fremdes aus einem Link legt keine Arten an
  if ("ein" in h) S.ein = h.ein ? h.ein.split(",").map(function (c) { return CODE[c]; }).filter(function (a, i, l) { return a && l.indexOf(a) === i; }) : [];
  if (h.zu && CODE[h.zu]) S.zu = CODE[h.zu];
  if (h.weg === "fuss" && FUSS_DA) S.weg = "fuss";
  S.ein = S.ein.filter(erlaubt);
  if (h.raum === "st" || (h.raum === "pr" && PR)) S.raum = h.raum;
  if (h.r) S.r = h.r;
  if (h.k) { var k = h.k.split("/").map(Number); if (k.length >= 3 && k.every(function (x) { return !isNaN(x); }) && k[0] >= 0 && k[0] <= 22 && Math.abs(k[1]) <= 85 && Math.abs(k[2]) <= 180) S.kam = { zoom: k[0], center: [k[2], k[1]], pitch: k[3] || 0, bearing: k[4] || 0 }; }
})();
var bereitKarte = false;
function hashSchreiben() {
  if (!bereitKarte) return;
  var c = map.getCenter(), teile = ["ein=" + S.ein.map(function (a) { return art(a).h; }).join(",")];
  if (S.zu) teile.push("zu=" + art(S.zu).h);
  teile.push("weg=" + S.weg, "raum=" + S.raum);
  if (S.r) teile.push("r=" + S.r);
  teile.push("k=" + [map.getZoom().toFixed(2), c.lat.toFixed(5), c.lng.toFixed(5), Math.round(map.getPitch()), Math.round(map.getBearing())].join("/"));
  try { history.replaceState(null, "", "#" + teile.join("&")); } catch (e) { /* file:// in manchen Browsern */ }
}

// ---------- Raumeinheiten: Planungsräume (H1, Ebene der Kita- und Schulentwicklungsplanung) und Stadtteile
// datei = Wert von raumebene in planer.js; nur wenn er zur gewählten Ebene passt, zeigt die Seite die Tabelle
var RAUMEBENE = {
  pr: { name: "Planungsräume", einzahl: "Planungsraum", datei: "planungsraum", fc: PR,
    att: 'Planungsräume © Landeshauptstadt Potsdam, <a href="' + DLDE + '">dl-de/by-2-0</a>, Daten verändert' },
  st: { name: "Stadtteile", einzahl: "Stadtteil", datei: "stadtteil", fc: ST, att: "Stadtteile © Landeshauptstadt Potsdam, dl-zero-de/2.0" }
};
var RAUMEBENE_DATEI = { stadtteil: "Stadtteilen", planungsraum: "Planungsräumen" };
var RAUM = {};
function raumIndex() { RAUM = {}; RAUMEBENE[S.raum].fc.features.forEach(function (f) { RAUM[f.properties.nr] = f; }); }
raumIndex();
if (!RAUM[S.r]) S.r = "";

// ---------- Karte
var LEER = { type: "FeatureCollection", features: [] };
var start = S.kam ? { center: S.kam.center, zoom: S.kam.zoom, pitch: S.kam.pitch, bearing: S.kam.bearing } : { bounds: T.GANZ, fitBoundsOptions: { padding: SCHMAL ? 16 : 40 } };
var map = new maplibregl.Map(Object.assign({
  container: "karte",
  style: T.grundkarte({ version: 8, sources: {
      basemap: { type: "raster", tileSize: 256, maxzoom: 18, tiles: ["https://sgx.geodatenzentrum.de/wmts_basemapde/tile/1.0.0/de_basemapde_web_raster_grau/default/GLOBAL_WEBMERCATOR/{z}/{y}/{x}.png"],
        attribution: 'Hintergrund © <a href="https://www.bkg.bund.de">GeoBasis-DE / BKG</a> (2026) <a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>' },
      zellen: { type: "geojson", data: LEER },
      raum: { type: "geojson", data: RAUMEBENE[S.raum].fc, promoteId: "nr", attribution: RAUMEBENE[S.raum].att },
      ein: { type: "geojson", data: LEER },
      ein_odbl: { type: "geojson", data: LEER } },
    layers: [
      { id: "papier", type: "background", paint: { "background-color": "#e6e9e4" } },
      { id: "basemap", type: "raster", source: "basemap", paint: { "raster-opacity": 0.6, "raster-saturation": -1 } },
      { id: "zellen", type: "fill", source: "zellen", layout: { visibility: "none" }, paint: { "fill-color": T.STUFEN[2], "fill-opacity": 0.82, "fill-outline-color": "rgba(255,255,255,0.3)" } },
      { id: "raum-flaeche", type: "fill", source: "raum", paint: { "fill-color": "#ffffff", "fill-opacity": ["case", ["boolean", ["feature-state", "gewaehlt"], false], 0.18, 0] } },
      { id: "raum-linie", type: "line", source: "raum", paint: { "line-color": "#13212a", "line-width": 1, "line-opacity": 0.55 } },
      { id: "raum-wahl", type: "line", source: "raum", paint: { "line-color": "#6a2c82", "line-width": ["case", ["boolean", ["feature-state", "gewaehlt"], false], 3.2, 0] } },
      { id: "ein_odbl", type: "circle", source: "ein_odbl", layout: { visibility: "none" }, paint: {} },
      { id: "ein", type: "circle", source: "ein", paint: {} }
    ] }, { vor: "ein_odbl" }),
  maxZoom: 19, maxPitch: 60, attributionControl: false, fadeDuration: RUHIG ? 0 : 300,
  locale: { "NavigationControl.ZoomIn": "Vergrößern", "NavigationControl.ZoomOut": "Verkleinern", "NavigationControl.ResetBearing": "Nach Norden ausrichten", "AttributionControl.ToggleAttribution": "Quellen ein- oder ausblenden" }
}, start));
map.addControl(new maplibregl.NavigationControl({ visualizePitch: false, showCompass: false }), "top-right");
map.addControl(new maplibregl.ScaleControl({ unit: "metric" }), "bottom-left");
window.KIEZ_KARTE = map;

// Symbole je Art als MapLibre-Ausdruck
function symbol(i, standard) {
  var e = ["match", ["get", "art"]];
  Object.keys(ART).forEach(function (a) { if (ART[a].s) e.push(a, ART[a].s[i]); });
  e.push(standard); return e;
}
function symbolFarbe() { return { "circle-color": symbol(0, "#e6e9e4"), "circle-stroke-color": symbol(1, "#13212a"), "circle-radius": ["interpolate", ["linear"], ["zoom"], 10, ["*", 0.8, symbol(2, 4)], 15, ["*", 1.5, symbol(2, 4)]],
  "circle-stroke-width": symbol(3, 1), "circle-opacity": ["case", ["==", ["get", "in_potsdam"], false], 0.5, 1], "circle-stroke-opacity": ["case", ["==", ["get", "in_potsdam"], false], 0.5, 1] }; }
function swatch(a) {
  var s = art(a).s || ["#e6e9e4", "#13212a", 4, 1], i = el("i", "zeichen"); i.setAttribute("aria-hidden", "true");
  i.style.background = s[0]; i.style.borderColor = s[1]; i.style.borderWidth = Math.max(1, Math.round(s[3])) + "px";
  i.style.width = i.style.height = Math.round(2 * s[2] + 2) + "px"; return i;
}

// ---------- Daten laden: Einrichtungen (amtlich) sofort, Versorgung erst bei der Wahl einer Raumeinheit
// (hält das Startgewicht klein, wenn die echten Dateien aus A6 kommen), alles andere bei Bedarf
var EIN = {}, ARTEN_IN = { ein: [], ein_odbl: [] }, offen = 1;
function einMerken(d, quelle) {
  (d && d.features || []).forEach(function (f) { EIN[f.properties.id] = { f: f, d: d, quelle: quelle }; if (ARTEN_IN[quelle].indexOf(f.properties.art) < 0) ARTEN_IN[quelle].push(f.properties.art); });
}
holen("ein", function (d) { einMerken(d, "ein"); fertig(); });
function fertig() { if (--offen === 0) aufbauen(); }

// ---------- Einrichtungs-Chips je Gruppe
var odblLaedt = false;
function einBauen() {
  var box = $("ein"), fokus = document.activeElement && box.contains(document.activeElement) ? document.activeElement.value : null; box.innerHTML = "";
  var osm = Object.keys(ART).filter(function (a) { return ART[a].g === "versorgung"; }).concat(ARTEN_IN.ein_odbl.filter(function (a) { return !ART[a] || ART[a].g !== "versorgung"; }));
  GRUPPEN.forEach(function (g) {
    var arten = g.id === "versorgung" ? osm.filter(function (a, i) { return osm.indexOf(a) === i; })
      : Object.keys(ART).filter(function (a) { return ART[a].g === g.id && ARTEN_IN.ein.indexOf(a) > -1; })
        .concat(ARTEN_IN.ein.filter(function (a) { return !ART[a] && g.id === "bildung"; }));
    if (!arten.length) return;
    var fs = el("fieldset", "eingruppe"); fs.appendChild(el("legend", "eingruppe__titel", g.titel));
    var reihe = el("div", "chips");
    arten.forEach(function (a) {
      var A = art(a), l = el("label", "chip chip--ein"), r = document.createElement("input");
      r.type = "checkbox"; r.value = a; r.name = "ein"; r.checked = S.ein.indexOf(a) > -1;
      var aus = !erlaubt(a); if (aus) { r.disabled = true; l.classList.add("chip--aus"); }
      l.appendChild(r); l.appendChild(swatch(a)); l.appendChild(el("span", null, A.kurz)); l.title = A.name + (aus ? ": folgt mit dem OpenStreetMap-Auszug" : "");
      reihe.appendChild(l);
    });
    fs.appendChild(reihe); fs.appendChild(el("p", "fuss", g.hinweis + (g.id === "versorgung" && !OSM_DA ? " Folgt: Der OpenStreetMap-Auszug ist noch nicht eingebunden." : ""))); box.appendChild(fs);
  });
  if (fokus != null) { var f = box.querySelector('input[value="' + fokus + '"]'); if (f) f.focus(); }
}
$("ein").addEventListener("change", function (e) {
  if (e.target.name !== "ein") return;
  var a = e.target.value, i = S.ein.indexOf(a);
  if (e.target.checked && i < 0) S.ein.push(a); else if (!e.target.checked && i > -1) S.ein.splice(i, 1);
  einAnwenden(); hashSchreiben();
});
function osmGewaehlt() { return S.ein.some(function (a) { return ART[a] && ART[a].g === "versorgung"; }); }
function einAnwenden() {
  if (!bereitKarte) return;
  var liste = ["literal", S.ein];
  map.setFilter("ein", ["in", ["get", "art"], liste]);
  map.setFilter("ein_odbl", ["in", ["get", "art"], liste]);
  if (osmGewaehlt()) {
    if (window.KIEZ_EINRICHTUNGEN_ODBL) map.setLayoutProperty("ein_odbl", "visibility", "visible");
    else if (!odblLaedt) {
      odblLaedt = true; beginn();
      holen("ein_odbl", function (d) {
        laufend--; odblLaedt = false;
        if (d) { einMerken(d, "ein_odbl"); map.getSource("ein_odbl").setData(d); map.setLayoutProperty("ein_odbl", "visibility", "visible"); einBauen(); }
        else meldung("Die Einrichtungen aus OpenStreetMap ließen sich nicht laden.");
        odblVermerk(); legende(); pruefeBereit();
      });
    }
  } else map.setLayoutProperty("ein_odbl", "visibility", "none");
  odblVermerk(); legende();
}
function odblVermerk() { $("fuss-odbl").hidden = !(S.weg === "fuss" || osmGewaehlt()); }

// ---------- Erreichbarkeit je Zelle (nachgeladen)
function beginn() { laufend++; window.KIEZ_BEREIT = false; }
var laufend = 0, ZUARTEN = ZU_START.slice();
function zuBauen() {
  var box = $("zu");
  var P = window.KIEZ_PLANER, e = window[S.weg === "fuss" ? "KIEZ_ERREICHBAR_FUSS" : "KIEZ_ERREICHBAR"];
  if (P) Object.keys(P.raeume).forEach(function (k) { P.raeume[k].werte.forEach(function (w) { if (w.kennzahl === "anteil_in_radius" && ZUARTEN.indexOf(w.art) < 0) ZUARTEN.push(w.art); }); });
  if (e) e.arten.forEach(function (a) { if (ZUARTEN.indexOf(a) < 0) ZUARTEN.push(a); });
  // Knöpfe nur neu bauen, wenn neue Arten dazukommen; sonst Zustand setzen (Fokus bleibt beim Pfeiltasten-Wechsel)
  var liste = [""].concat(ZUARTEN);
  if (box.dataset.liste !== liste.join(",")) {
    var fokus = document.activeElement && box.contains(document.activeElement) ? document.activeElement.value : null;
    box.querySelectorAll("label").forEach(function (l) { l.remove(); });
    liste.forEach(function (a) {
      var l = el("label", "chip"), r = document.createElement("input"); r.type = "radio"; r.name = "zu"; r.value = a;
      l.appendChild(r); l.appendChild(el("span", null, a ? art(a).kurz : "keine Entfernung")); box.appendChild(l);
    });
    box.dataset.liste = liste.join(",");
    if (fokus != null) { var f = box.querySelector('input[value="' + fokus + '"]'); if (f) f.focus(); }
  }
  box.querySelectorAll("input").forEach(function (r) {
    var a = r.value, l = r.parentNode, aus = !!(a && e && e.arten.indexOf(a) < 0);
    r.checked = S.zu === a; r.disabled = aus; l.classList.toggle("chip--aus", aus);
    l.title = !a ? "Keine Entfernungen anzeigen" : aus ? art(a).name + ": nicht in den Daten (" + (S.weg === "fuss" ? "Fußweg" : "Luftlinie") + ")" : "Entfernung jeder bewohnten Zelle zur nächsten Einrichtung: " + art(a).name;
  });
  document.querySelectorAll('#weg input').forEach(function (r) {
    r.checked = r.value === S.weg;
    if (r.value === "fuss" && !FUSS_DA) {
      r.disabled = true; r.parentNode.classList.add("chip--aus"); r.parentNode.title = "Fußweg folgt: Der OpenStreetMap-Auszug für das Wegenetz ist noch nicht eingebunden.";
      var sp = r.parentNode.querySelector("span"); if (sp) sp.textContent = "Fußweg folgt";   // Sperre sichtbar, nicht nur im title (Touch)
    }
  });
}
$("zu").addEventListener("change", function (e) { if (e.target.name === "zu") { S.zu = e.target.value; zuAnwenden(); } });
$("weg").addEventListener("change", function (e) { if (e.target.name === "weg") wegSetzen(e.target.value); });
function wegSetzen(w) { S.weg = w; nochmal(); odblVermerk(); zuAnwenden(); versorgung(); raumHinweis(); vergleich(); }

// themen.js liest KIEZ_ZELLEN beim eigenen Laden; zellen.js kommt hier erst bei Bedarf. Darum prüft die Seite
// die Zellreihenfolge selbst (gleiche Regel wie KIEZ_THEMEN.ebenen.zellwerte: anzahl, erste_id, letzte_id).
function zellwerte(d, a) {
  var f = window.KIEZ_ZELLEN.features, l = d.werte && d.werte[a];
  return Array.isArray(l) && d.anzahl === f.length && l.length === f.length && f.length &&
    d.erste_id === f[0].properties.id && d.letzte_id === f[f.length - 1].properties.id ? l : null;
}
var ZELLEN = null, EBENE = { luft: { datei: "erreichbar", id: "erreichbar", p: "l_" }, fuss: { datei: "erreichbar_fuss", id: "erreichbar_fuss", p: "f_" } };
function thema(w, a) { return T.THEMA[EBENE[w].p + a]; }
function zuAnwenden() {
  if (!bereitKarte) return;
  var w = S.weg, a = S.zu, E = EBENE[w];
  if (!a) { map.setLayoutProperty("zellen", "visibility", "none"); zuBauen(); legende(); status(); hashSchreiben(); return; }
  beginn();
  holen("zellen", function (z) {
    holen(E.datei, function (d) {
      laufend--;
      if (!z) { meldung("Die Zellen der Karte ließen sich nicht laden; keine Entfernungen."); S.zu = ""; zuAnwenden(); pruefeBereit(); return; }
      if (!d) {
        meldung(w === "fuss" ? "Die Fußweg-Daten ließen sich nicht laden; die Karte zeigt Luftlinie." : "Die Entfernungen ließen sich nicht laden.");
        if (w === "fuss") { S.weg = "luft"; odblVermerk(); zuAnwenden(); versorgung(); } else { S.zu = ""; zuAnwenden(); }
        pruefeBereit(); return;
      }
      var vermerk = vermerke(d.quellen).join(" ");
      T.ebenen.registrieren({ id: E.id, datei: WURZEL + DATEI[E.datei].src, global: DATEI[E.datei].global, art: "zellwert", odbl: !!DATEI[E.datei].odbl,
        themen: d.arten.map(function (x) { return { id: E.p + x, h: E.p + art(x).h, kurz: art(x).kurz, name: "Entfernung zur nächsten Einrichtung: " + art(x).name, einheit: d.einheit, quelle: vermerk }; }) });
      zuBauen();
      if (d.arten.indexOf(a) < 0 || S.zu !== a || S.weg !== w) { if (S.zu === a && S.weg === w) { meldung(art(a).name + " ist in den Daten (" + METHODE[d.methode] + ") nicht enthalten."); S.zu = ""; zuAnwenden(); } pruefeBereit(); return; }
      var t = thema(w, a), l = zellwerte(d, a);
      if (!l) { meldung("Die Entfernungen passen nicht zu den Zellen der Karte."); S.zu = ""; zuAnwenden(); pruefeBereit(); return; }
      if (!ZELLEN) { ZELLEN = { type: "FeatureCollection", features: z.features.map(function (f) { return { type: "Feature", geometry: f.geometry, properties: { id: f.properties.id, ew: f.properties.ew } }; }) }; }
      if (ZELLEN.features[0].properties[t.id] === undefined) ZELLEN.features.forEach(function (f, i) { f.properties[t.id] = l[i]; });
      var src = map.getSource("zellen");
      src.setData(ZELLEN);
      src.setAttribution && src.setAttribution(vermerk);
      map.setFilter("zellen", ["!=", ["get", t.id], null]);
      map.setPaintProperty("zellen", "fill-color", T.farbe(t, d.einheit === "min" ? KL_MIN : KL_M));
      map.setLayoutProperty("zellen", "visibility", "visible");
      legende(); status(); hashSchreiben(); pruefeBereit();
    });
  });
  zuBauen(); legende(); status(); hashSchreiben();
}

// ---------- Legende: Entfernungsstufen und Symbole der gewählten Einrichtungen, mit Quelle
function legende() {
  var L = $("legende"); L.innerHTML = "";
  var d = window[S.weg === "fuss" ? "KIEZ_ERREICHBAR_FUSS" : "KIEZ_ERREICHBAR"];
  if (S.zu && d && map.getLayoutProperty("zellen", "visibility") === "visible") {
    var k = d.einheit === "min" ? KL_MIN : KL_M, ein = d.einheit === "min" ? "min" : "m";
    L.appendChild(el("p", "legende__titel", "Entfernung zur nächsten " + art(S.zu).kurz + " · " + METHODE[d.methode]));
    L.appendChild(el("p", "legende__weg", METHODE[d.methode] + ", " + ein + " je bewohnter 100-m-Zelle"));
    var st = el("div", "stufen stufen--flach"); st.setAttribute("aria-hidden", "true");
    T.STUFEN.forEach(function (f) { var x = el("span"); x.style.background = f; st.appendChild(x); }); L.appendChild(st);
    var m = el("div", "marken"); m.appendChild(el("span", null, "0"));
    k.grenzen.forEach(function (g) { m.appendChild(el("span", null, fmt.format(g))); }); m.appendChild(el("span", null, "mehr " + ein)); L.appendChild(m);
    var str = ((window.KIEZ_EINRICHTUNGEN || {}).features || []).filter(function (f) { return f.properties.hinweis && f.properties.art === S.zu; });
    if (str.length) L.appendChild(el("p", "legende__q", str.map(function (f) { return f.properties.name; }).join(", ") + ": Lage strittig, zählt nicht für die Entfernungen."));
    var q = el("p", "legende__q legende__vermerk"); q.appendChild(vermerkKnoten(vermerke(d.quellen).join(" "))); L.appendChild(q);
  }
  var sichtbar = S.ein.filter(function (a) { return ARTEN_IN.ein.indexOf(a) > -1 || (window.KIEZ_EINRICHTUNGEN_ODBL && ARTEN_IN.ein_odbl.indexOf(a) > -1); });
  if (sichtbar.length) {
    var ul = el("ul", "legende__arten");
    sichtbar.forEach(function (a) { var li = el("li"); li.appendChild(swatch(a)); li.appendChild(document.createTextNode(art(a).kurz)); ul.appendChild(li); });
    L.appendChild(ul);
  }
  L.hidden = !L.children.length;
}

// ---------- Raumeinheiten und Versorgungstabelle
function planerDaten() { return window[S.weg === "fuss" ? "KIEZ_PLANER_FUSS" : "KIEZ_PLANER"]; }
function raumBauen() {
  var sel = $("raumebene"); sel.innerHTML = "";
  Object.keys(RAUMEBENE).forEach(function (k) {
    if (!RAUMEBENE[k].fc) return;
    var o = el("option", null, RAUMEBENE[k].name); o.value = k; sel.appendChild(o);
  });
  sel.value = S.raum;
  raumHinweis();
  var box = $("raeume"); box.innerHTML = "";
  RAUMEBENE[S.raum].fc.features.map(function (f) { return f.properties; }).sort(function (a, b) { return a.nr - b.nr; }).forEach(function (p) {
    var li = el("li"), b = el("button", "treffer"); b.type = "button"; b.dataset.nr = p.nr;
    var i = el("i"); i.style.background = S.raum === "st" ? T.FARBE[p.nr] : "#cdd1cc"; b.appendChild(i);
    b.appendChild(el("b", null, p.nr)); b.appendChild(el("span", null, p.name));
    b.addEventListener("click", function () { waehle(S.r === p.nr ? "" : p.nr); });
    li.appendChild(b); box.appendChild(li);
  });
  markieren();
}
function raumHinweis() {
  var P = planerDaten() || window.KIEZ_PLANER || window.KIEZ_PLANER_FUSS, E = RAUMEBENE[S.raum];
  $("raumebene-hinweis").textContent = P && P.raumebene !== E.datei
    ? "Die Versorgungswerte liegen je " + (P.raumebene === "planungsraum" ? "Planungsraum" : "Stadtteil") + " vor. " + E.name + " dienen hier der Orientierung" +
      (P.raumebene === "planungsraum" && !PR ? "; die Grenzen der Planungsräume fehlen der Karte noch." : "; für die Tabelle die andere Ebene wählen.")
    : S.raum === "pr"
      ? "Planungsräume sind die Ebene, auf der die Stadt Kita und Schule plant (19 Räume, Grenzen Stand 31.12.2025)."
      : PR ? "Die 32 amtlichen Stadtteile der Landeshauptstadt."
        : "Die Stadt plant Kita und Schule auf Planungsräumen. Bis deren Grenzen vorliegen, rechnet der Planer je Stadtteil.";
}
function markieren() { $("raeume").querySelectorAll(".treffer").forEach(function (b) { b.setAttribute("aria-pressed", String(b.dataset.nr === S.r)); }); }
var gewaehlt = "";
function waehle(nr) {
  if (bereitKarte && gewaehlt) map.setFeatureState({ source: "raum", id: gewaehlt }, { gewaehlt: false });
  gewaehlt = S.r = RAUM[nr] ? nr : "";
  if (bereitKarte && gewaehlt) map.setFeatureState({ source: "raum", id: gewaehlt }, { gewaehlt: true });
  nochmal(); markieren(); versorgung(); status(); hashSchreiben();
  $("griff-name").textContent = S.r ? S.r + " " + RAUM[S.r].properties.name : "Versorgung";
  $("zoom-raum").querySelector(".knopf__text").textContent = S.r ? "Auf Raumeinheit zoomen" : "Ganz Potsdam zeigen";
}
// planerLaedt[datei]: true = lädt oder geladen, false = fehlgeschlagen (nächste Handlung versucht es neu)
var planerLaedt = {};
function nochmal() { Object.keys(planerLaedt).forEach(function (k) { if (planerLaedt[k] === false) delete planerLaedt[k]; }); }
function versorgung() {
  var box = $("vs-inhalt"); box.innerHTML = "";
  if (!S.r) { $("vs-name").textContent = "Keine Raumeinheit gewählt"; $("vs-art").textContent = "Raumeinheit in der Liste oder in der Karte wählen. Die Tabelle zeigt je Zeile Wert, Methode, Status und Quelle."; return; }
  var p = RAUM[S.r].properties, P = planerDaten();
  $("vs-name").textContent = p.name;
  $("vs-art").textContent = RAUMEBENE[S.raum].einzahl + " " + p.nr + " der Landeshauptstadt Potsdam, Werte " + (S.weg === "fuss" ? "als Fußweg" : "in Luftlinie");
  if (!P) {
    var dn = S.weg === "fuss" ? "planer_fuss" : "planer";
    if (planerLaedt[dn] === undefined) {
      planerLaedt[dn] = true; beginn();
      holen(dn, function (d) {
        laufend--; planerLaedt[dn] = !!d;
        if (!d && dn === "planer_fuss") { meldung("Die Fußweg-Tabelle ließ sich nicht laden; sie zeigt Luftlinie."); S.weg = "luft"; odblVermerk(); zuAnwenden(); }
        if (d) { zuBauen(); raumHinweis(); }
        versorgung(); vergleich(); pruefeBereit();
      });
    }
    box.appendChild(el("p", "fuss", planerLaedt[dn] === false ? "Die Versorgungsdatei ließ sich nicht laden." : "Daten werden geladen.")); return;
  }
  // Rechnet die Datei auf einer anderen Ebene als der gewählten, passen die Schlüssel nicht:
  // dann nichts zuordnen, sondern das sagen.
  raumHinweis();
  if (P.raumebene !== RAUMEBENE[S.raum].datei) {
    var andere = Object.keys(RAUMEBENE).filter(function (k) { return RAUMEBENE[k].datei === P.raumebene && RAUMEBENE[k].fc; })[0];
    box.appendChild(el("p", "fuss", "Die Versorgungsdatei rechnet auf " + (RAUMEBENE_DATEI[P.raumebene] || P.raumebene) + ". " +
      (andere ? "Für die Tabelle oben die Ebene „" + RAUMEBENE[andere].name + "“ wählen; " + RAUMEBENE[S.raum].name + " dienen nur der Orientierung."
              : "Deren Grenzen fehlen der Karte noch; die Tabelle erscheint, sobald sie eingebunden sind. Bis dahin lassen sich die Werte nicht einem " + RAUMEBENE[S.raum].einzahl + " zuordnen.")));
    return;
  }
  var R = P.raeume[S.r];
  if (!R) { box.appendChild(el("p", "fuss", "Für diese Raumeinheit stehen keine Versorgungswerte in der Datei (" + (S.weg === "fuss" ? "Fußweg" : "Luftlinie") + ").")); return; }
  var QN = [], qnr = function (q) { var i = QN.indexOf(q); if (i < 0) { QN.push(q); i = QN.length - 1; } return i + 1; };
  // Einwohner: gerundet laut Datei, Quelle Zensus
  var ew = el("p", "vs-ew");
  ew.appendChild(el("b", null, R.ew == null ? "Einwohner: k. A." : "rund " + fmt.format(R.ew) + " Einwohner"));
  ew.appendChild(document.createTextNode(" (Zensus 2022, Stichtag 15.05.2022, gerundet auf " + fmt.format(P.rundung.ew) + "; © Statistische Ämter des Bundes und der Länder, dl-de/by-2-0, "));
  var lz = el("a", "link", "Lizenztext"); lz.href = DLDE; ew.appendChild(lz); ew.appendChild(document.createTextNode(", Daten verändert (eigene Berechnung))"));
  box.appendChild(ew);
  if (P.hinweis) box.appendChild(el("p", "fuss vs-hinweis", P.hinweis));
  steckbriefLink(box, p, P);
  var ul = el("ul", "vs-liste"); ul.setAttribute("aria-label", "Versorgung " + p.name);
  R.werte.forEach(function (w) {
    var li = el("li", "vs-zeile" + (w.status === "orientierung" ? " vs-zeile--orientierung" : ""));
    li.dataset.kennzahl = w.kennzahl;
    li.appendChild(el("h3", "vs-titel", kennzahlText(w)));
    var z = el("p", "vs-wert"); z.appendChild(el("span", "vs-zahl", w.wert == null ? "k. A." : zahl(w.wert) + NB + w.einheit));
    if (wegText(w)) z.appendChild(el("span", "marke-weg", wegText(w)));
    li.appendChild(z);
    if (znText(w)) li.appendChild(el("p", "vs-zn", znText(w) + (differenzText(w) ? ". " + differenzText(w) : "")));
    var G = P.gesamt && P.gesamt.werte.filter(function (g) { return wertSchluessel(g) === wertSchluessel(w); })[0];
    if (G) li.appendChild(el("p", "vs-stadt", "Ganz Potsdam: " + (G.wert == null ? "kein Wert" : zahl(G.wert) + NB + G.einheit) + (znKurz(G) ? " (" + znKurz(G) + ")" : "")));
    var st = el("p", "vs-status");
    st.appendChild(el("span", "abzeichen abzeichen--" + statusKlasse(w), statusText(w)));
    if (w.vorlaeufig) st.appendChild(el("span", "abzeichen abzeichen--vorlaeufig", "vorläufig, ohne Schulbezirk"));
    if (NUR_LAGE[w.art]) st.appendChild(el("span", "abzeichen abzeichen--vorlaeufig", "nur Lage, keine Versorgungsaussage"));
    li.appendChild(st);
    if (w.richtwert) {
      var rw = el("p", "vs-richt", (w.status === "orientierung" ? "Orientierungswert: " : "Richtwert: ") + zahl(w.richtwert.wert) + NB + w.richtwert.einheit + (wegText(w) ? " " + wegText(w) : ""));
      rw.appendChild(el("sup", null, "[" + qnr(w.richtwert.q) + "]")); if (w.richtwert.seite) rw.appendChild(document.createTextNode(", " + w.richtwert.seite)); li.appendChild(rw);
    }
    var q = el("p", "vs-q"); q.appendChild(document.createTextNode("Quelle [" + qnr(w.q) + "] " + ((P.quellen[w.q] || {}).quelle || w.q) + ". Stand: " + w.stand + ". " + w.unsicherheit));
    li.appendChild(q);
    if (w.prognose) li.appendChild(el("p", "vs-q", "Prognose liegt vor (siehe Datei)."));
    ul.appendChild(li);
  });
  box.appendChild(ul);
  var ol = el("ol", "vs-quellen"); ol.setAttribute("aria-label", "Quellen der Tabelle");
  QN.forEach(function (k) { var li = el("li"), Q = P.quellen[k] || { vermerk: k }; li.appendChild(vermerkKnoten(Q.vermerk)); ol.appendChild(li); });
  box.appendChild(ol);
}

// Druckseite A4 je Planungsraum (daten/export/steckbriefe/<nr>.html, aus skripte/16_export.py); nur für die
// echten Planungsräume, nicht für Beispieldaten oder die Stadtteil-Ebene. Der Steckbrief rechnet in Luftlinie.
function steckbriefLink(box, p, P) {
  if (FIXTURE || S.raum !== "pr" || P.raumebene !== "planungsraum") return;
  var z = el("div", "seite__aktion vs-steckbrief"), a = el("a", "knopf knopf--rand");
  a.href = WURZEL + "export/steckbriefe/" + encodeURIComponent(p.nr) + ".html";
  var f = el("span", "knopf__flut"); f.setAttribute("aria-hidden", "true"); a.appendChild(f);
  a.appendChild(el("span", "knopf__text", "Steckbrief (A4)")); a.title = "Steckbrief " + p.nr + " " + p.name + " als Druckseite";
  z.appendChild(a); box.appendChild(z);
  box.appendChild(el("p", "fuss", "Druckseite dieses Planungsraums mit der Versorgungstabelle. Der Steckbrief rechnet in Luftlinie" +
    (S.weg === "fuss" ? ", die Tabelle hier zeigt den Fußweg." : ".")));
}

// ---------- Vergleich aller Raumeinheiten (Audit K24): eine Kennzahl für jede Raumeinheit und ganz Potsdam.
// Lädt die Versorgungsdatei erst auf Knopfdruck (Startgewicht), zeigt Wert, Zähler und Nenner aus der Datei.
var vgOffen = false;
function vergleich() {
  var box = $("vg-inhalt"), sel = $("vg-kennzahl"); if (!box || !vgOffen) return;
  var P = planerDaten();
  if (!P) {
    var dn = S.weg === "fuss" ? "planer_fuss" : "planer";
    box.innerHTML = ""; box.appendChild(el("p", "fuss", planerLaedt[dn] === false ? "Die Versorgungsdatei ließ sich nicht laden." : "Daten werden geladen."));
    if (planerLaedt[dn] === undefined) {
      planerLaedt[dn] = true; beginn();
      holen(dn, function (d) { laufend--; planerLaedt[dn] = !!d; if (d) { zuBauen(); raumHinweis(); } versorgung(); vergleich(); pruefeBereit(); });
    }
    return;
  }
  // Auswahl: jede Kennzahl einmal, in der Reihenfolge der Datei
  var liste = [], gesehen = {};
  Object.keys(P.raeume).forEach(function (k) { P.raeume[k].werte.forEach(function (w) { var s = wertSchluessel(w); if (!gesehen[s]) { gesehen[s] = 1; liste.push(w); } }); });
  var alt = sel.value, schl = liste.map(wertSchluessel).join(",");
  if (sel.dataset.liste !== schl) {
    sel.innerHTML = "";
    liste.forEach(function (w) { var o = el("option", null, kennzahlText(w) + (wegText(w) ? ", " + wegText(w) : "")); o.value = wertSchluessel(w); sel.appendChild(o); });
    sel.dataset.liste = schl;
  }
  sel.value = gesehen[alt] ? alt : (liste[0] ? wertSchluessel(liste[0]) : "");
  sel.disabled = false;
  var w0 = liste.filter(function (w) { return wertSchluessel(w) === sel.value; })[0];
  box.innerHTML = ""; if (!w0) return;
  var tab = el("table", "tabelle vg-tabelle"), cap = el("caption", "nur-sr", kennzahlText(w0) + ", alle " + (P.raumebene === "planungsraum" ? "Planungsräume" : "Stadtteile") + " und ganz Potsdam");
  tab.appendChild(cap);
  var kopf = el("tr"); [P.raumebene === "planungsraum" ? "Planungsraum" : "Stadtteil", "Wert", "Zähler", "Nenner"].forEach(function (x) { var th = el("th", null, x); th.scope = "col"; kopf.appendChild(th); });
  var th = el("thead"); th.appendChild(kopf); tab.appendChild(th);
  function reihe(teil, nr, name, w, fuss) {
    var tr = el("tr", fuss ? "vg-stadt" : null), c = el("th", null, (nr ? nr + " " : "") + name); c.scope = "row"; tr.appendChild(c);
    tr.appendChild(el("td", null, !w || w.wert == null ? "kein Wert" : zahl(w.wert) + NB + w.einheit));
    tr.appendChild(el("td", null, w && w.zaehler != null ? fmt.format(w.zaehler) : ""));
    tr.appendChild(el("td", null, w && w.nenner != null ? fmt.format(w.nenner) : ""));
    teil.appendChild(tr);
  }
  var tb = el("tbody");
  Object.keys(P.raeume).sort(function (a, b) { return a - b; }).forEach(function (nr) {
    var R = P.raeume[nr]; reihe(tb, nr, R.name, R.werte.filter(function (w) { return wertSchluessel(w) === sel.value; })[0], false);
  });
  tab.appendChild(tb);
  if (P.gesamt) { var tf = el("tfoot"); reihe(tf, "", "Ganz Potsdam", P.gesamt.werte.filter(function (w) { return wertSchluessel(w) === sel.value; })[0], true); tab.appendChild(tf); }
  box.appendChild(tab);
  var G = P.gesamt && P.gesamt.werte.filter(function (w) { return wertSchluessel(w) === sel.value; })[0];
  box.appendChild(el("p", "fuss vg-hinweis", (w0.zaehler_text ? "Zähler: " + w0.zaehler_text + ". Nenner: " + w0.nenner_text + ". " : "Ohne Zähler und Nenner (Median über die Zellen). ") +
    statusText(w0) + (G ? ". " + G.unsicherheit : ". Für ganz Potsdam gibt es hier keinen Wert.") + " Hinweise je Raumeinheit stehen in der Versorgungstabelle oben."));
}
$("vg-laden").addEventListener("click", function () { vgOffen = true; this.hidden = true; $("vg-auswahl").hidden = false; vergleich(); });
$("vg-kennzahl").addEventListener("change", vergleich);

// ---------- Fragen als Einstieg: jede setzt den Zustand und erklärt nebenbei eine Funktion
var FRAGEN = [
  { titel: "Wie weit ist es zur nächsten Kita?", text: "Färbt jede bewohnte Zelle nach der Entfernung zur nächsten Kita. Klick auf einen Kreis zeigt Plätze und Quelle.", ein: ["kita"], zu: "kita" },
  { titel: "Liegt eine Grundschule in der Nähe?", text: "Entfernung zur nächsten Grundschule. Vorläufig, denn Grundschulen werden über Schulbezirke geplant, die hier noch fehlen.", ein: ["grundschule"], zu: "grundschule" },
  { titel: "Wo ist das nächste Grün?", text: "Entfernung zur nächsten öffentlichen Grünfläche" + (OSM_DA ? ", dazu Spielplätze aus OpenStreetMap." : "; Spielplätze folgen mit dem OpenStreetMap-Auszug."), ein: ["spielplatz"], zu: "gruen" },
  { titel: "Wie ist ein " + (PR && !FIXTURE ? "Planungsraum" : "Stadtteil") + " versorgt?", text: (PR && !FIXTURE ? "Planungsraum" : "Stadtteil") + " wählen: Die Tabelle nennt je Zeile Wert, Methode, Status und Quelle.", ein: ["kita", "hort", "grundschule"], zu: "", raum: true }
];
function fragenBauen() {
  var ul = $("fragen");
  FRAGEN.forEach(function (F, i) {
    var li = el("li"), b = el("button", "frage-knopf"); b.type = "button"; b.dataset.frage = i;
    b.appendChild(el("span", "frage-knopf__nr", String(i + 1))); var t = el("span", "frage-knopf__text");
    t.appendChild(el("b", null, F.titel)); t.appendChild(el("span", null, F.text)); b.appendChild(t);
    b.addEventListener("click", function () {
      S.ein = F.ein.filter(erlaubt); S.zu = F.zu;
      document.querySelectorAll('#ein input').forEach(function (r) { r.checked = S.ein.indexOf(r.value) > -1; });
      einAnwenden(); zuAnwenden();
      if (F.raum) { if (PR && !FIXTURE && S.raum !== "pr") ebeneSetzen("pr"); var v = $("block-raum"); v.scrollIntoView({ block: "start", behavior: RUHIG ? "auto" : "smooth" }); var f = $("raeume").querySelector(".treffer"); if (f) f.focus({ preventScroll: true }); }
      else if (SCHMAL) seite(false);
    });
    li.appendChild(b); ul.appendChild(li);
  });
}

// ---------- Bedienung
function ebeneSetzen(k) {
  if (!RAUMEBENE[k] || !RAUMEBENE[k].fc) return;
  if (bereitKarte) map.removeFeatureState({ source: "raum" });
  gewaehlt = ""; S.raum = k; raumIndex();
  if (bereitKarte) { var q = map.getSource("raum"); q.setData(RAUMEBENE[k].fc); if (q.setAttribution) q.setAttribution(RAUMEBENE[k].att); }
  raumBauen(); waehle(RAUM[S.r] ? S.r : "");
}
$("raumebene").addEventListener("change", function (e) { ebeneSetzen(e.target.value); });
$("zoom-raum").addEventListener("click", function () {
  var opt = { padding: SCHMAL ? { top: 70, bottom: 30, left: 16, right: 16 } : 40, maxZoom: 15.5 };
  var b = S.r ? T.umriss(RAUM[S.r]) : T.GANZ;
  map.fitBounds(b, Object.assign(opt, RUHIG ? { animate: false } : { duration: 700 }));
  if (SCHMAL) seite(false);
});
$("link-teilen").addEventListener("click", function () {
  hashSchreiben();
  var url = location.href, hin = $("teilen-hinweis");
  function ok() { hin.textContent = "Link kopiert. Er öffnet genau diese Ansicht."; }
  function zeigen() { hin.textContent = "Link: " + url; }
  if (navigator.clipboard && window.isSecureContext) navigator.clipboard.writeText(url).then(ok, zeigen); else zeigen();
});
var seiteEl = $("seite"), griff = $("seite-griff");
function seite(an) { seiteEl.classList.toggle("offen", an); griff.setAttribute("aria-expanded", String(an)); }
griff.addEventListener("click", function () { seite(!seiteEl.classList.contains("offen")); });
addEventListener("keydown", function (e) { if (e.key === "Escape" && seiteEl.classList.contains("offen") && SCHMAL) { seite(false); griff.focus(); } });
var letzteMeldung = "";
function meldung(t) { letzteMeldung = t; $("kartenstatus").textContent = t; var h = $("teilen-hinweis"); if (h) h.textContent = t; }
function status() {
  var m = letzteMeldung; letzteMeldung = "";
  $("kartenstatus").textContent = (m ? m + " " : "") + "Karte zeigt: " + (S.ein.length ? S.ein.map(function (a) { return art(a).kurz; }).join(", ") : "keine Einrichtungen") +
    (S.zu ? "; Entfernung zur nächsten " + art(S.zu).kurz + " in " + (S.weg === "fuss" ? "Fußweg" : "Luftlinie") : "") + (S.r ? "; gewählt " + S.r + " " + RAUM[S.r].properties.name : "") + ".";
}

// ---------- Klicks in der Karte (keine Kamerabewegung)
function zeile(t, a) { return "<tr><td>" + t + "</td><td>" + a + "</td></tr>"; }
function popupEinrichtung(e, f) {
  var x = EIN[f.properties.id]; if (!x) return false;
  var p = x.f.properties, A = art(p.art), Q = x.d.quellen[p.q] || { vermerk: p.q }, osm = x.quelle === "ein_odbl", h = "";
  h += "<b>" + esc(osm ? A.name : (p.name || A.name)) + "</b><br>" + esc(A.name) + (p.unterart && !osm ? ", " + esc(wort(p.unterart)) : "");
  var tab = "";
  if (p.plaetze != null) tab += zeile("Plätze", fmt.format(p.plaetze));
  if (p.schueler != null) tab += zeile("Schüler", fmt.format(p.schueler) + (p.schueler_stand ? " (Stand " + esc(p.schueler_stand) + ")" : ""));
  if (tab) h += "<table class='pop-tab'>" + tab + "</table>";
  if (p.plaetze != null) h += "<div class='pop-q'>Genehmigte Plätze laut Betriebserlaubnis. Wie viele frei sind, steht nicht in den Daten.</div>";
  if (p.status === "lage_ohne_kapazitaet" || osm) h += "<div class='pop-q'>Nur Lage, ohne Kapazität" + (NUR_LAGE[p.art] ? "; keine Aussage zur Versorgung" : "") + ".</div>";
  if (p.hinweis) h += "<div class='pop-q'>" + esc(p.hinweis) + "</div>";
  else if (p.in_potsdam === false) h += "<div class='pop-q'>Außerhalb der Stadtgrenze; zählt für die Entfernungen mit.</div>";
  h += "<div class='pop-q'>" + vermerkHtml(Q.vermerk) + "</div>";
  new maplibregl.Popup({ maxWidth: "290px" }).setLngLat(x.f.geometry.coordinates).setHTML(h).addTo(map);
  return true;
}
map.on("click", function (e) {
  var lay = ["ein", "ein_odbl"].filter(function (l) { return map.getLayoutProperty(l, "visibility") !== "none"; });
  var pkt = lay.length ? map.queryRenderedFeatures([[e.point.x - 6, e.point.y - 6], [e.point.x + 6, e.point.y + 6]], { layers: lay }) : [];
  if (pkt.length && popupEinrichtung(e, pkt[0])) return;
  var zelleGezeigt = false;
  if (map.getLayoutProperty("zellen", "visibility") === "visible") {
    var c = map.queryRenderedFeatures(e.point, { layers: ["zellen"] }), d = window[S.weg === "fuss" ? "KIEZ_ERREICHBAR_FUSS" : "KIEZ_ERREICHBAR"], t = thema(S.weg, S.zu);
    if (c.length && d && t) {
      zelleGezeigt = true;
      var v = Number(c[0].properties[t.id]);
      new maplibregl.Popup({ maxWidth: "290px" }).setLngLat(e.lngLat).setHTML("<b>Gitterzelle 100 × 100 m</b><table class='pop-tab'>" +
        zeile("Nächste " + esc(art(S.zu).kurz), fmt.format(v) + NB + esc(d.einheit) + " " + METHODE[d.methode]) + "</table><div class='pop-q'>" +
        vermerkHtml(vermerke(d.quellen).join(" ")) + " Zellen: Zensus 2022, © Statistische Ämter des Bundes und der Länder, dl-de/by-2-0 (<a class=\"link\" href=\"" + DLDE + "\">Lizenztext</a>), Daten verändert (eigene Berechnung).</div>").addTo(map);
    }
  }
  var r = map.queryRenderedFeatures(e.point, { layers: ["raum-flaeche"] });
  // Klick wählt die Raumeinheit darunter; ein zweiter Klick hebt die Wahl auf, außer er galt einer Zelle
  if (r.length) { var nr = r[0].properties.nr; if (nr !== S.r) waehle(nr); else if (!zelleGezeigt) waehle(""); }
});
var zeiger = null;   // höchstens eine Abfrage je Bild
map.on("mousemove", function (e) {
  var neu = !zeiger; zeiger = e.point; if (!neu) return;
  requestAnimationFrame(function () {
    var pt = zeiger; zeiger = null;
    var lay = ["ein", "ein_odbl", "raum-flaeche"].filter(function (l) { return map.getLayer(l) && map.getLayoutProperty(l, "visibility") !== "none"; });
    map.getCanvas().style.cursor = map.queryRenderedFeatures(pt, { layers: lay }).length ? "pointer" : "";
  });
});
map.on("moveend", hashSchreiben);

// ---------- Aufbau, sobald Karte und Startdaten da sind
var kartenGeladen = false, datenDa = false;
map.on("load", function () { kartenGeladen = true; if (datenDa) aufbauenKarte(); });
function aufbauen() { datenDa = true; einBauen(); zuBauen(); raumBauen(); fragenBauen(); versorgung(); if (kartenGeladen) aufbauenKarte(); }
function aufbauenKarte() {
  bereitKarte = true;
  map.addControl(new maplibregl.AttributionControl({ compact: true }), "bottom-right");
  var att = document.querySelector(".maplibregl-ctrl-attrib"); if (att) att.classList.remove("maplibregl-compact-show");
  // Ebene kann vor dem Laden der Karte gewechselt haben (Auswahl, Frage 4): Quelle nachziehen
  var rq = map.getSource("raum"); rq.setData(RAUMEBENE[S.raum].fc); if (rq.setAttribution) rq.setAttribution(RAUMEBENE[S.raum].att);
  var E = window.KIEZ_EINRICHTUNGEN;
  if (E) { map.getSource("ein").setData(E); var s = map.getSource("ein"); if (s.setAttribution) s.setAttribution(vermerke(E.quellen).join(" ")); }
  var paint = symbolFarbe();
  Object.keys(paint).forEach(function (k) { map.setPaintProperty("ein", k, paint[k]); map.setPaintProperty("ein_odbl", k, paint[k]); });
  waehle(S.r); einAnwenden(); zuAnwenden(); odblVermerk(); status();
  pruefeBereit();
}
function pruefeBereit() {
  if (!bereitKarte || laufend > 0) return;
  window.KIEZ_BEREIT = false;
  map.once("idle", function () { if (laufend === 0) window.KIEZ_BEREIT = true; });
  map.triggerRepaint();
}

// ======================================================================= Methode
function methode() {
  holen("planer", function (P) {
    var box = $("richtwerte"); if (!box) return;
    if (!P) { box.appendChild(el("p", "fuss", "Die Versorgungsdatei ließ sich nicht laden.")); window.KIEZ_BEREIT = true; return; }
    var gesehen = {}, zeilen = [];
    Object.keys(P.raeume).forEach(function (k) {
      P.raeume[k].werte.forEach(function (w) {
        var key = [w.kennzahl, w.art, statusKlasse(w), w.richtwert ? w.richtwert.wert + w.richtwert.einheit : "-"].join("|");
        if (gesehen[key]) return; gesehen[key] = 1; zeilen.push(w);
      });
    });
    var tab = el("table", "tabelle richt-tabelle"), kopf = el("tr");
    ["Kennzahl", "Maßstab", "Status", "Quelle"].forEach(function (t) { kopf.appendChild(el("th", null, t)); });
    var th = el("thead"); th.appendChild(kopf); tab.appendChild(th); var tb = el("tbody");
    zeilen.forEach(function (w) {
      var tr = el("tr");
      tr.appendChild(el("td", null, kennzahlText(w)));
      tr.appendChild(el("td", null, w.richtwert ? zahl(w.richtwert.wert) + NB + w.richtwert.einheit + (wegText(w) ? " " + wegText(w) : "") : "ohne festen Wert"));
      tr.appendChild(el("td", null, statusText(w) + (w.vorlaeufig ? "; vorläufig, ohne Schulbezirk" : "")));
      var td = el("td"), Q = P.quellen[(w.richtwert || w).q] || { vermerk: (w.richtwert || w).q };
      td.appendChild(vermerkKnoten(Q.vermerk)); if (w.richtwert && w.richtwert.seite) td.appendChild(document.createTextNode(", " + w.richtwert.seite));
      // Maßstab aus einem Dokument ohne Lizenz: dazu die Quelle der Daten mit ihrem Vermerk (Lizenz)
      if (w.richtwert && w.q && w.q !== w.richtwert.q && P.quellen[w.q]) { td.appendChild(document.createTextNode(". Daten: ")); td.appendChild(vermerkKnoten(P.quellen[w.q].vermerk)); }
      tr.appendChild(td); tb.appendChild(tr);
    });
    tab.appendChild(tb); box.appendChild(tab);
    // Zahl der Planungsräume aus der Datei statt fest im Text (K28); Beispieldaten rechnen auf Stadtteilen
    if (P.raumebene === "planungsraum" && !P.fixture) document.querySelectorAll('[data-feld="anzahl-raeume"]').forEach(function (n) { n.textContent = String(Object.keys(P.raeume).length); });
    // Prüfwerte mit Beleg aus der Datei (Audit K28): Zahl, Stand und Belegdatei; ohne Datei bleibt der Text im HTML
    var PW = P.fixture ? null : P.pruefwerte;
    if (PW) {
      var stellen = { ganz: { maximumFractionDigits: 0 }, eins: { minimumFractionDigits: 1, maximumFractionDigits: 1 }, genau: { maximumFractionDigits: 3 } };
      document.querySelectorAll("[data-pw]").forEach(function (n) { var x = PW[n.getAttribute("data-pw")]; if (x) n.textContent = new Intl.NumberFormat("de-DE", stellen[n.getAttribute("data-format") || "genau"]).format(x.wert); });
      document.querySelectorAll("[data-pw-stand]").forEach(function (n) { var x = PW[n.getAttribute("data-pw-stand")]; if (x) n.textContent = new Date(x.stand + "T12:00:00").toLocaleDateString("de-DE", { day: "numeric", month: "long", year: "numeric" }); });
      document.querySelectorAll("[data-pw-beleg]").forEach(function (n) { var x = PW[n.getAttribute("data-pw-beleg")]; if (x) n.textContent = x.beleg; });
    }
    var h = $("planer-hinweis"); if (h) h.textContent = (P.hinweis || "") + " Einwohnerzahlen sind auf " + fmt.format(P.rundung.ew) + " gerundet. Raumebene der Datei: " + (P.raumebene === "stadtteil" ? "Stadtteile" : "Planungsräume") + ", Stand der Auswertung " + P.stand.split("-").reverse().join(".") + ".";
    window.KIEZ_BEREIT = true;
  });
}
})();
