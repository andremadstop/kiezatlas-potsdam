/* Kiezatlas Potsdam: Schaugrafik für den Druck (SVG, PNG 300 dpi, Druckansicht/PDF).
   Alles im Browser, ohne Server, auch per Doppelklick (file://). Keine Kartenkacheln: die Karte
   wird aus den eigenen Gitter- und Stadtteildaten gezeichnet. Maße in Millimetern. */
(function () {
"use strict";
var K = window.KIEZ_KENNZAHLEN, ST = window.KIEZ_STADTTEILE, Z = window.KIEZ_ZELLEN, A = window.KIEZ, KT = window.KIEZ_THEMEN;
if (!A || !KT) return;
var fmt = KT.fmt, fmt1 = KT.fmt1, PT = 0.3528, NB = " ";
var INK = "#13212a", MUTED = "#4f5d64", LINE = "#cdd1cc", ACC = "#6a2c82";
var TINTEN = ["#13212a", "#3b7684", "#6a2c82", "#8fb5b3"];
var FORMATE = [
  { id: "a4h", name: "A4 hoch", w: 210, h: 297, r: 14 },
  { id: "a4q", name: "A4 quer", w: 297, h: 210, r: 14 },
  { id: "halb", name: "Halbe Seite quer", w: 210, h: 148, r: 10 },
  { id: "spalte", name: "Spalte", w: 85, h: 230, r: 6 },
  { id: "quadrat", name: "Quadrat", w: 200, h: 200, r: 12 }
];
var RUBRIKEN = [
  { id: "kennzahlen", name: "Kennzahlen", an: true },
  { id: "alter", name: "Alter", an: true },
  { id: "baujahr", name: "Baujahr", an: true },
  { id: "heizung", name: "Heizungsart", an: false },
  { id: "energie", name: "Energieträger", an: false },
  { id: "karte", name: "Karte (Gitter)", an: true },
  { id: "gebaeude", name: "Gebäudezahl (ALKIS)", an: false }
];
var ZAEHLER = 0;
var STICHTAG = (K.stadt.kacheln[0].quelle.match(/Stichtag ([\d.]+)/) || [])[1] || "";

var esc = KT.esc;
function n2(v) { return Math.round(v * 100) / 100; }
function breite(s, pt, fam) { return s.length * pt * PT * (fam === "d" ? 0.47 : 0.5); }
function umbruch(s, maxW, pt, fam) {
  var worte = String(s).split(" "), z = [], cur = "";
  worte.forEach(function (w) { var t = cur ? cur + " " + w : w; if (cur && breite(t, pt, fam) > maxW) { z.push(cur); cur = w; } else cur = t; });
  if (cur) z.push(cur); return z;
}
function T(x, y, s, o) {
  o = o || {}; var pt = o.pt || 9;
  return '<text x="' + n2(x) + '" y="' + n2(y) + '" font-family="' + (o.fam === "d" ? "Barlow Semi Condensed" : "Barlow") + ', sans-serif" font-size="' + n2(pt * PT) +
    '" font-weight="' + (o.w || 400) + '" fill="' + (o.fill || INK) + '"' + (o.anchor ? ' text-anchor="' + o.anchor + '"' : "") +
    (o.halo ? ' paint-order="stroke" stroke="#fff" stroke-width="0.8"' : "") + ">" + esc(s) + "</text>";
}
function zeilen(x, y, s, maxW, o) {   // mehrzeiliger Text, gibt {s, h}
  var pt = o.pt || 9, lh = pt * PT * (o.lh || 1.3), ls = umbruch(s, maxW, pt, o.fam), out = "";
  ls.forEach(function (l, i) { out += T(x, y + pt * PT * 0.8 + i * lh, l, o); });
  return { s: out, h: ls.length * lh };
}
function linie(x1, y1, x2, y2, w, c) { return '<line x1="' + n2(x1) + '" y1="' + n2(y1) + '" x2="' + n2(x2) + '" y2="' + n2(y2) + '" stroke="' + (c || INK) + '" stroke-width="' + w + '"/>'; }
function rect(x, y, w, h, c) { return '<rect x="' + n2(x) + '" y="' + n2(y) + '" width="' + n2(Math.max(0, w)) + '" height="' + n2(h) + '" fill="' + c + '"/>'; }
function G(nr) { return nr ? K.stadtteile[nr] : K.stadt; }

// ---------- Bausteine: (x, y, w) -> {s, h}
function kopf(o, x, y, w, klein) {
  var s = "", h = 0, ein = o.gebiete.length === 1, nr = o.gebiete[0];
  s += T(x, y + 3, "Kiezatlas Potsdam", { pt: 8, w: 600, fill: ACC }); h += 6;
  var titel = ein ? KT.name(nr) + " in Zahlen" : o.gebiete.map(KT.name).join(", ").replace(/, ([^,]*)$/, " und $1") + " im Vergleich";
  var t = zeilen(x, y + h, titel, w, { pt: klein ? 17 : 24, fam: "d", w: 600, lh: 1.02 }); s += t.s; h += t.h + 1.5;
  var sub = ein ? (nr ? "Stadtteil " + nr + " der Landeshauptstadt Potsdam, " : "Landeshauptstadt Potsdam, ") + fmt1.format(G(nr).flaeche_km2) + " km². "
    : "Vergleich von " + o.gebiete.length + " Gebieten. ";
  sub += "Zensus 2022, Stichtag " + STICHTAG + ".";
  var u = zeilen(x, y + h, sub, w, { pt: 9, fill: MUTED }); s += u.s; h += u.h + 3;
  s += linie(x, y + h, x + w, y + h, 0.35); h += 4;
  return { s: s, h: h };
}

function kennwerte(nr, o) {
  var g = G(nr), l = [];
  if (o.rubriken.kennzahlen) g.kacheln.forEach(function (k) {
    l.push({ titel: k.anzeige === "summe" ? k.titel + " (gerundet)" : k.titel, wert: k.wert == null ? "k. A." : k.anzeige === "summe" ? KT.rundEw(k.wert) : fmt1.format(k.wert) + NB + "%" });
  });
  if (o.rubriken.gebaeude) l.push({ titel: "Gebäude laut ALKIS, davon " + fmt.format((g.gebaeude || {}).wohngebaeude || 0) + " Wohngebäude", kurz: "Gebäude laut ALKIS", wert: fmt.format((g.gebaeude || {}).anzahl || 0) });
  if (o.rubriken.gebaeude && o.gebiete.length > 1) l.push({ titel: "davon Wohngebäude", wert: fmt.format((g.gebaeude || {}).wohngebaeude || 0) });
  return l;
}

function kacheln(o, x, y, w) {
  var l = kennwerte(o.gebiete[0], o); if (!l.length) return { s: "", h: 0 };
  var cols = Math.max(1, Math.min(l.length, Math.floor(w / 36))), cw = w / cols, s = "", h = 0, i = 0;
  if (cols === 1) {
    l.forEach(function (k) {
      var t = zeilen(x + 30, y + h + 1.5, k.titel, w - 30, { pt: 8.5 });
      s += T(x, y + h + 7, k.wert, { pt: 17, fam: "d", w: 600 }) + t.s;
      var rh = Math.max(9, t.h + 3); s += linie(x, y + h + rh, x + w, y + h + rh, 0.2, LINE); h += rh + 1.5;
    });
    return { s: s, h: h + 2 };
  }
  while (i < l.length) {
    var reihe = l.slice(i, i + cols), rh = 0, rs = "";
    reihe.forEach(function (k, j) {
      var xx = x + j * cw, t = zeilen(xx, y + h + 10, k.titel, cw - 4, { pt: 8.5 });
      rs += T(xx, y + h + 8, k.wert, { pt: 19, fam: "d", w: 600 }) + t.s;
      rh = Math.max(rh, 11 + t.h);
    });
    s += rs + linie(x, y + h + rh + 1.5, x + w, y + h + rh + 1.5, 0.2, LINE); h += rh + 4; i += cols;
  }
  return { s: s, h: h + 1 };
}

function vergleichstabelle(o, x, y, w) {
  var spalten = o.gebiete, lw = w * (w < 100 ? 0.36 : 0.4), vw = (w - lw) / spalten.length, s = "", h = 0, kopfH = 0;
  var ref = kennwerte(spalten[0], o); if (!ref.length) return { s: "", h: 0 };
  spalten.forEach(function (nr, j) {
    var xx = x + lw + (j + 1) * vw, t = umbruch(KT.name(nr), vw - 2, 8.5, "t");
    t.forEach(function (z, k) { s += T(xx, y + 3.2 + k * 3.6, z, { pt: 8.5, w: 600, anchor: "end" }); });
    s += rect(xx - vw + 2, y + 3.2 + t.length * 3.6 - 1.6, vw - 2, 0.8, TINTEN[j]);
    kopfH = Math.max(kopfH, t.length * 3.6 + 3);
  });
  h = kopfH + 1; s += linie(x, y + h, x + w, y + h, 0.35);
  ref.forEach(function (r, i) {
    var t = zeilen(x, y + h + 1.2, r.kurz || r.titel, lw - 3, { pt: 8.5 }), rh = Math.max(6, t.h + 2.4);
    s += t.s;
    spalten.forEach(function (nr, j) { s += T(x + lw + (j + 1) * vw, y + h + 4.6, kennwerte(nr, o)[i].wert, { pt: 10, fam: "d", w: 600, anchor: "end" }); });
    h += rh; s += linie(x, y + h, x + w, y + h, 0.2, LINE);
  });
  return { s: s, h: h + 4 };
}

function verteilung(key, o, x, y, w) {
  var s = "", h = 0, gs = o.gebiete, ref = G(gs[0]).verteilungen[key];
  var t = zeilen(x, y, A.TITEL[key], w, { pt: 11, fam: "d", w: 600 }); s += t.s; h += t.h + 0.5;
  var note = gs.length === 1 ? "Anteile an " + fmt.format(ref.insgesamt) + " " + ref.einheit + "." : "Anteile an allen " + ref.einheit + " im Gebiet.";
  var u = zeilen(x, y + h, note, w, { pt: 7.5, fill: MUTED }); s += u.s; h += u.h + 1.5;
  var klassen = ref.werte.map(function (wv) { return wv[0]; }).filter(function (lab) {
    if (key !== "energie" && key !== "heizung") return true;
    return gs.some(function (nr) { var v = G(nr).verteilungen[key].werte.filter(function (x2) { return x2[0] === lab; })[0]; return v && v[1] > 0; });
  });
  var anteil = function (nr, lab) { var v = G(nr).verteilungen[key], e = v.werte.filter(function (x2) { return x2[0] === lab; })[0]; return v.insgesamt ? 100 * (e ? e[1] : 0) / v.insgesamt : 0; };
  var max = 0; gs.forEach(function (nr) { klassen.forEach(function (lab) { max = Math.max(max, anteil(nr, lab)); }); }); max = max || 1;
  var vw = 12, lmax = Math.max.apply(null, klassen.map(function (lab) { return breite(lab, 8.5, "t"); })) + 3;
  var lw = Math.min(lmax, w * 0.48), eineZeile = gs.length === 1 && lmax <= w * 0.48 && w - lw - vw >= 18;
  klassen.forEach(function (lab) {
    if (eineZeile) {
      var a = anteil(gs[0], lab), bw = w - lw - vw - 2;
      s += T(x, y + h + 3.2, lab, { pt: 8.5 });
      s += rect(x + lw, y + h + 0.9, bw, 2.8, "#e8ebe6") + rect(x + lw, y + h + 0.9, bw * a / max, 2.8, "#3b7684");
      s += T(x + w, y + h + 3.3, fmt1.format(a) + NB + "%", { pt: 8.5, anchor: "end" });
      h += 5;
    } else {
      s += T(x, y + h + 3.2, lab, { pt: 8.5 }); h += 4.3;
      gs.forEach(function (nr, j) {
        var a = anteil(nr, lab), bw = w - vw - 1;
        s += rect(x, y + h, bw, 2, "#e8ebe6") + rect(x, y + h, bw * a / max, 2, gs.length > 1 ? TINTEN[j] : "#3b7684");
        s += T(x + w, y + h + 2, fmt1.format(a) + NB + "%", { pt: 7.5, anchor: "end", fill: gs.length > 1 ? MUTED : INK });
        h += gs.length > 1 ? 2.9 : 3.4;
      });
      h += 1.2;
    }
  });
  return { s: s, h: h + 5 };
}

function legendeGebiete(o, x, y, w) {
  if (o.gebiete.length < 2) return { s: "", h: 0 };
  var s = "", xx = x, h = 0;
  o.gebiete.forEach(function (nr, j) {
    var lab = KT.name(nr), bw = breite(lab, 8.5, "t") + 8;
    if (xx + bw > x + w && xx > x) { xx = x; h += 5; }
    s += rect(xx, y + h + 1, 3, 3, TINTEN[j]) + T(xx + 4.5, y + h + 3.8, lab, { pt: 8.5 }); xx += bw;
  });
  return { s: s, h: h + 7 };
}

// Karte aus eigenen Daten: Stadtteilflächen + Gitterzellen, keine fremden Kacheln
function karte(o, x, y, w, maxH) {
  var alle = o.gebiete.indexOf("") > -1, teile = alle ? ST.features.map(function (f) { return f.properties.nr; }) : o.gebiete.filter(Boolean);
  var b = [180, 90, -180, -90];
  teile.forEach(function (nr) { var u = KT.umriss(KT.TEIL[nr]); b[0] = Math.min(b[0], u[0][0]); b[1] = Math.min(b[1], u[0][1]); b[2] = Math.max(b[2], u[1][0]); b[3] = Math.max(b[3], u[1][1]); });
  var lat0 = (b[1] + b[3]) / 2, kx = Math.cos(lat0 * Math.PI / 180) * 111320, ky = 110540;
  var mw = (b[2] - b[0]) * kx * 1.06, mh = (b[3] - b[1]) * ky * 1.06, sk = Math.min(w / mw, (maxH - 12) / mh);
  var kw = mw * sk, kh = mh * sk, ox = x + (w - kw) / 2, oy = y;
  var cx = (b[0] + b[2]) / 2, cy = (b[1] + b[3]) / 2;
  function P(c) { return n2(ox + kw / 2 + (c[0] - cx) * kx * sk) + "," + n2(oy + kh / 2 - (c[1] - cy) * ky * sk); }
  function pfad(f) { return KT.polys(f).map(function (p) { return p.map(function (r) { return "M" + r.map(P).join("L") + "Z"; }).join(""); }).join(""); }
  var kid = "sg-kc-" + (++ZAEHLER);
  var s = '<g><clipPath id="' + kid + '"><rect x="' + n2(ox) + '" y="' + n2(oy) + '" width="' + n2(kw) + '" height="' + n2(kh) + '"/></clipPath><g clip-path="url(#' + kid + ')">';
  var t = KT.THEMA[o.kartenthema], gitter = t.id !== "stadtteile", wahl = {}; teile.forEach(function (nr) { wahl[nr] = 1; });
  ST.features.forEach(function (f) {
    var nr = f.properties.nr, an = wahl[nr];
    s += '<path d="' + pfad(f) + '" fill="' + (!gitter && an ? KT.FARBE[nr] : an ? "#eef0ec" : "#f3f4f1") + '" stroke="#ffffff" stroke-width="0.25" fill-rule="evenodd"/>';
  });
  if (gitter) {
    var farben = {};
    Z.features.forEach(function (f) {
      var p = f.properties; if (!wahl[p.st] || p[t.id] == null) return;
      var c = KT.unscharf(t, p) ? KT.GRAU : KT.STUFEN[KT.klasse(t, p[t.id])];
      (farben[c] = farben[c] || []).push("M" + f.geometry.coordinates[0].slice(0, 4).map(P).join("L") + "Z");
    });
    Object.keys(farben).forEach(function (c) { s += '<path d="' + farben[c].join("") + '" fill="' + c + '"/>'; });
  }
  if (!alle) teile.forEach(function (nr) { s += '<path d="' + pfad(KT.TEIL[nr]) + '" fill="none" stroke="' + ACC + '" stroke-width="0.4" fill-rule="evenodd"/>'; });
  else s += ST.features.map(function (f) { return '<path d="' + pfad(f) + '" fill="none" stroke="#9aa3a0" stroke-width="0.15"/>'; }).join("");
  s += "</g></g>";
  // Nummern
  var schrift = alle ? 6.5 : 8;
  teile.forEach(function (nr) { var f = KT.TEIL[nr], q = P([f.properties.lx, f.properties.ly]).split(","); s += '<text x="' + q[0] + '" y="' + q[1] + '" font-family="Barlow Semi Condensed, sans-serif" font-weight="600" font-size="' + n2(schrift * PT) + '" fill="' + INK + '" text-anchor="middle" paint-order="stroke" stroke="#fff" stroke-width="0.6">' + nr + "</text>"; });
  // Maßstab und Norden
  var km = kw / (mw / 1000) > 30 ? 0.5 : 1, mm = km * 1000 * sk, by = oy + kh - 3;
  s += linie(ox + 2, by, ox + 2 + mm, by, 0.5) + T(ox + 2, by - 1.4, (km === 1 ? "1 km" : "500 m"), { pt: 7, fill: INK, halo: true });
  s += '<path d="M' + n2(ox + kw - 4) + "," + n2(oy + 2) + "l1.6,4.2h-3.2z" + '" fill="' + INK + '"/>' + T(ox + kw - 4, oy + 9.6, "N", { pt: 7, anchor: "middle", w: 600 });
  var h = kh + 2;
  // Legende
  var lg = "", lx = Math.max(x, ox);
  if (gitter) {
    var kl = KT.KLASSEN[t.id], r = function (v) { return t.einheit === "Personen" ? fmt.format(Math.round(v)) : fmt1.format(v); };
    lg += T(lx, y + h + 3, t.name + " (" + t.einheit + ")" + (t.id === "ew" ? "" : ", je 100-m-Zelle"), { pt: 8, w: 600 });
    var sw = Math.min(14, (w - 2) / 5);
    KT.STUFEN.slice(0, kl.grenzen.length + 1).forEach(function (c, i) { lg += rect(lx + i * sw, y + h + 4.5, sw - 0.4, 2.4, c); });
    var marken = [kl.min].concat(kl.grenzen, [kl.max]);
    marken.forEach(function (v, i) { lg += T(lx + i * sw, y + h + 10, r(v), { pt: 7, fill: MUTED, anchor: i === 0 ? "start" : i === marken.length - 1 ? "end" : "middle" }); });
    if (t.nenner) lg += rect(lx + 5 * sw + 3, y + h + 4.5, 2.4, 2.4, KT.GRAU) + T(lx + 5 * sw + 6.5, y + h + 6.7, "unscharf, unter 10 " + (t.nenner === "a_ges" ? "Personen" : "Wohnungen"), { pt: 7, fill: MUTED });
    h += 12;
  } else { lg += T(lx, y + h + 3, "Stadtteile, Farbton je Stadtbezirk", { pt: 8, w: 600 }); h += 6; }
  return { s: s + lg, h: h + 3 };
}

function fuss(o, x, w, klein) {
  var teile = [], z = {};
  function zensus(qs) { var m = qs.match(/^(.*?)\s*\(([^)]+)\)\s*$/); if (!m) return; var basis = m[1].replace(/, eigene Auswertung$/, "").replace(/; eigene Auswertung$/, ""); (z[basis] = z[basis] || []).indexOf(m[2]) < 0 && z[basis].push(m[2]); }
  var g = G(o.gebiete[0]);
  if (o.rubriken.kennzahlen) g.kacheln.forEach(function (k) { zensus(k.quelle); });
  ["alter", "baujahr", "heizung", "energie"].forEach(function (k) { if (o.rubriken[k]) zensus(g.verteilungen[k].quelle); });
  if (o.rubriken.karte && o.kartenthema !== "stadtteile") zensus(K.stadt.kacheln[0].quelle);
  Object.keys(z).forEach(function (b) { teile.push(b + "; eigene Auswertung (" + z[b].join(", ") + ")."); });
  teile.push("Stadtteile: © Landeshauptstadt Potsdam, Stand 31.12.2025, dl-zero-de/2.0.");
  if (o.rubriken.gebaeude) teile.push("Gebäude: ALKIS vereinfacht, © GeoBasis-DE/LGB, dl-de/by-2-0 (Daten geändert).");
  teile.push("Kiezatlas Potsdam, Stiebitz Souverain Systems UG (haftungsbeschränkt). Auswertung vom " + new Date(K.stand_auswertung).toLocaleDateString("de-DE") + ".");
  var pt = klein ? 6 : 6.5, s = "", h = 2.5;
  teile.forEach(function (tx) { var t = zeilen(x, h, tx, w, { pt: pt, fill: MUTED, lh: 1.25 }); s += t.s; h += t.h + 0.6; });
  return { s: s, h: h };
}

// ---------- Gesamtlayout
function baueEinmal(o) {
  var f = FORMATE.filter(function (x) { return x.id === o.format; })[0], W = f.w, H = f.h, r = f.r, cw = W - 2 * r, klein = W < 120;
  var k = kopf(o, r, r, cw, klein), y = r + k.h, body = "";
  var ft = fuss(o, r, cw, klein), footY = H - r - ft.h;
  var verts = ["alter", "baujahr", "heizung", "energie"].filter(function (x) { return o.rubriken[x]; });
  var multi = o.gebiete.length > 1, y0 = y;
  var lg = legendeGebiete(o, r, y, cw); body += lg.s; y += lg.h;
  var kz = (o.rubriken.kennzahlen || o.rubriken.gebaeude) ? (multi ? vergleichstabelle(o, r, y, cw) : kacheln(o, r, y, cw)) : { s: "", h: 0 };
  body += kz.s; y += kz.h + (kz.h ? 3 : 0);
  var platz = footY - 4 - y;
  var zwei = cw >= 150, gap = 8, spalten = zwei ? [{ x: r, w: (cw - gap) * (o.rubriken.karte ? 0.5 : 0.5), h: 0 }, { x: r + (cw - gap) / 2 + gap, w: (cw - gap) / 2, h: 0 }] : [{ x: r, w: cw, h: 0 }];
  var bloecke = [], hoch = H > W * 1.2;
  if (o.rubriken.karte && zwei && hoch) {          // Hochformat: Karte über die volle Breite, darunter zwei Spalten
    var ek = karte(o, r, y, cw, Math.max(70, platz * 0.6)); body += ek.s; y += ek.h + 4;
  } else if (o.rubriken.karte) bloecke.push(function (x, yy, w) { return karte(o, x, yy, w, zwei ? Math.max(40, platz - 6) : Math.min(platz * 0.55, w * 1.1)); });
  verts.forEach(function (key) { bloecke.push(function (x, yy, w) { return verteilung(key, o, x, yy, w); }); });
  bloecke.forEach(function (b) {
    var sp = spalten.reduce(function (a, c) { return c.h < a.h ? c : a; });
    var e = b(sp.x, y + sp.h, sp.w); body += e.s; sp.h += e.h + 3;
  });
  var hoehe = (y - y0) + Math.max.apply(null, spalten.map(function (s) { return s.h; }));
  var verfuegbar = footY - 3 - y0, sk = Math.min(1, verfuegbar / Math.max(hoehe, 1));
  var tr = sk < 1 ? ' transform="translate(' + n2(r + cw * (1 - sk) / 2) + "," + n2(y0) + ") scale(" + n2(sk * 1000) / 1000 + ") translate(" + n2(-r) + "," + n2(-y0) + ')"' : "";
  var svg = '<svg xmlns="http://www.w3.org/2000/svg" width="' + W + 'mm" height="' + H + 'mm" viewBox="0 0 ' + W + " " + H + '" role="img" aria-label="Schaugrafik: ' + esc(o.gebiete.map(KT.name).join(", ")) + '">' +
    "<!--FONTS-->" + rect(0, 0, W, H, "#ffffff") + k.s + "<g" + tr + ">" + body + "</g>" +
    linie(r, footY, r + cw, footY, 0.25) + '<g transform="translate(0,' + n2(footY) + ')">' + ft.s + "</g></svg>";
  return { svg: svg, w: W, h: H, skala: sk, format: f };
}
// Passt der Inhalt nicht, wird nicht unter 85 % verkleinert, sondern Rubriken von hinten weggelassen (und genannt).
var NAMEN = {}; RUBRIKEN.forEach(function (x) { NAMEN[x.id] = x.name; });
function baue(o) {
  var r = Object.assign({}, o.rubriken), weg = [], res = baueEinmal(o);
  var reihe = ["energie", "heizung", "baujahr", "alter", "karte", "gebaeude"];
  while (res.skala < 0.85) {
    var naechste = reihe.filter(function (id) { return r[id]; })[0];
    if (!naechste) break;
    r[naechste] = false; weg.push(NAMEN[naechste]);
    res = baueEinmal(Object.assign({}, o, { rubriken: r }));
  }
  res.weg = weg; return res;
}
A.schaugrafik = baue;

// ---------- Formular
var form = document.getElementById("schau-form"); if (!form) return;
var liste = document.getElementById("schau-gebiete"), MAXG = 4;
function haken(name, wert, text, an, typ, extra) {
  var l = document.createElement("label"); l.className = "haken";
  var i = document.createElement("input"); i.type = typ || "checkbox"; i.name = name; i.value = wert; i.checked = !!an;
  l.appendChild(i); l.appendChild(document.createTextNode(" " + text));
  if (extra) { var sm = document.createElement("small"); sm.textContent = extra; l.appendChild(sm); }
  return l;
}
liste.appendChild(haken("gebiet", "", "Ganz Potsdam", true));
ST.features.forEach(function (f) { liste.appendChild(haken("gebiet", f.properties.nr, f.properties.nr + " " + f.properties.name, false)); });
var rb = document.getElementById("schau-rubriken");
RUBRIKEN.forEach(function (x) { rb.appendChild(haken("rubrik", x.id, x.name, x.an)); });
var fb = document.getElementById("schau-format");
FORMATE.forEach(function (x, i) { fb.appendChild(haken("format", x.id, x.name, i === 0, "radio", x.w + " × " + x.h + " mm")); });
var kt = document.getElementById("schau-kartenthema");
KT.THEMEN.forEach(function (t) { kt.appendChild(new Option(t.name, t.id)); }); kt.value = "ew";

function lesen() {
  var g = [].slice.call(form.querySelectorAll('input[name="gebiet"]:checked')).map(function (i) { return i.value; });
  var r = {}; form.querySelectorAll('input[name="rubrik"]').forEach(function (i) { r[i.id || i.value] = i.checked; });
  return { gebiete: g.length ? g : [""], rubriken: r, format: form.querySelector('input[name="format"]:checked').value, kartenthema: kt.value };
}
var aktuell = null;
function zeichne() {
  var o = lesen(), n = o.gebiete.length;
  form.querySelectorAll('input[name="gebiet"]').forEach(function (i) { i.disabled = !i.checked && n >= MAXG; });
  document.getElementById("schau-zaehler").textContent = n + " von höchstens " + MAXG;
  kt.disabled = !o.rubriken.karte;
  aktuell = baue(o);
  var blatt = document.getElementById("schau-blatt"); blatt.dataset.format = o.format;
  blatt.innerHTML = aktuell.svg.replace("<!--FONTS-->", "");
  var sv = blatt.querySelector("svg"); sv.removeAttribute("width"); sv.removeAttribute("height"); blatt.style.setProperty("--ar", (aktuell.w / aktuell.h).toFixed(4));
  document.getElementById("schau-mass").textContent = aktuell.format.name + ", " + aktuell.w + " × " + aktuell.h + " mm";
  var hin = document.getElementById("schau-hinweis");
  hin.textContent = (aktuell.weg.length ? "Passt nicht auf dieses Format und fehlt deshalb: " + aktuell.weg.join(", ") + ". Ein größeres Format oder weniger Rubriken wählen. " : "") +
    (aktuell.skala < 0.85 ? "Die Grafik ist auf " + Math.round(aktuell.skala * 100) + " % verkleinert, die Schrift wird im Druck klein." : "");
}
form.addEventListener("change", zeichne);
A.schauGebiet = function (nr) {
  form.querySelectorAll('input[name="gebiet"]').forEach(function (i) { i.checked = i.value === (nr || ""); });
  zeichne();
};

// ---------- Ausgabe
function schriften() {
  return new Promise(function (ok, fehler) {
    if (window.KIEZ_SCHRIFTEN) return ok(window.KIEZ_SCHRIFTEN);
    var s = document.createElement("script"); s.src = "fonts/einbettung.js";
    s.onload = function () { ok(window.KIEZ_SCHRIFTEN); }; s.onerror = fehler; document.body.appendChild(s);
  });
}
function mitSchriften(svg, F) {
  var css = "@font-face{font-family:'Barlow';font-weight:400;src:url(" + F["barlow-400-normal"] + ") format('woff2')}" +
    "@font-face{font-family:'Barlow';font-weight:600;src:url(" + F["barlow-600-normal"] + ") format('woff2')}" +
    "@font-face{font-family:'Barlow Semi Condensed';font-weight:600;src:url(" + F["barlow-semi-condensed-600-normal"] + ") format('woff2')}";
  return '<?xml version="1.0" encoding="UTF-8"?>\n' + svg.replace("<!--FONTS-->", "<defs><style>" + css + "</style></defs>");
}
function dateiname(ext) {
  var o = lesen(), n = o.gebiete.map(function (g) { return KT.name(g).toLowerCase().replace(/ä/g, "ae").replace(/ö/g, "oe").replace(/ü/g, "ue").replace(/ß/g, "ss").replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, ""); }).join("_");
  return "kiezatlas-" + n + "-" + o.format + "." + ext;
}
function laden(blob, name) {
  var a = document.createElement("a"), u = URL.createObjectURL(blob); a.href = u; a.download = name; document.body.appendChild(a); a.click(); a.remove();
  setTimeout(function () { URL.revokeObjectURL(u); }, 4000);
}
var hinweis = function (t) { document.getElementById("schau-hinweis").textContent = t; };
document.getElementById("schau-svg").addEventListener("click", function () {
  schriften().then(function (F) { laden(new Blob([mitSchriften(aktuell.svg, F)], { type: "image/svg+xml" }), dateiname("svg")); hinweis("SVG erzeugt: " + dateiname("svg") + ". Schriften sind eingebettet."); })
    .catch(function () { hinweis("Die Schriften für den Export konnten nicht geladen werden."); });
});
document.getElementById("schau-png").addEventListener("click", function () {
  var knopf = this; knopf.disabled = true; hinweis("PNG wird gerechnet …");
  schriften().then(function (F) {
    var dpi = 300, pw = Math.round(aktuell.w / 25.4 * dpi), ph = Math.round(aktuell.h / 25.4 * dpi);
    var url = URL.createObjectURL(new Blob([mitSchriften(aktuell.svg, F)], { type: "image/svg+xml" })), img = new Image();
    img.onload = function () {
      setTimeout(function () {
        var c = document.createElement("canvas"); c.width = pw; c.height = ph;
        var x = c.getContext("2d"); x.fillStyle = "#fff"; x.fillRect(0, 0, pw, ph); x.drawImage(img, 0, 0, pw, ph);
        URL.revokeObjectURL(url);
        c.toBlob(function (b) { knopf.disabled = false; if (!b) { hinweis("PNG konnte nicht erzeugt werden."); return; } laden(b, dateiname("png")); hinweis("PNG erzeugt: " + pw + " × " + ph + " Pixel, " + dpi + " dpi bei " + aktuell.w + " × " + aktuell.h + " mm."); }, "image/png");
      }, 120);
    };
    img.onerror = function () { knopf.disabled = false; hinweis("PNG konnte nicht erzeugt werden."); };
    img.src = url;
  }).catch(function () { knopf.disabled = false; hinweis("Die Schriften für den Export konnten nicht geladen werden."); });
});
document.getElementById("schau-druck").addEventListener("click", function () {
  var d = document.getElementById("druck"); d.innerHTML = aktuell.svg.replace("<!--FONTS-->", "").replace(/sg-kc-(\d+)/g, "sg-kc-$1-druck");
  var st = document.createElement("style"); st.id = "druck-seite"; st.textContent = "@page{size:" + aktuell.w + "mm " + aktuell.h + "mm;margin:0}";
  document.head.appendChild(st); document.documentElement.classList.add("druckmodus");
  var weg = function () { document.documentElement.classList.remove("druckmodus"); st.remove(); d.innerHTML = ""; removeEventListener("afterprint", weg); };
  addEventListener("afterprint", weg);
  setTimeout(function () { window.print(); }, 50);
});
zeichne();
})();
