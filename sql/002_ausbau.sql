-- Kiezatlas Potsdam, Ausbau Planer-Ebene (A) und Gebäudejahre (B): Schema, Zieltabellen, Rollenrechte.
-- Eigentümer: Paket P0. Nur P0 schreibt DDL; alle anderen Pakete schreiben Zeilen in ihre eigenen
-- Tabellen (Tabelle 0.4 im Bauplan, Eigentümer je Tabelle im COMMENT).
--
-- Einspielen von Hand als admin (das Volume besteht schon, docker-entrypoint-initdb.d greift nicht):
--   skripte/ausbau_einrichten.py   (spielt diese Datei ein und setzt das Passwort der Rolle
--                                   kiezatlas_rechnen aus RECHNEN_PASSWORD als SCRAM-Hash)
-- Die Datei läuft beliebig oft (IF NOT EXISTS); sie ändert keine bestehende Tabelle aus 001.
--
-- Bezugssysteme: public.* in EPSG:4326 (Vorgabe der Geodaten-Import-Pipeline, ziel.ZIEL_SRID),
-- auswertung.* in EPSG:25833 (metrisch, für Abstände und Flächen), außer dem Gebäude-Snapshot,
-- der eine unveränderte Kopie von public.gebaeude ist.
--
-- Rollen:
--   pipeline_import  schreibt public-Ziele aus config/potsdam.yaml (Rechte vergibt pipeline.einrichten)
--   mosidi_lesen     liest public und auswertung (nicht auswertung.gebaeude_adresse), schreibt nichts
--   kiezatlas_rechnen  liest public, schreibt Zeilen in auswertung (kein CREATE, ALTER, DROP:
--                      Zwischenergebnisse in TEMP-Tabellen). Passwort: RECHNEN_PASSWORD in .env.

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE SCHEMA IF NOT EXISTS auswertung AUTHORIZATION admin;
COMMENT ON SCHEMA auswertung IS 'Abgeleitete Zwischenergebnisse des Kiezatlas-Ausbaus (A, B). DDL nur aus sql/002_ausbau.sql (P0).';

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'kiezatlas_rechnen') THEN
        CREATE ROLE kiezatlas_rechnen NOLOGIN;
    END IF;
END $$;

-- ===================================================================================== public
-- Ziele der Pipeline (config/potsdam.yaml). Rohwerte als Text, wo die Quelle Text liefert
-- (z. B. schueler = '478 (Stand: 2022)'); Auswertung in auswertung.einrichtung (A2).

-- Zensus 2022, Strukturmerkmale im 100-m-Gitter (A1 bereitet vor und lädt per --nur zensus_struktur).
-- Nur Zellen, für die Destatis eine Zeile liefert. '–' (genau null oder durch die Cell-Key-Methode
-- auf null geändert) wird 0; die Felder mit '–' stehen in geaendert (kommagetrennt).
CREATE TABLE IF NOT EXISTS public.zensus_struktur (
    gitter_id   varchar(40) PRIMARY KEY,
    -- Alter in infrastrukturellen Altersgruppen (Personen)
    i_ges integer, i_u3 integer, i_3_5 integer, i_6_9 integer, i_10_15 integer, i_16_18 integer,
    i_19_24 integer, i_25_39 integer, i_40_59 integer, i_60_66 integer, i_67_74 integer, i_75p integer,
    -- Größe des privaten Haushalts (Haushalte)
    hh_ges integer, hh_1 integer, hh_2 integer, hh_3 integer, hh_4 integer, hh_5 integer, hh_6p integer,
    -- Typ des privaten Haushalts nach Familien (Haushalte)
    ht_ges integer, ht_single integer, ht_paar_ohne integer, ht_paar_mit integer, ht_alleinerz integer,
    ht_mehrpers integer,
    -- Typ der Kernfamilie nach Kindern (Familien)
    kf_ges integer, kf_ehe_ohne integer, kf_ehe_u18 integer, kf_ehe_ab18 integer, kf_lp_ohne integer,
    kf_lp_u18 integer, kf_lp_ab18 integer, kf_nel_ohne integer, kf_nel_u18 integer, kf_nel_ab18 integer,
    kf_vater_u18 integer, kf_vater_ab18 integer, kf_mutter_u18 integer, kf_mutter_ab18 integer,
    -- Seniorenstatus eines privaten Haushalts (Haushalte)
    sen_ges integer, sen_nur integer, sen_mit integer, sen_ohne integer,
    -- Staatsangehörigkeit in Gruppen (Personen)
    st_ges integer, st_de integer, st_ausland integer, st_eu27 integer, st_europa integer, st_welt integer,
    st_sonst integer,
    -- Mittelwerte (leer = geheim oder ohne Wert, nie 0)
    miete_qm numeric(8,2), leer_quote numeric(6,2), wfl_je_bew numeric(8,2),
    geaendert   text,
    geom        geometry(Point, 4326) NOT NULL
);
COMMENT ON TABLE public.zensus_struktur IS 'A1 (lädt per Pipeline --nur zensus_struktur). © Statistische Ämter des Bundes und der Länder, Zensus 2022, dl-de/by-2-0. Feine Klassen nie je Zelle veröffentlichen.';

