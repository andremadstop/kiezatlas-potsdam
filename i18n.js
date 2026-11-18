/* Kiezatlas: Textschicht und Zahlenformate aller Seiten. Schnittstelle und Ladereihenfolge: daten/schema/texte.md. */
(function () {
  "use strict";
  var LOCALE = { pl: "pl-PL", en: "en-GB", de: "de-DE" };
  var lang = (document.documentElement.getAttribute("lang") || "").toLowerCase().split("-")[0];
  if (!LOCALE[lang]) lang = "pl";
  var locale = LOCALE[lang];
  var TEXTE = window.KIEZ_TEXTE = window.KIEZ_TEXTE || {};
  var regeln = new Intl.PluralRules(locale);
  var formate = {};

  function nf(o) {
    var k = o ? JSON.stringify(o) : "";
    return formate[k] || (formate[k] = new Intl.NumberFormat(locale, o));
  }
  var fmt = {
    nf: nf,
    zahl: function (x, stellen) {
      return stellen == null ? nf().format(x) : nf({ minimumFractionDigits: stellen, maximumFractionDigits: stellen }).format(x);
    },
    anteil: function (x, stellen) {
      var s = stellen == null ? 1 : stellen;
      return nf({ style: "percent", minimumFractionDigits: s, maximumFractionDigits: s }).format(x / 100);
    },
    datum: function (d, o) { return new Date(d).toLocaleDateString(locale, o); },
    zeit: function (d, o) { return new Date(d).toLocaleString(locale, o); }
  };

  function t(schluessel, werte) {
    var v = TEXTE[schluessel];
    if (v == null) return schluessel;
    if (typeof v === "object") {
      var n = werte && werte.n;
      if (typeof n !== "number") return schluessel;
      v = v[regeln.select(n)] != null ? v[regeln.select(n)] : v.other;
    }
    return String(v).replace(/\{(\w+)\}/g, function (ganz, name) {
      if (!werte || werte[name] == null) return ganz;
      return name === "n" && typeof werte.n === "number" ? nf().format(werte.n) : String(werte[name]);
    });
  }

  var ORT = window.KIEZ_ORT || {};
  function sprachwert(v) {
    if (v == null || typeof v !== "object" || Array.isArray(v)) return v;
    return v[lang] != null ? v[lang] : v[ORT.standardsprache || "pl"];
  }

  window.KIEZ_LANG = lang;
  window.KIEZ_I18N = {
    lang: lang,
    locale: locale,
    t: t,
    fmt: fmt,
    plural: function (n) { return regeln.select(n); },
    karteLocale: function () { var l = TEXTE["kern.karte_locale"]; return l && typeof l === "object" ? l : {}; },
    sprachwert: sprachwert,
    ort: function (feld) { return sprachwert(ORT[feld]); }
  };
})();
