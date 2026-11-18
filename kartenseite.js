/* Kiezatlas: gemeinsamer Unterbau der Kartenseiten im Textrahmen (Erreichbarkeit, Kamienice, Wohnungsbestand).
   Stellt window.KIEZ_KS bereit: Karte mit Grundkarte und Stadtteilen, Zustand im Hash, Gebäude in 3D auf Wunsch.
   Braucht vorher: daten/ort.js, i18n.js, Texte (Namensraum planer), daten/stadtteile_odbl.js,
   vendor/maplibre-gl.js, daten/grundkarte.js, themen.js. Daten nur per <script> (KIEZ_THEMEN.laden), nie per fetch.

   3D: Gebäude je Stadtteil liegen als daten/gebaeude/<nr>_odbl.js (window.KIEZ_GEB_<nr>, Vertrag
   daten/schema/gebaeude_odbl.json). Geladen wird nur auf ausdrücklichen Wunsch (Knopf „3D“ oder Hash 3d=1) und erst
   ab Zoom 14,5, nur die Stadtteile im Bild. Fehlt eine Datei (die Ablage der 3D-Dateien ist noch offen), meldet die
   Seite das einmal und lädt sie nicht erneut. Die Farbe des Gebäudes zeigt die Herkunft der Höhe (Feld hq). */