-- MBJS Brandenburg, Kita-Standorte (WFS ms:KITA_Standorte). Ohne Adresse, ohne Kontaktdaten.
CREATE TABLE IF NOT EXISTS public.mbjs_kita (
    id_kita          varchar(20) PRIMARY KEY,
    name             text,
    einrichtungsart  text,
    altersstruktur   text,
    kapazitaet       text,
    ortsteil         text,
    plz              varchar(10),
    ort              text,
    geom             geometry(Point, 4326) NOT NULL
);
COMMENT ON TABLE public.mbjs_kita IS 'P0 lädt per Pipeline --nur mbjs_kita, A2 liest. © Ministerium für Bildung, Jugend und Sport, dl-de/by-2-0. Ohne Telefon, Fax, E-Mail, Straße.';

-- MBJS Brandenburg, Schulstandorte (WFS ms:Schul_Standorte). Ohne Telefon, Fax, Dienst-E-Mail.
CREATE TABLE IF NOT EXISTS public.mbjs_schule (
    schul_nr           varchar(20) PRIMARY KEY,
    schulname          text,
    plz                varchar(10),
    ort                text,
    kreis              text,
    schulamt_nr        varchar(10),
    schulform_kurzbez  varchar(20),
    schulform          text,
    schulformgrp_sl    varchar(10),
    traeger            text,
    schultraeger_grp   varchar(10),
    schueler           text,
    besonderheiten_sl  text,
    geom               geometry(Point, 4326) NOT NULL
);
COMMENT ON TABLE public.mbjs_schule IS 'P0 lädt per Pipeline --nur mbjs_schule, A2 liest. © Ministerium für Bildung, Jugend und Sport, dl-de/by-2-0. Ohne Telefon, Fax, Dienst-E-Mail, Straße.';

-- ALKIS vereinfacht, tatsächliche Nutzung (WFS ave:Nutzung der LGB)
CREATE TABLE IF NOT EXISTS public.alkis_nutzung (
    oid       varchar(20) PRIMARY KEY,
    nutzart   text,
    bez       text,
    name      text,
    aktualit  varchar(20),
    geom      geometry(MultiPolygon, 4326) NOT NULL
);
COMMENT ON TABLE public.alkis_nutzung IS 'P0 lädt per Pipeline --nur alkis_nutzung, A2 liest. © GeoBasis-DE/LGB, dl-de/by-2-0. aktualit ist das Fortführungsdatum, kein Baujahr.';

