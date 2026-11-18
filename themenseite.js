/* Kiezatlas: Bausteine der Themenseiten Luft (powietrze), Wohnungsmarkt (mieszkania) und Klima (klimat).
   Zeichnet nur, was die Seitenmodule (seite_*.js) übergeben; Texte kommen fertig übersetzt herein. Dieses Modul fragt
   bewusst keine Schlüssel eines Themen-Namensraums ab (pruefen/texte.py, Punkt 9: sonst müsste jede Seite alle
   Namensräume laden), nur kern.* über KIEZ_I18N. Keine Zahl steht hier fest: alles kommt aus daten/*.js.
   Braucht vorher: daten/ort.js, i18n.js. Schnittstelle: window.KIEZ_TS. */
(function () {
"use strict";
var I18N = window.KIEZ_I18N, SVGNS = "http://www.w3.org/2000/svg";

function el(tag, attrs, kinder) {
  var e = document.createElement(tag);
  Object.keys(attrs || {}).forEach(function (k) {
    var v = attrs[k];
    if (v == null || v === false) return;
    if (k === "text") e.textContent = v;
    else if (k === "class") e.className = v;
    else e.setAttribute(k, v === true ? "" : v);
  });
  (kinder || []).forEach(function (c) { if (c != null) e.appendChild(typeof c === "string" ? document.createTextNode(c) : c); });
  return e;
}
function svg(tag, attrs, kinder) {
  var e = document.createElementNS(SVGNS, tag);
  Object.keys(attrs || {}).forEach(function (k) { if (attrs[k] != null) e.setAttribute(k, attrs[k]); });
  (kinder || []).forEach(function (c) { if (c != null) e.appendChild(typeof c === "string" ? document.createTextNode(c) : c); });
  return e;
}
function leeren(e) { while (e.firstChild) e.removeChild(e.firstChild); return e; }

// Zahlen nur über die Textschicht (Landesbrauch); null → „b.d.“ / „n/a“ / „k. A.“ aus kern.k_a
function zahl(x, stellen) { return x == null ? I18N.t("kern.k_a") : I18N.fmt.zahl(x, stellen); }
function proz(x, stellen) { return x == null ? I18N.t("kern.k_a") : I18N.fmt.anteil(x, stellen == null ? 1 : stellen); }
function datum(iso) { return iso ? I18N.fmt.datum(iso + "T12:00:00", { day: "numeric", month: "long", year: "numeric" }) : I18N.t("kern.k_a"); }

// Kennzeichnung Beispieldaten im Inhalt (zusätzlich zum Hinweis oben im Rahmen): Kasten mit fehlender Quelle,
// Abbildungen schraffiert und mit Marke. opt: { titel, saetze: [...], marke }
function beispiel(kasten, opt) {
  if (!kasten) return;
  leeren(kasten);
  kasten.appendChild(el("p", { class: "ts-beispiel__titel", text: opt.titel }));
  opt.saetze.forEach(function (s) { if (s) kasten.appendChild(el("p", { text: s })); });
  kasten.hidden = false;
  document.documentElement.classList.add("ts-mit-beispiel");
  document.documentElement.style.setProperty("--ts-marke", JSON.stringify(opt.marke));
}

// Tabelle in einem waagerecht scrollbaren, per Tastatur erreichbaren Rahmen (axe: scrollable-region-focusable).
// opt: { titel, spalten: [{ text, zahl }], zeilen: [{ zellen: [Text oder Element], klasse, kopf }], fuss: [...] }
function tabelle(opt) {
  var kopf = el("tr", {}, opt.spalten.map(function (s) { return el("th", { scope: "col", class: s.zahl ? "ts-zahl" : null, text: s.text }); }));
  var koerper = el("tbody", {}, opt.zeilen.map(function (z) {
    return el("tr", { class: z.klasse || null }, z.zellen.map(function (c, i) {
      var s = opt.spalten[i] || {}, attr = { class: s.zahl ? "ts-zahl" : null };
      if (i === 0 && z.kopf !== false) attr.scope = "row";
      var zelle = el(i === 0 && z.kopf !== false ? "th" : "td", attr);
      if (c != null && typeof c === "object") zelle.appendChild(c); else zelle.textContent = c == null ? "" : c;
      return zelle;
    }));
  }));
  var t = el("table", { class: "ts-tabelle" }, [opt.titel ? el("caption", { text: opt.titel }) : null, el("thead", {}, [kopf]), koerper]);
  return el("div", { class: "ts-tabellenrahmen", role: "region", tabindex: "0", "aria-label": opt.titel || null }, [t]);
}

// Balken in einer Tabellenzelle: Wert als Text, Balken nur als Schmuck (aria-hidden)
function balken(text, anteil, klasse) {
  var b = el("span", { class: "ts-balken" + (klasse ? " " + klasse : ""), "aria-hidden": "true" });
  b.style.setProperty("--w", Math.max(0, Math.min(1, anteil || 0)).toFixed(3));
  return el("span", { class: "ts-balkenzelle" }, [el("span", { text: text }), b]);
}

// Linien über Jahre als SVG; Breite aus dem Rahmen, neu gezeichnet bei Größenänderung.
// opt: { rahmen, beschreibung, jahre: [...], einheit, reihen: [{ name, werte: {jahr: {w, offen}}, klasse }],
//        grenzen: [{ y, ab, text }], band: { jahr, text }, fenster: [{ von, bis, text }], format(y) }
function linien(opt) {
  var fig = opt.rahmen;
  function zeichnen() {
    var B = Math.max(280, Math.round(fig.clientWidth || 600)), schmal = B < 520;
    var H = schmal ? 230 : 280, L = schmal ? 42 : 52, R = 12, O = 24, U = 30, ZEILE = 15;
    var jahre = opt.jahre, alle = [];
    // Beschriftungen der Fenster: gemessen, an den Rändern gehalten; wo zwei sich überdecken würden, kommt die
    // spätere eine Zeile höher (die Zeichenfläche rückt dafür nach unten, ihre Höhe bleibt; x() hängt nicht von O ab)
    var breiten = textbreiten((opt.fenster || []).map(function (f) { return f.text; }), fig.querySelector(".ts-zeichnung"));
    var reihenEnde = [], lagen = (opt.fenster || []).map(function (f, i) {
      var w = breiten[i], mitte = Math.min(Math.max((x(f.von) + x(f.bis)) / 2, 2 + w / 2), B - 2 - w / 2), z = 0;
      while (reihenEnde[z] != null && reihenEnde[z] + 8 > mitte - w / 2) z++;
      reihenEnde[z] = mitte + w / 2;
      return { mitte: mitte, zeile: z };
    });
    var extra = Math.max(0, reihenEnde.length - 1) * ZEILE;
    O += extra; H += extra;
    opt.reihen.forEach(function (r) { jahre.forEach(function (j) { var p = r.werte[j]; if (p && p.w != null) alle.push(p.w); }); });
    (opt.grenzen || []).forEach(function (g) { alle.push(g.y); });
    var max = alle.length ? Math.max.apply(null, alle) : 1, schritt = gut(max / 4), top = Math.ceil(max / schritt) * schritt || 1;
    function x(j) { return L + (jahre.length > 1 ? (j - jahre[0]) / (jahre[jahre.length - 1] - jahre[0]) : 0.5) * (B - L - R); }
    function y(v) { return O + (1 - v / top) * (H - O - U); }
    var s = svg("svg", { viewBox: "0 0 " + B + " " + H, width: B, height: H, role: "img", "aria-label": opt.beschreibung, class: "ts-linien" });
    var halb = jahre.length > 1 ? (x(jahre[1]) - x(jahre[0])) / 2 : 10;
    (opt.fenster || []).forEach(function (f, i) {
      s.appendChild(svg("rect", { x: x(f.von) - halb, y: O, width: x(f.bis) - x(f.von) + 2 * halb, height: H - O - U, class: "ts-fenster" }));
      s.appendChild(svg("text", { x: lagen[i].mitte, y: O - 8 - lagen[i].zeile * ZEILE, "text-anchor": "middle", class: "ts-achsentext" }, [f.text]));
    });
    if (opt.band) {
      s.appendChild(svg("rect", { x: x(opt.band.jahr) - halb, y: O, width: 2 * halb, height: H - O - U, class: "ts-band" }));
    }
    for (var v = 0; v <= top + 1e-9; v += schritt) {
      s.appendChild(svg("line", { x1: L, x2: B - R, y1: y(v), y2: y(v), class: "ts-gitter" }));
      s.appendChild(svg("text", { x: L - 6, y: y(v) + 4, "text-anchor": "end", class: "ts-achsentext" }, [opt.format ? opt.format(v) : zahl(v)]));
    }
    var jede = schmal ? Math.ceil(jahre.length / 5) : Math.ceil(jahre.length / 9);
    jahre.forEach(function (j, i) {
      if (i % jede && i !== jahre.length - 1) return;
      s.appendChild(svg("text", { x: x(j), y: H - 10, "text-anchor": "middle", class: "ts-achsentext" }, [String(j)]));
    });
    // Beschriftung über der Linie; liegt sie zu dicht unter der nächsthöheren Beschriftung, kommt sie unter die
    // Linie, und reicht auch das nicht, eine Zeile tiefer (Grenzwerte mit Stufen liegen oft nah beieinander)
    var vorige = -Infinity;
    (opt.grenzen || []).filter(function (g) { return !(g.ab != null && g.ab > jahre[jahre.length - 1]); })
      .sort(function (a, b) { return b.y - a.y; }).forEach(function (g) {
        var x0 = g.ab != null ? Math.max(L, x(Math.max(jahre[0], g.ab)) - halb) : L, ty = y(g.y) - 5;
        if (ty - vorige < ZEILE) ty = Math.max(y(g.y) + 13, vorige + ZEILE);
        vorige = ty;
        s.appendChild(svg("line", { x1: x0, x2: B - R, y1: y(g.y), y2: y(g.y), class: "ts-grenze" }));
        s.appendChild(svg("text", { x: B - R, y: ty, "text-anchor": "end", class: "ts-grenztext" }, [g.text]));
      });
    opt.reihen.forEach(function (r) {
      var d = "", offen = false;
      jahre.forEach(function (j) {
        var p = r.werte[j];
        if (!p || p.w == null) { offen = false; return; }
        d += (offen ? "L" : "M") + x(j).toFixed(1) + " " + y(p.w).toFixed(1);
        offen = true;
      });
      var g = svg("g", { class: "ts-reihe " + (r.klasse || "") });
      if (d) g.appendChild(svg("path", { d: d }));
      jahre.forEach(function (j) {
        var p = r.werte[j];
        if (p && p.w != null) g.appendChild(svg("circle", { cx: x(j), cy: y(p.w), r: r.hervor ? 3.6 : 2.4, class: p.offen ? "ts-offen" : null }));
      });
      s.appendChild(g);
    });
    leeren(fig.querySelector(".ts-zeichnung")).appendChild(s);
  }
  zeichnen();
  var breite = fig.clientWidth;
  if (window.ResizeObserver) new ResizeObserver(function () { if (Math.abs(fig.clientWidth - breite) > 8) { breite = fig.clientWidth; zeichnen(); } }).observe(fig);
  return zeichnen;
}
// Breite von Achsentexten in px, gemessen in einem unsichtbaren SVG im Rahmen; ohne Darstellung geschätzt
function textbreiten(texte, rahmen) {
  if (!texte.length) return [];
  var m = svg("svg", { width: 0, height: 0, class: "ts-linien", "aria-hidden": "true", style: "position:absolute;visibility:hidden" });
  var t = texte.map(function (s) { var e = svg("text", { class: "ts-achsentext" }, [s]); m.appendChild(e); return e; });
  (rahmen || document.body).appendChild(m);
  var w = t.map(function (e, i) { var b = 0; try { b = e.getComputedTextLength(); } catch (x) { b = 0; } return b > 0 ? b : texte[i].length * 7; });
  m.parentNode.removeChild(m);
  return w;
}
// runde Achsenschritte 1, 2, 5 × 10^k
function gut(v) { var p = Math.pow(10, Math.floor(Math.log10(v || 1))), f = v / p; return (f <= 1 ? 1 : f <= 2 ? 2 : f <= 5 ? 5 : 10) * p; }

// Legende: [{ text, klasse }] als Liste mit Musterstrich
function legende(eintraege) {
  return el("ul", { class: "ts-legende" }, eintraege.map(function (e) {
    return el("li", {}, [el("span", { class: "ts-muster " + (e.klasse || ""), "aria-hidden": "true" }), e.text]);
  }));
}

// Quellen: [{ titel, zeilen: [Text | { text, lang } | { link, text }], hinweis }] als Beschreibungsliste
function quellen(dl, eintraege) {
  leeren(dl);
  eintraege.forEach(function (q) {
    dl.appendChild(el("dt", { text: q.titel }));
    var dd = el("dd");
    if (q.hinweis) dd.appendChild(el("p", { class: "ts-quelle-hinweis", text: q.hinweis }));
    q.zeilen.forEach(function (z) {
      if (!z) return;
      if (typeof z === "string") dd.appendChild(el("p", { text: z }));
      else if (z.link) dd.appendChild(el("p", {}, [el("a", { class: "link", href: z.link, rel: "noopener", text: z.text || z.link })]));
      else dd.appendChild(el("p", {}, [z.vor ? z.vor + " " : null, el("q", { lang: z.lang || null, text: z.text })]));
    });
    dl.appendChild(dd);
  });
}

// Auswahl als Knopfgruppe (gleich bedienbar mit Maus, Touch und Tastatur): [{ wert, text }], aktiv, beiWahl(wert)
function knoepfe(rahmen, titel, wahl, aktiv, beiWahl) {
  leeren(rahmen);
  rahmen.setAttribute("role", "group");
  rahmen.setAttribute("aria-label", titel);
  rahmen.appendChild(el("span", { class: "ts-knoepfe__titel", text: titel, "aria-hidden": "true" }));
  wahl.forEach(function (w) {
    var b = el("button", { type: "button", class: "ts-knopf", "aria-pressed": String(w.wert === aktiv), text: w.text });
    b.addEventListener("click", function () {
      rahmen.querySelectorAll(".ts-knopf").forEach(function (x) { x.setAttribute("aria-pressed", String(x === b)); });
      beiWahl(w.wert);
    });
    rahmen.appendChild(b);
  });
}

// Name einer dzielnica in der Seitensprache aus der Ortskonfiguration („Dzielnica I Stare Miasto“)
function teilName(nr) {
  var t = (window.KIEZ_ORT.gliederung.teile || []).filter(function (x) { return x.nr === nr; })[0];
  return t ? I18N.sprachwert(t.anzeige) : nr;
}
function teile() { return (window.KIEZ_ORT.gliederung.teile || []).slice(); }

window.KIEZ_TS = { el: el, leeren: leeren, zahl: zahl, proz: proz, datum: datum, beispiel: beispiel, tabelle: tabelle,
  balken: balken, linien: linien, legende: legende, quellen: quellen, knoepfe: knoepfe, teilName: teilName, teile: teile };
})();