(function () {
"use strict";
var T = window.KIEZ_THEMEN, ORT = window.KIEZ_ORT, ST = window.KIEZ_STADTTEILE, I18N = window.KIEZ_I18N;
if (!T || !ORT || !I18N || !window.maplibregl) return;
var t = I18N.t, NB = " ";
var RUHIG = matchMedia("(prefers-reduced-motion: reduce)").matches;
// Atlas-Wurzel aus dem eigenen Skriptpfad (gilt auch in en/ und de/)
var WURZEL = (function () {
  for (var s = document.scripts, k = 0; k < s.length; k++)
    if (/(^|\/)kartenseite\.js$/.test((s[k].src || "").split(/[?#]/)[0])) return new URL("./", s[k].src).href;
  return "";
})();

function el(tag, klasse, text) { var e = document.createElement(tag); if (klasse) e.className = klasse; if (text != null) e.textContent = text; return e; }
function $(id) { return document.getElementById(id); }
function esc(s) { return T.esc(s == null ? "" : s); }
// Vermerke wörtlich, Links anklickbar
function vermerkKnoten(text) {
  var span = el("span", "ks-vermerk"), teile = String(text || "").split(/(https?:\/\/[^\s),”]+)/);
  teile.forEach(function (x, i) {
    if (i % 2) { var a = el("a", "link", x); a.href = x; span.appendChild(a); }
    else if (x) span.appendChild(document.createTextNode(x));
  });
  return span;
}
function zahl(v, stellen) { return v == null ? t("kern.k_a") : I18N.fmt.zahl(v, stellen); }
function anteil(v, stellen) { return v == null ? t("kern.k_a") : I18N.fmt.anteil(v, stellen == null ? 0 : stellen); }
function datum(iso) { return iso ? I18N.fmt.datum(String(iso).slice(0, 10) + "T12:00:00", { day: "numeric", month: "long", year: "numeric" }) : t("kern.k_a"); }
// Sichtprüfung der Denkmalpunkte (daten/denkmale*.js, Feld sichtpruefung): Sätze mit den Zahlen aus den Daten
function geprueft(d) { return !!(d && d.sichtpruefung && d.sichtpruefung.geprueft === true && d.sichtpruefung.ergebnis); }
function sichtLage(sp, e) { var L = e.lage; return t("denkmale.sicht.lage", { n: zahl(e.n), datum: datum(sp.datum), ja: zahl(L.ja), daneben: zahl(L.daneben), nein: zahl(L.nein), q: anteil(L.quote), von: anteil(L.wilson95[0]), bis: anteil(L.wilson95[1]) }); }
function sichtAnsicht(e) { var A = e.ansicht; return t("denkmale.sicht.ansicht", { ja: zahl(A.ja), ent: zahl(A.entschieden), unklar: zahl(A.unklar) }); }
function sichtPunkt(e) { return t("denkmale.sicht.punkt", { q: anteil(e.lage.quote) }); }

// ---------- Zustand im Hash (Schlüssel bleiben deutsch und unsichtbar); k = Kamera zoom/lat/lng/pitch/bearing
function hashLesen() {
  var h = {};
  function dek(x) { try { return decodeURIComponent(x); } catch (e) { return ""; } }
  location.hash.replace(/^#/, "").split("&").forEach(function (p) { var kv = p.split("="); if (kv[0]) h[dek(kv[0])] = dek(kv.slice(1).join("=")); });
  return h;
}
function kameraAusHash(k) {
  if (!k) return null;
  var a = String(k).split("/").map(Number);
  if (a.length < 3 || a.some(isNaN) || a[0] < 0 || a[0] > 22 || Math.abs(a[1]) > 85 || Math.abs(a[2]) > 180) return null;
  return { zoom: a[0], center: [a[2], a[1]], pitch: a[3] || 0, bearing: a[4] || 0 };
}
function hashSchreiben(map, werte) {
  var teile = [];
  Object.keys(werte).forEach(function (k) { var v = werte[k]; if (v !== "" && v != null && v !== false) teile.push(k + "=" + encodeURIComponent(v === true ? "1" : v)); });
  if (map) { var c = map.getCenter(); teile.push("k=" + [map.getZoom().toFixed(2), c.lat.toFixed(5), c.lng.toFixed(5), Math.round(map.getPitch()), Math.round(map.getBearing())].join("/")); }
  try { history.replaceState(null, "", "#" + teile.join("&")); } catch (e) { /* file:// in manchen Browsern */ }
}

// ---------- Karte: Grundkarte, Stadtteile (Linie, Auswahl), eigene Quellen und Ebenen der Seite dazwischen
// o.quellen, o.ebenen (unter den Stadtteilgrenzen), o.oben (über den Grenzen), o.kamera (aus dem Hash)
function karte(o) {
  o = o || {};
  var r = ORT.karte.rahmen, quellen = { basemap: ORT.karte.grundkarte };
  var ebenen = [{ id: "papier", type: "background", paint: { "background-color": "#e6e9e4" } },
    { id: "basemap", type: "raster", source: "basemap" }];
  Object.keys(o.quellen || {}).forEach(function (k) { quellen[k] = o.quellen[k]; });
  ebenen = ebenen.concat(o.ebenen || []);
  if (ST) {
    quellen.teile = { type: "geojson", data: ST, promoteId: "nr", attribution: I18N.sprachwert(ORT.karte.teile_attribution) };
    ebenen.push(
      { id: "teile-flaeche", type: "fill", source: "teile", paint: { "fill-color": "#ffffff", "fill-opacity": ["case", ["boolean", ["feature-state", "gewaehlt"], false], 0.16, 0] } },
      { id: "teile-linie", type: "line", source: "teile", paint: { "line-color": "#13212a", "line-width": 1, "line-opacity": 0.6 } },
      { id: "teile-wahl", type: "line", source: "teile", paint: { "line-color": "#6a2c82", "line-width": ["case", ["boolean", ["feature-state", "gewaehlt"], false], 3, 0] } });
  }
  ebenen = ebenen.concat(o.oben || []);
  var start = o.kamera ? { center: o.kamera.center, zoom: o.kamera.zoom, pitch: o.kamera.pitch, bearing: o.kamera.bearing }
    : { bounds: T.GANZ || [[r[0], r[1]], [r[2], r[3]]], fitBoundsOptions: { padding: 16 } };
  var map = new maplibregl.Map(Object.assign({
    container: "karte",
    style: T.grundkarte({ version: 8, sources: quellen, layers: ebenen }, { vor: o.vor }),
    maxZoom: 18, maxPitch: 60, attributionControl: false, cooperativeGestures: true, fadeDuration: RUHIG ? 0 : 300,
    locale: I18N.karteLocale()
  }, start));
  map.addControl(new maplibregl.NavigationControl({ showCompass: true, visualizePitch: true }), "top-right");
  map.addControl(new maplibregl.ScaleControl({ unit: "metric" }), "bottom-left");
  map.addControl(new maplibregl.AttributionControl({ compact: false }), "bottom-right");
  map.once("load", function () { map.__ksGeladen = true; });
  legendeKnopf();
  window.KIEZ_KARTE = map;
  return map;
}
// Legende ein- und ausklappen: offen am Desktop, am Handy (schmal) zu, damit die Karte frei bleibt. Trägt die Legende
// data-start="zu" (Kamienice: hohe Legende über der Altstadt, die Filterchips der Seitenleiste zeigen die Bauzeiten
// schon), startet sie auch am Desktop zu.
var LEG_OFFEN = !matchMedia("(max-width:860px)").matches && !($("legende") && $("legende").getAttribute("data-start") === "zu"), LEG_KNOPF = null;
function legendeKnopf() {
  var L = $("legende"), k = L && L.parentNode; if (!L || LEG_KNOPF) return;
  LEG_KNOPF = el("button", "chip chip--knopf ks-legende-knopf"); LEG_KNOPF.type = "button";
  LEG_KNOPF.appendChild(el("span", null, t("planer.ks_legende"))); LEG_KNOPF.setAttribute("aria-controls", "legende");
  LEG_KNOPF.addEventListener("click", function () { LEG_OFFEN = !LEG_OFFEN; legendeZeigen(); });
  k.appendChild(LEG_KNOPF); legendeZeigen();
}
function legendeZeigen() {
  var L = $("legende"); if (!L) return;
  L.hidden = !LEG_OFFEN || !L.children.length;
  if (LEG_KNOPF) { LEG_KNOPF.setAttribute("aria-expanded", String(LEG_OFFEN)); LEG_KNOPF.setAttribute("aria-pressed", String(LEG_OFFEN)); }
}

// Stadtteil hervorheben (feature-state); "" hebt auf
function stadtteilWahl(map) {
  var alt = "";
  return function (nr) {
    if (!map.getSource("teile")) return;
    if (alt) map.setFeatureState({ source: "teile", id: alt }, { gewaehlt: false });
    alt = nr && T.TEIL[nr] ? nr : "";
    if (alt) map.setFeatureState({ source: "teile", id: alt }, { gewaehlt: true });
  };
}
function stadtteilName(nr) {
  var g = ORT.gliederung, z = (g.teile || []).filter(function (x) { return x.nr === nr; })[0];
  return z ? I18N.sprachwert(z.anzeige) : nr;
}
function stadtteilAuswahl(sel, leer) {
  sel.innerHTML = "";
  var o0 = el("option", null, leer); o0.value = ""; sel.appendChild(o0);
  (ORT.gliederung.teile || []).forEach(function (x) { var o = el("option", null, I18N.sprachwert(x.anzeige)); o.value = x.nr; sel.appendChild(o); });
}

// ---------- 3D-Gebäude
var HQ_FARBE = { lod2: "#9fb0b6", lod1: "#7f949b", geschosse: "#d9d5c9", ersatz: "#eeebe3", kataster: "#9fb0b6" };
var ZOOM_3D = 14.5;
var KST = { "101": "planer.ks_kst.101", "102": "planer.ks_kst.102", "103": "planer.ks_kst.103", "104": "planer.ks_kst.104", "105": "planer.ks_kst.105",
  "106": "planer.ks_kst.106", "107": "planer.ks_kst.107", "108": "planer.ks_kst.108", "109": "planer.ks_kst.109", "110": "planer.ks_kst.110" };
var HQ_TEXT = { lod2: "planer.ks_hq.lod2", geschosse: "planer.ks_hq.geschosse", ersatz: "planer.ks_hq.ersatz" };
function drei(map, o) {
  o = o || {};
  var knopf = o.knopf, an = false, geladen = {}, fehlt = false, laufend = 0, daten = { type: "FeatureCollection", features: [] };
  var meldung = o.meldung || function () {};
  function farbe() { var e = ["match", ["get", "hq"]]; Object.keys(HQ_FARBE).forEach(function (k) { e.push(k, HQ_FARBE[k]); }); e.push("#eeebe3"); return e; }
  function ebene() {
    if (map.getLayer("geb3d")) return;
    map.addSource("geb3d", { type: "geojson", data: daten, attribution: t("planer.ks_3d_bildzeile") });
    map.addLayer({ id: "geb3d", type: "fill-extrusion", source: "geb3d", minzoom: ZOOM_3D,
      paint: { "fill-extrusion-color": farbe(), "fill-extrusion-height": ["coalesce", ["get", "h"], 3], "fill-extrusion-base": 0, "fill-extrusion-opacity": 0.92 } },
      map.getLayer("teile-linie") ? "teile-linie" : undefined);
  }
  function sichtbareTeile() {
    if (!ST) return [];
    var b = map.getBounds(), x0 = b.getWest(), y0 = b.getSouth(), x1 = b.getEast(), y1 = b.getNorth();
    return ST.features.filter(function (f) { var u = T.umriss(f); return !(u[1][0] < x0 || u[0][0] > x1 || u[1][1] < y0 || u[0][1] > y1); })
      .map(function (f) { return f.properties.nr; });
  }
  function nachladen() {
    if (!an || fehlt || map.getZoom() < ZOOM_3D) { status(); return; }
    var neu = sichtbareTeile().filter(function (nr) { return !geladen[nr]; }).slice(0, 3);
    neu.forEach(function (nr) {
      geladen[nr] = true; laufend++; status();
      T.laden(WURZEL + "daten/gebaeude/" + nr + "_odbl.js", "KIEZ_GEB_" + nr, function (d) {
        laufend--;
        if (!d) { fehlt = true; meldung(t("planer.ks_3d_fehlt")); status(); return; }
        daten.features = daten.features.concat(d.features);
        if (map.getSource("geb3d")) map.getSource("geb3d").setData(daten);
        status(); if (o.bereit) o.bereit();
      });
    });
  }
  function status() {
    var s = !an ? "" : fehlt ? t("planer.ks_3d_fehlt") : map.getZoom() < ZOOM_3D ? t("planer.ks_3d_ab_zoom", { zoom: I18N.fmt.zahl(Math.ceil(ZOOM_3D)) }) : laufend ? t("planer.ks_3d_laedt") : "";
    if (o.hinweis) { o.hinweis.textContent = s; o.hinweis.hidden = !s; }
    if (o.legende) o.legende();
  }
  function setzen(wert, fliegen) {
    an = !!wert;
    if (knopf) knopf.setAttribute("aria-pressed", String(an));
    if (!map.__ksGeladen) { map.once("load", function () { setzen(an, fliegen); }); return; }
    ebene();
    map.setLayoutProperty("geb3d", "visibility", an ? "visible" : "none");
    if (an && fliegen) {
      var z = Math.max(map.getZoom(), 15.2), ziel = { zoom: z, pitch: 50 };
      if (o.ziel && map.getZoom() < ZOOM_3D) ziel.center = o.ziel();
      if (RUHIG) map.jumpTo(ziel); else map.easeTo(Object.assign(ziel, { duration: 900 }));
    } else if (!an && fliegen && map.getPitch() > 0) { if (RUHIG) map.jumpTo({ pitch: 0 }); else map.easeTo({ pitch: 0, duration: 600 }); }
    if (fliegen) map.once("moveend", nachladen); else nachladen();
    status(); if (o.geaendert) o.geaendert();
  }
  if (knopf) knopf.addEventListener("click", function () { setzen(!an, true); });
  map.on("moveend", function () { if (an) nachladen(); });
  map.on("zoomend", status);
  map.on("click", "geb3d", function (e) {
    if (!an || !e.features || !e.features.length) return;
    if (o.klickVorrang && o.klickVorrang(e)) return;
    var p = e.features[0].properties, h = "<b>" + esc(t("planer.ks_gebaeude")) + "</b><table class='pop-tab'>";
    if (KST[p.f]) h += "<tr><td>" + esc(t("planer.ks_art")) + "</td><td>" + esc(t(KST[p.f])) + "</td></tr>";
    h += "<tr><td>" + esc(t("planer.ks_hoehe")) + "</td><td>" + esc(zahl(Number(p.h))) + NB + "m</td></tr>";
    if (p.gs != null && p.gs !== "null") h += "<tr><td>" + esc(t("planer.ks_geschosse")) + "</td><td>" + esc(zahl(Number(p.gs))) + "</td></tr>";
    h += "</table><div class='pop-q'>" + esc(HQ_TEXT[p.hq] ? t(HQ_TEXT[p.hq]) : String(p.hq)) + "</div><div class='pop-q'>" + esc(t("planer.ks_3d_quelle")) + "</div>";
    new maplibregl.Popup({ maxWidth: "300px" }).setLngLat(e.lngLat).setHTML(h).addTo(map);
  });
  // Legende der Höhenherkunft (nur Einträge, nicht die Zahlen; die stehen im Popup)
  function legendeKnoten() {
    if (!an) return null;
    var box = el("div"); box.appendChild(el("p", "ks-legende__titel", t("planer.ks_3d_legende")));
    var ul = el("ul");
    ["lod2", "geschosse", "ersatz"].forEach(function (k) { var li = el("li"), z = el("i", "ks-zeichen ks-zeichen--flaeche"); z.setAttribute("aria-hidden", "true"); z.style.background = HQ_FARBE[k]; li.appendChild(z); li.appendChild(document.createTextNode(t(HQ_TEXT[k]))); ul.appendChild(li); });
    box.appendChild(ul);
    var s = !an ? "" : fehlt ? t("planer.ks_3d_fehlt") : map.getZoom() < ZOOM_3D ? t("planer.ks_3d_ab_zoom", { zoom: I18N.fmt.zahl(Math.ceil(ZOOM_3D)) }) : "";
    if (s) box.appendChild(el("p", null, s));
    return box;
  }
  return { setzen: setzen, an: function () { return an; }, legende: legendeKnoten, laufend: function () { return laufend; } };
}

// ---------- Prüfhilfe: KIEZ_BEREIT, sobald die Karte nach der letzten Änderung still steht
function bereitNach(map, offen) {
  window.KIEZ_BEREIT = false;
  map.once("idle", function () { if (!offen || offen() === 0) window.KIEZ_BEREIT = true; });
  map.triggerRepaint();
}

window.KIEZ_KS = {
  WURZEL: WURZEL, el: el, $: $, esc: esc, vermerkKnoten: vermerkKnoten, zahl: zahl, anteil: anteil, datum: datum,
  geprueft: geprueft, sichtLage: sichtLage, sichtAnsicht: sichtAnsicht, sichtPunkt: sichtPunkt,
  hashLesen: hashLesen, hashSchreiben: hashSchreiben, kameraAusHash: kameraAusHash,
  karte: karte, stadtteilWahl: stadtteilWahl, stadtteilName: stadtteilName, stadtteilAuswahl: stadtteilAuswahl,
  drei: drei, bereitNach: bereitNach, ZOOM_3D: ZOOM_3D, legendeZeigen: legendeZeigen
};
})();