-- Planungsräume der Landeshauptstadt (Handdownload H1, Open-Data-Portal; Lizenz beim Download ablesen).
-- Vorbereitung: skripte/03_planungsraeume.py -> vorbereitet/planungsraeume.csv, Laden per --nur planungsraeume.
CREATE TABLE IF NOT EXISTS public.planungsraum (
    nr    varchar(10) PRIMARY KEY,
    name  varchar(120),
    geom  geometry(MultiPolygon, 4326) NOT NULL
);
COMMENT ON TABLE public.planungsraum IS 'P0-Ladekoordinator lädt nach Eingang von H1, A6/A8 lesen. Lizenz laut Handdownload (QUELLEN.md).';

CREATE INDEX IF NOT EXISTS zensus_struktur_geom_idx ON public.zensus_struktur USING gist (geom);
CREATE INDEX IF NOT EXISTS mbjs_kita_geom_idx ON public.mbjs_kita USING gist (geom);
CREATE INDEX IF NOT EXISTS mbjs_schule_geom_idx ON public.mbjs_schule USING gist (geom);
CREATE INDEX IF NOT EXISTS alkis_nutzung_geom_idx ON public.alkis_nutzung USING gist (geom);
CREATE INDEX IF NOT EXISTS planungsraum_geom_idx ON public.planungsraum USING gist (geom);

-- ================================================================================= auswertung

-- Stand-Snapshot der Gebäude (Korrektur 16): Teil B bezieht sich nur hierauf, nie auf public.gebaeude,
-- dessen oid sich bei einem neuen Pipeline-Lauf ändern kann. Kein gebaeude-Lauf, solange Teil B läuft.
CREATE TABLE IF NOT EXISTS auswertung.gebaeude_stand_20261105 AS
    SELECT oid, funktion, gebnutzbez, anzahlgs, aktualit, geom FROM public.gebaeude;
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'gebaeude_stand_20261105_pkey') THEN
        ALTER TABLE auswertung.gebaeude_stand_20261105 ADD CONSTRAINT gebaeude_stand_20261105_pkey PRIMARY KEY (oid);
    END IF;
END $$;
CREATE INDEX IF NOT EXISTS gebaeude_stand_20261105_geom_idx ON auswertung.gebaeude_stand_20261105 USING gist (geom);
COMMENT ON TABLE auswertung.gebaeude_stand_20261105 IS 'P0: unveränderte Kopie von public.gebaeude am 05.11.2026 (85.046 Gebäude im Rechteck, EPSG:4326). Nur lesen. © GeoBasis-DE/LGB, dl-de/by-2-0.';

-- A2: Einrichtungen (MBJS amtlich; dazu Gemeinbedarf aus ALKIS nur als Lage, Korrektur 12)
-- art: kita, hort, grundschule, sek1, gymnasium, foerderschule, osz, sonstige_schule,
--      dazu aus ALKIS: jugend, senioren, bibliothek, sport, buergerhaus, feuerwehr, sonstiger_gemeinbedarf
-- status: 'kapazitaet' (Plätze bzw. Schüler bekannt) oder 'lage_ohne_kapazitaet'
CREATE TABLE IF NOT EXISTS auswertung.einrichtung (
    id              text PRIMARY KEY,
    art             text NOT NULL,
    unterart        text,
    name            text,
    plaetze         integer,
    schueler        integer,
    schueler_stand  text,
    altersstruktur  text,
    status          text NOT NULL DEFAULT 'kapazitaet' CHECK (status IN ('kapazitaet', 'lage_ohne_kapazitaet')),
    quelle          text NOT NULL,
    lizenz          text NOT NULL,
    stand           date,
    in_potsdam      boolean NOT NULL,
    geom            geometry(Point, 25833) NOT NULL
);
COMMENT ON TABLE auswertung.einrichtung IS 'A2 (skripte/11_einrichtungen.py). Keine Telefon-, Fax- oder E-Mail-Spalte. dl-de/by-2-0 je Quelle.';

