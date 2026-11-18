/* Kiezatlas: gemeinsame Kartenfläche der Seiten Erzählung (index), Karte (karta) und Steckbrief (dzielnica).
   Baut eine MapLibre-Karte mit der eigenen Grundkarte (daten/grundkarte.js über KIEZ_THEMEN.grundkarte), den
   Stadtteilen (KIEZ_STADTTEILE) und, falls geladen oder nachgeladen, dem 1-km-Gitter (KIEZ_ZELLEN).
   Braucht vorher: daten/ort.js, i18n.js, texte/<lang>/erzaehlung.js, daten/stadtteile_odbl.js,
   vendor/maplibre-gl.js, daten/grundkarte.js, themen.js. Setzt window.KIEZ_KARTE (eine Karte je Seite).
   Zahlen kommen nur aus daten/*.js; hier steht keine Ergebniszahl von Hand. Klassengrenzen in Metern und Prozent
   sind Methode (die Legende nennt sie), keine Ergebnisse.
   Die Bildzeilen stehen ausgeklappt in der Karte (Lizenzpflicht), nicht hinter einem Knopf; Beschriftungen oben. */
(function () {
"use strict";
var T = window.KIEZ_THEMEN, ORT = window.KIEZ_ORT, ST = window.KIEZ_STADTTEILE, I18N = window.KIEZ_I18N;
if (!T || !ORT || !I18N) return;
var tt = I18N.t, RUHIG = matchMedia("(prefers-reduced-motion: reduce)").matches;
var LEER = { type: "FeatureCollection", features: [] };

// Weg zur Atlas-Wurzel (Seiten in en/ und de/ liegen eine Ebene tiefer): aus dem Verweis auf daten/ort.js
var WURZEL = (function () {
  // Die Deploy-Kopie hängt ?v=<Stand> an (skripte/deploy_kopie.py); ohne Abfrageteil vergleichen, sonst laden die
  // Sprachordner nachgeladene Dateien relativ zu sich selbst (en/daten/… → 404)
  var s = [].slice.call(document.querySelectorAll('script[src*="daten/ort.js"]')).filter(function (x) {
    return /(^|\/)daten\/ort\.js(\?[^#]*)?$/.test(x.getAttribute("src"));
  })[0];
  return s ? s.getAttribute("src").replace(/daten\/ort\.js(\?[^#]*)?$/, "") : "";
})();
function pfad(rel) { return WURZEL + rel; }
// Datei nachladen (per <script>, läuft auch über file://); danach Kennzeichnung Beispieldaten neu prüfen
function laden(rel, global, fertig) {
  T.laden(pfad(rel), global, function (d) { if (window.KIEZ_BEISPIEL_PRUEFEN) window.KIEZ_BEISPIEL_PRUEFEN(); fertig(d); });
}

function el(tag, cls, text) { var e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; }

// Fünf Stufen wie die Zellkarte (themen.js), Grau für unscharfe oder fehlende Werte
var STUFEN = T.STUFEN, GRAU = T.GRAU;
var TEILE_DECKKRAFT = 0.28;   // Füllung der Stadtteile in der Ansicht nach Gruppen (Karte und Legendenfeld)
// Ausdruck: Wert v (MapLibre-Ausdruck) in Stufen nach Grenzen g; kein Zahlwert → Grau
function stufen(v, g) {
  var e = ["step", v, STUFEN[0]];
  g.forEach(function (x, i) { e.push(x, STUFEN[Math.min(i + 1, 4)]); });
  return ["case", ["==", ["typeof", v], "number"], e, GRAU];
}
function stufeVon(w, g) { var i = 0; while (i < g.length && w >= g[i]) i++; return Math.min(i, 4); }

function bauen(feld, o) {
  o = o || {};
  var r = ORT.karte.rahmen;
  var quellen = {}, ebenen = [{ id: "papier", type: "background", paint: { "background-color": "#e6e9e4" } }];
  if (T.GRUNDKARTE) {
    quellen.basemap = ORT.karte.grundkarte;
    ebenen.push({ id: "basemap", type: "raster", source: "basemap" });   // themen.js setzt hier die Vektorebenen ein
  }
  quellen.zellen = { type: "geojson", data: window.KIEZ_ZELLEN || LEER, promoteId: "id", attribution: tt("erzaehlung.bildzeile_gitter") };
  quellen.teile = { type: "geojson", data: ST || LEER, promoteId: "nr", attribution: I18N.sprachwert(ORT.karte.teile_attribution) };
  ebenen.push(
    { id: "zellen-flaeche", type: "fill", source: "zellen", layout: { visibility: "none" }, paint: { "fill-color": STUFEN[0], "fill-opacity": 0.72, "fill-outline-color": "rgba(255,255,255,.55)" } },
    { id: "teile-flaeche", type: "fill", source: "teile", paint: { "fill-color": ["get", "farbe"], "fill-opacity": o.teileDeckkraft == null ? TEILE_DECKKRAFT : o.teileDeckkraft } },
    { id: "teile-linie", type: "line", source: "teile", paint: { "line-color": "#13212a", "line-width": 1.2, "line-opacity": 0.75 } },
    { id: "teile-auswahl", type: "line", source: "teile", filter: ["==", ["get", "nr"], ""], paint: { "line-color": "#6a2c82", "line-width": 3.2 } });
  var map = new maplibregl.Map({
    container: feld,
    style: T.grundkarte({ version: 8, sources: quellen, layers: ebenen }),
    bounds: o.bounds || T.GANZ || [[r[0], r[1]], [r[2], r[3]]], fitBoundsOptions: { padding: 16 },
    maxZoom: 17, attributionControl: false, cooperativeGestures: true, fadeDuration: RUHIG ? 0 : 300,
    dragRotate: false, pitchWithRotate: false, locale: I18N.karteLocale(),
    preserveDrawingBuffer: !!o.druck   // Druckansicht: Kartenbild bleibt im Ausdruck stehen
  });
  map.touchZoomRotate.disableRotation();
  map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
  map.addControl(new maplibregl.ScaleControl({ unit: "metric" }), "bottom-left");
  // Schmale Fenster (bis 860 px) und kleine Karten (Steckbrief, unter 560 px): Quellenzeile einklappbar („i“). MapLibre
  // zeigt sie beim Laden offen und klappt sie beim ersten Verschieben ein; die volle Quelle steht zudem unter jeder Zahl.
  map.addControl(new maplibregl.AttributionControl({ compact: matchMedia("(max-width:860px)").matches || feld.clientWidth < 560 }), "bottom-right");
  // Desktop mit Maus: das Mausrad scrollt die Seite, gezoomt wird per Knopf oder Doppelklick; Touch: zwei Finger
  if (matchMedia("(hover:hover) and (pointer:fine)").matches) { map.scrollZoom.disable(); map.cooperativeGestures.disable(); }
  window.KIEZ_KARTE = map;
  return map;
}

// Kamera auf einen Rahmen [[w,s],[o,n]]; reduzierte Bewegung: springen
function zeige(map, b, pad) {
  var p = pad == null ? 24 : pad;
  if (RUHIG) map.fitBounds(b, { padding: p, animate: false }); else map.fitBounds(b, { padding: p, duration: 1400 });
}
function teilRahmen(nr) { return T.TEIL[nr] ? T.umriss(T.TEIL[nr]) : T.GANZ; }
function zelleRahmen(f) { return T.umriss(f); }
function auswahl(map, nr) { if (map.getLayer("teile-auswahl")) map.setFilter("teile-auswahl", ["==", ["get", "nr"], nr || ""]); }

// Zellen neu setzen (nachgeladenes Gitter)
function zellenSetzen(map) { var q = map.getSource("zellen"); if (q && window.KIEZ_ZELLEN) q.setData(window.KIEZ_ZELLEN); }

// Zellthema aus themen.js (ew, q_u15, q_65p) oder null = aus
function zellThema(map, id) {
  if (!map.getLayer("zellen-flaeche")) return;
  if (!id) { map.setLayoutProperty("zellen-flaeche", "visibility", "none"); return; }
  map.setPaintProperty("zellen-flaeche", "fill-color", T.farbe(T.THEMA[id]));
  map.setLayoutProperty("zellen-flaeche", "visibility", "visible");
}
// Zellen nach eigenen Werten (Liste in Zellreihenfolge) und Grenzen färben, über feature-state
function zellWerte(map, liste, grenzen) {
  var Z = window.KIEZ_ZELLEN; if (!Z || !liste) return;
  Z.features.forEach(function (f, i) { map.setFeatureState({ source: "zellen", id: f.properties.id }, { w: liste[i] == null ? null : liste[i] }); });
  map.setPaintProperty("zellen-flaeche", "fill-color", stufen(["feature-state", "w"], grenzen));
  map.setLayoutProperty("zellen-flaeche", "visibility", "visible");
}
// Stadtteile nach Werten je nr (Objekt nr → Zahl oder null) färben; ohne Werte: Farbton der Gruppe
function teilWerte(map, werte, grenzen) {
  if (!werte) { map.setPaintProperty("teile-flaeche", "fill-color", ["get", "farbe"]); map.setPaintProperty("teile-flaeche", "fill-opacity", TEILE_DECKKRAFT); return; }
  Object.keys(T.TEIL).forEach(function (nr) { map.setFeatureState({ source: "teile", id: nr }, { w: werte[nr] == null ? null : werte[nr] }); });
  map.setPaintProperty("teile-flaeche", "fill-color", stufen(["feature-state", "w"], grenzen));
  map.setPaintProperty("teile-flaeche", "fill-opacity", 0.8);
}
// Quintilgrenzen über eine Werteliste (doppelte Grenzen entfallen), wie themen.js
function quintile(werte) {
  var w = werte.filter(function (v) { return v != null && !isNaN(v); }).sort(function (a, b) { return a - b; }), g = [];
  [0.2, 0.4, 0.6, 0.8].map(function (p) { return w[Math.min(w.length - 1, Math.floor(p * w.length))]; })
    .forEach(function (v) { if (v != null && (!g.length || v > g[g.length - 1])) g.push(v); });
  return g;
}

// Legende: Stufen mit Grenzen; o.einheit (z. B. " %", " m"), o.grau (Text für Grau), o.quelle, o.format
function legende(box, titel, grenzen, o) {
  o = o || {};
  var f = o.format || function (x) { return T.fmt.format(x); }, e = o.einheit || "";
  box.textContent = "";
  box.appendChild(el("p", "fl-titel", titel));
  var ul = el("ul", "fl-stufen"), n = grenzen.length + 1;
  for (var i = 0; i < n; i++) {
    var li = el("li"), sw = el("span", "fl-farbe"); sw.style.background = STUFEN[Math.min(i, 4)];
    var text = n === 1 ? tt("erzaehlung.leg_alle")
      : i === 0 ? tt("erzaehlung.leg_unter", { wert: f(grenzen[0]) + e })
      : i === n - 1 ? tt("erzaehlung.leg_ab", { wert: f(grenzen[i - 1]) + e })
      : tt("erzaehlung.leg_von_bis", { von: f(grenzen[i - 1]), bis: f(grenzen[i]) + e });
    li.appendChild(sw); li.appendChild(el("span", null, text)); ul.appendChild(li);
  }
  if (o.grau) { var lg = el("li"), sg = el("span", "fl-farbe"); sg.style.background = GRAU; lg.appendChild(sg); lg.appendChild(el("span", null, o.grau)); ul.appendChild(lg); }
  box.appendChild(ul);
  if (o.quelle) box.appendChild(el("p", "fl-quelle", o.quelle));
}
// Legende der Gruppen (historische Stadtbezirke): ein Farbton je Gruppe
function legendeGruppen(box) {
  box.textContent = "";
  box.appendChild(el("p", "fl-titel", I18N.sprachwert(ORT.gliederung.gruppe)));
  var ul = el("ul", "fl-stufen");
  ORT.gliederung.gruppen.forEach(function (g) {
    // Feld wie die Fläche auf der Karte: derselbe Ton mit der Deckkraft der Füllung über dem Kartenpapier, der Rand
    // im vollen Ton zur Zuordnung (vorher stand der volle Ton im Feld, auf der Karte erschien er nur blass)
    var c = T.BEZIRKFARBE[g.id], li = el("li"), sw = el("span", "fl-farbe");
    if (c && /^hsl\(/.test(c)) {
      var blass = c.replace(/^hsl\(/, "hsla(").replace(/\)$/, "," + TEILE_DECKKRAFT + ")");
      sw.style.background = "linear-gradient(" + blass + "," + blass + "),#e6e9e4"; sw.style.boxShadow = "inset 0 0 0 1.5px " + c;
    } else sw.style.background = c || GRAU;
    li.appendChild(sw); li.appendChild(el("span", null, g.name)); ul.appendChild(li);
  });
  box.appendChild(ul);
  box.appendChild(el("p", "fl-quelle", I18N.sprachwert(ORT.karte.teile_bildzeile)));
}

window.KIEZ_KARTENFELD = {
  bauen: bauen, zeige: zeige, teilRahmen: teilRahmen, zelleRahmen: zelleRahmen, auswahl: auswahl,
  zellenSetzen: zellenSetzen, zellThema: zellThema, zellWerte: zellWerte, teilWerte: teilWerte,
  quintile: quintile, stufeVon: stufeVon, stufen: stufen, legende: legende, legendeGruppen: legendeGruppen,
  laden: laden, pfad: pfad, el: el, LEER: LEER
};
})();
