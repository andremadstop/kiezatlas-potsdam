-- Zieltabellen des Kiezatlas Potsdam. Die Geodaten-Import-Pipeline schreibt hinein, die Auswertung
-- (skripte/02_auswerten.py) liest daraus. Alles in EPSG:4326 wie bei MOSIDI.
CREATE EXTENSION IF NOT EXISTS postgis;

-- Amtliche Stadtteile der Landeshauptstadt Potsdam (Open-Data-Portal, Handdownload)
CREATE TABLE stadtteil (
    nr      varchar(4) PRIMARY KEY,
    name    varchar(80) NOT NULL,
    geom    geometry(MultiPolygon, 4326) NOT NULL
);

-- Zensus 2022, 100-m-Gitter, Mittelpunkt der Zelle; Zählwerte, geheim gehaltene Werte als 0
CREATE TABLE zensus_zelle (
    gitter_id  varchar(40) PRIMARY KEY,
    ew         integer,  a_ges integer,  a_u18 integer,  a_18_29 integer,  a_30_49 integer,
    a_50_64    integer,  a_65p integer,  d_alter numeric(5,2),
    h_ges      integer,  h_fern integer, h_etage integer, h_block integer, h_zentral integer,
    h_oefen    integer,  h_keine integer,
    e_ges      integer,  e_gas integer,  e_oel integer,  e_holz integer, e_bio integer, e_wp integer,
    e_strom    integer,  e_kohle integer, e_fern integer, e_kein integer,
    w_ges      integer,  w_v1919 integer, w_1919_48 integer, w_1949_78 integer, w_1979_90 integer,
    w_1991_00  integer,  w_2001_13 integer, w_2014_19 integer, w_2020p integer,
    geom       geometry(Point, 4326) NOT NULL
);

-- Gebäude aus ALKIS vereinfacht (WFS der LGB)
CREATE TABLE gebaeude (
    oid        varchar(20) PRIMARY KEY,
    funktion   varchar(120),
    gebnutzbez varchar(120),
    anzahlgs   integer,
    aktualit   varchar(20),
    geom       geometry(MultiPolygon, 4326) NOT NULL
);

CREATE INDEX ON stadtteil USING gist (geom);
CREATE INDEX ON zensus_zelle USING gist (geom);
CREATE INDEX ON gebaeude USING gist (geom);