-- A2: Grünflächen (Definition in config/richtwerte.yaml, Abschnitt gruen_definition)
CREATE TABLE IF NOT EXISTS auswertung.gruenflaeche (
    id          text PRIMARY KEY,
    art         text NOT NULL,
    bez         text,
    flaeche_m2  numeric(14,1) NOT NULL,
    quelle      text NOT NULL,
    lizenz      text NOT NULL,
    geom        geometry(MultiPolygon, 25833) NOT NULL
);
COMMENT ON TABLE auswertung.gruenflaeche IS 'A2 (skripte/11_einrichtungen.py) aus public.alkis_nutzung. © GeoBasis-DE/LGB, dl-de/by-2-0, Daten verändert (eigene Berechnung).';

-- A3: OSM-Einrichtungen, ohne Namen (Ärzte, Apotheken, Märkte, Pflege, Spielplätze)
CREATE TABLE IF NOT EXISTS auswertung.osm_poi (
    osm_id    text PRIMARY KEY,
    art       text NOT NULL,
    unterart  text,
    geom      geometry(Point, 25833) NOT NULL
);
COMMENT ON TABLE auswertung.osm_poi IS 'ODbL 1.0, © OpenStreetMap-Mitwirkende. A3 (skripte/12_osm.py). Keine Spalte name. Ableitungen nur in *_odbl-Dateien.';

-- A3: Fußwegnetz (aus dem Hand-PBF, offline)
CREATE TABLE IF NOT EXISTS auswertung.netz_knoten (
    id    bigint PRIMARY KEY,
    geom  geometry(Point, 25833) NOT NULL
);
COMMENT ON TABLE auswertung.netz_knoten IS 'ODbL 1.0, © OpenStreetMap-Mitwirkende. A3 (skripte/12_osm.py).';
CREATE TABLE IF NOT EXISTS auswertung.netz_kante (
    id        bigint PRIMARY KEY,
    von       bigint NOT NULL,
    nach      bigint NOT NULL,
    laenge_m  numeric(10,2) NOT NULL,
    geom      geometry(LineString, 25833)
);
COMMENT ON TABLE auswertung.netz_kante IS 'ODbL 1.0, © OpenStreetMap-Mitwirkende. A3 (skripte/12_osm.py).';

-- A4: Haltestellen mit Taktklasse nach NVP 2019 (Klassengrenzen in config/richtwerte.yaml)
CREATE TABLE IF NOT EXISTS auswertung.haltestelle (
    stop_id                  text PRIMARY KEY,
    name                     text,
    verkehrsmittel           text,
    fahrten_hvz_je_richtung  numeric(6,1),
    klasse                   text CHECK (klasse IN ('I', 'II', 'III', 'unter III')),
    in_potsdam               boolean,
    geom                     geometry(Point, 25833) NOT NULL
);
COMMENT ON TABLE auswertung.haltestelle IS 'A4 (skripte/13_oepnv.py). VBB-GTFS, CC BY 4.0 VBB Verkehrsverbund Berlin-Brandenburg GmbH, Daten verändert (eigene Berechnung).';

-- A5: Entfernung je Zelle zur nächsten Einrichtung je Art. Zeilen mit methode = fussweg: ODbL.
CREATE TABLE IF NOT EXISTS auswertung.zelle_erreichbar (
    gitter_id      varchar(40) NOT NULL,
    art            text NOT NULL,
    methode        text NOT NULL CHECK (methode IN ('luftlinie', 'fussweg')),
    meter          numeric(10,1),
    minuten        numeric(6,1),
    ziel_id        text,
    quelle_lizenz  text NOT NULL,
    PRIMARY KEY (gitter_id, art, methode),
    CHECK (methode <> 'fussweg' OR quelle_lizenz ILIKE '%ODbL%')
);
COMMENT ON TABLE auswertung.zelle_erreichbar IS 'A5 (skripte/14_erreichbarkeit.py). Luftlinie: dl-de/by-2-0 je Quelle. Fußweg: ODbL 1.0 (OSM-Netz).';

-- A5: Grün je Zelle (Korrektur 22, eigene Tabelle statt Spalte in zelle_erreichbar)
CREATE TABLE IF NOT EXISTS auswertung.zelle_gruen (
    gitter_id      varchar(40) NOT NULL,
    methode        text NOT NULL CHECK (methode IN ('luftlinie', 'fussweg')),
    radius_m       integer NOT NULL,
    m2_gruen       numeric(14,1),
    m2_je_ew       numeric(10,2),
    quelle_lizenz  text NOT NULL,
    PRIMARY KEY (gitter_id, methode, radius_m),
    CHECK (methode <> 'fussweg' OR quelle_lizenz ILIKE '%ODbL%')
);
COMMENT ON TABLE auswertung.zelle_gruen IS 'A5 (skripte/14_erreichbarkeit.py). Grünfläche im Umkreis je Zelle (Definition: config/richtwerte.yaml).';

-- B0: Gebäudeform aus ALKIS-NAS (alkis_p.zip), zugeordnet über die größte Überlappung mit dem Snapshot
CREATE TABLE IF NOT EXISTS auswertung.alkis_nas_gebaeude (
    gml_id        text PRIMARY KEY,
    oid_bezug     varchar(20),
    funktion      text,
    dachform      text,
    bauweise      text,
    geschosse     integer,
    objekthoehe   numeric(7,2),
    baujahr       integer,
    wohnungen     integer,
    ueberlappung  numeric(5,3)
);
CREATE INDEX IF NOT EXISTS alkis_nas_gebaeude_oid_idx ON auswertung.alkis_nas_gebaeude (oid_bezug);
COMMENT ON TABLE auswertung.alkis_nas_gebaeude IS 'B0 (skripte/20_alkis_nas.py). © GeoBasis-DE/LGB, dl-de/by-2-0. Kein Eigentümerfeld. oid_bezug verweist auf auswertung.gebaeude_stand_20261105.';

-- B0: Adressen, nur intern für die Zuordnung (Korrektur 6). Nie in daten/ oder Exporte:
-- die Leserolle mosidi_lesen bekommt kein SELECT.
CREATE TABLE IF NOT EXISTS auswertung.gebaeude_adresse (
    oid_bezug  varchar(20) NOT NULL,
    strasse    text NOT NULL,
    hausnr     text NOT NULL,
    PRIMARY KEY (oid_bezug, strasse, hausnr)
);
COMMENT ON TABLE auswertung.gebaeude_adresse IS 'B0, nur intern (Zuordnung Denkmal/Adresse). Kein Zugriff für mosidi_lesen; nie veröffentlichen.';

-- B1: Zensus-Gebäude nach Baujahr je Zelle (B1 liest die Zips selbst, Korrektur 17; kein Pipeline-Ziel)
-- merkmal: 'jahrzehnte' oder 'mz_klassen'; raster: '100m' oder '1km'
CREATE TABLE IF NOT EXISTS auswertung.zensus_gebaeude_jahr (
    gitter_id  varchar(40) NOT NULL,
    raster     text NOT NULL CHECK (raster IN ('100m', '1km')),
    merkmal    text NOT NULL CHECK (merkmal IN ('jahrzehnte', 'mz_klassen')),
    klasse     text NOT NULL,
    anzahl     integer NOT NULL,
    geaendert  boolean NOT NULL DEFAULT false,
    PRIMARY KEY (gitter_id, merkmal, klasse)
);
COMMENT ON TABLE auswertung.zensus_gebaeude_jahr IS 'B1 (skripte/21_jahre_zensus.py). Gebäude mit Wohnraum, nicht einzelne Gebäude. © Statistische Ämter des Bundes und der Länder, Zensus 2022, dl-de/by-2-0.';

-- B2: genaue Jahre mit Beleg. OSM und Wikipedia nur als Prüfwert (Korrektur 5, E1).
CREATE TABLE IF NOT EXISTS auswertung.jahr_beleg (
    id            bigserial PRIMARY KEY,
    oid_bezug     varchar(20),
    jahr_von      integer,
    jahr_bis      integer,
    art           text NOT NULL CHECK (art IN ('bau', 'umbau', 'unklar')),
    genau         boolean NOT NULL,
    nur_pruefung  boolean NOT NULL DEFAULT false,
    quelle        text NOT NULL,
    lizenz        text NOT NULL,
    beleg_url     text NOT NULL,
    CHECK (nur_pruefung OR (quelle !~* '(openstreetmap|wikipedia|\mosm\M)' AND lizenz !~* '(odbl|by-sa)'))
);
CREATE INDEX IF NOT EXISTS jahr_beleg_oid_idx ON auswertung.jahr_beleg (oid_bezug);
COMMENT ON TABLE auswertung.jahr_beleg IS 'B2 (skripte/22_jahre_genau.py). Jede Zeile mit quelle, lizenz, beleg_url. OSM/Wikipedia nur mit nur_pruefung = true.';

-- B3: Luftbild- und Kartenklammern (Pilot)
CREATE TABLE IF NOT EXISTS auswertung.jahr_klammer (
    oid_bezug   varchar(20) NOT NULL,
    nicht_vor   integer,
    nicht_nach  integer,
    quelle      text NOT NULL,
    PRIMARY KEY (oid_bezug, quelle)
);
COMMENT ON TABLE auswertung.jahr_klammer IS 'B3 (skripte/23_luftbild_pilot.py). © GeoBasis-DE/LGB, dl-de/by-2-0, Daten verändert (eigene Berechnung).';

-- B4: Kaskade. Kein OSM- oder Wikipedia-Wert (E1, Korrektur 5); Wohngebäude mit < 3 Wohneinheiten
-- werden nur als Klasse veröffentlicht (Korrektur 6), das regelt die Ausgabe in B4/B5.
CREATE TABLE IF NOT EXISTS auswertung.gebaeude_jahr (
    oid       varchar(20) PRIMARY KEY,
    j         integer,
    j_klasse  text,
    genau     boolean NOT NULL DEFAULT false,
    quelle    text,
    stufe     smallint CHECK (stufe BETWEEN 1 AND 6),
    CHECK (quelle IS NULL OR quelle !~* '(openstreetmap|wikipedia|\mosm\M)')
);
COMMENT ON TABLE auswertung.gebaeude_jahr IS 'B4 (skripte/24_jahre_kaskade.py). oid verweist auf auswertung.gebaeude_stand_20261105. Stufe 6 = nicht datiert.';

-- ===================================================================================== Rechte
-- Nach pipeline.einrichten --haerten hat PUBLIC kein CONNECT mehr: jede Rolle braucht es ausdrücklich.
DO $$ BEGIN
    EXECUTE format('GRANT CONNECT, TEMPORARY ON DATABASE %I TO kiezatlas_rechnen', current_database());
END $$;
REVOKE CREATE ON SCHEMA auswertung FROM PUBLIC;
GRANT USAGE ON SCHEMA public, auswertung TO kiezatlas_rechnen;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO kiezatlas_rechnen;
GRANT SELECT, INSERT, UPDATE, DELETE, TRUNCATE ON ALL TABLES IN SCHEMA auswertung TO kiezatlas_rechnen;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA auswertung TO kiezatlas_rechnen;
-- Der Snapshot bleibt unverändert
REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON auswertung.gebaeude_stand_20261105 FROM kiezatlas_rechnen;

DO $$ BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'mosidi_lesen') THEN
        GRANT USAGE ON SCHEMA auswertung TO mosidi_lesen;
        GRANT SELECT ON ALL TABLES IN SCHEMA auswertung TO mosidi_lesen;
        REVOKE ALL ON auswertung.gebaeude_adresse FROM mosidi_lesen;
    END IF;
END $$;
