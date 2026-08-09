# What is on the objective-prism plates, and what ground truth exists

Written before any extraction method is built, because the work that follows is
scoped by what is actually there.

Every figure below carries the command that produced it. The commands were run
against the services as they answered on the day they were run, and a reader who
re-runs them may get different numbers if an archive has moved. Everything up to
and including the list of published catalogues was run on 2026-08-08. The counts
under `How many spectra carry an independent classification` were run on
2026-08-09. Where a figure could not be established, the entry says so and says
what was run.

Two words are used strictly. Digitised means a scan exists in the archive's own
records. Extracted means a one-dimensional spectrum has been produced from that
scan and published.

## The per-collection table

Plate counts are machine-readable plates, meaning plates the archive records as
scanned. A dash means not established, and the entry below the table says what
was run.

| Collection | Prism plates | Scanned | Dispersion | Wavelength range | Limiting magnitude | Crowded fields | Widened | Published extraction |
|---|---|---|---|---|---|---|---|---|
| First Byurakan Survey, digitised as DFBS | 1874 by its own table, 1729 in the published plate database | 1729 rows in that database, see below | 1800 A/mm near H-gamma, 2500 A/mm near H-beta | 3400-6900 A with a gap at 5300 A | 17.5-18.0 V for the majority, 16.5-19.5 V across plates | designed for high latitude, 28 plates deliberately at low latitude | 5 pixels wide, 107 pixels long at 1.542 arcsec per pixel | yes, catalogue-driven, IRAF apall |
| Hamburg Lippert-Astrograph, in APPLAUSE | 2091 | 2087 | - | - | - | see the latitude figure below | - | - |
| Hamburg Grosser Schmidt-Spiegel, in APPLAUSE | 2094 | 2073 | - | - | - | see below | - | - |
| Hamburg Schmidt-Spiegel at Calar Alto, in APPLAUSE | 1733 | 1716 | - | - | - | see below | - | - |
| Hamburg Schmidtsches Spiegelteleskop, in APPLAUSE | 318 | 307 | - | - | - | see below | - | - |
| Hamburg Kleiner Schmidt-Spiegel II, in APPLAUSE | 150 | 130 | - | - | - | see below | - | - |
| Hamburg Doppel-Reflektor, in APPLAUSE | 1 | 1 | - | - | - | see below | - | - |
| Harvard plate collection, digitised as DASCH | 0 in data release 7 | 0 | not applicable | not applicable | not applicable | not applicable | not applicable | not applicable |
| NAROO | - | - | - | - | - | - | - | - |
| Second Byurakan Survey | - | - | - | - | - | - | - | catalogues exist, see below |

## The Byurakan plates

The survey was taken on the Byurakan 102/132/213 cm Schmidt telescope with a
1.5 degree prism, and its own technical page states the observational
parameters:

    curl -sS https://www.aras.am/Dfbs/fbs.htm

That page gives the dispersion as 1800 A/mm near H-gamma and 2500 A/mm near
H-beta, a mean spectral resolution of about 50 A, a spectral range of
3400-6900 A with a sensitivity gap at 5300 A, a scale of 96.8 arcsec/mm, and a
limiting magnitude of 17.5-18.0 in V, varying between 16.5 and 19.5 across
plates. It gives 1874 plates in 1139 fields in its summary block and 2050
plates in 1133 fields in the prose above it, on the same page.

The digitisation page gives the scan parameters and the size of a spectrum on
the scan:

    curl -sS https://www.aras.am/Dfbs/digitization.htm

Plates were scanned at 1600 dpi, 15.875 micron or 1.542 arcsec per pixel,
9601 by 9601 pixels each, 16 bit. A spectrum is 107 pixels long and 5 pixels
wide. That width is the answer to the widening question for this collection:
the traces are a few pixels across, not tens.

The published plate database is smaller than either plate count on the technical
page:

    curl -sS https://cdsarc.cds.unistra.fr/ftp/VI/116/ReadMe | grep -nE '^[a-z0-9_.]+\.dat'
    58:dfbs.dat     103     1729   The Digitized First Byurakan Survey (DFBS)

So three numbers are in circulation for how many plates this collection has,
1729, 1874 and 2050, and this document does not pick one. The 1729 is the one
that can be read row by row, and it is the one an adapter would work against.

The overview page states the survey holds low-dispersion spectra for 20,000,000
objects and covers more than 17,000 square degrees:

    curl -sS https://www.aras.am/Dfbs/dfbs.html

Crowding. The survey was designed away from the galactic plane, at galactic
latitude above 15 degrees, and the technical page records a deliberate exception:
28 plates were taken in two Milky Way regions in the zones at declination +39 and
+43, covering 171 and 117 square degrees, specifically to test whether
low-dispersion spectra can be worked in crowded regions. That is a small,
identified, crowded subset inside a collection that otherwise avoids crowding,
and it is the most directly relevant material this survey found for the problem
this milestone is about.

Extraction. It has been done and the method is on the record:

    curl -sS https://www.aras.am/Dfbs/extraction.htm

The published procedure is catalogue-driven. Objects are taken from USNO-A2 down
to the plate limit, converted to pixel coordinates, and extracted automatically
with IRAF apall using a template derived from one well-exposed star, with the
sky taken as the mode of a 21 by 150 pixel box centred on each spectrum. That is
detect-then-extract with a fixed aperture, driven by an external catalogue rather
than by detection on the plate. It is the classical baseline decision 0007 names,
and it is already implemented and published for this collection, which makes this
collection the one where a learned method has something concrete to be measured
against.

## The APPLAUSE prism plates

APPLAUSE publishes a table access protocol service, and its plate table carries a
`prism` field. Every count in this section comes from that service.

    curl -sS --data-urlencode "REQUEST=doQuery" --data-urlencode "LANG=ADQL" \
      --data-urlencode "QUERY=SELECT COUNT(*) AS n FROM applause_dr4.plate" \
      https://www.plate-archive.org/tap/sync
    94090

    QUERY=SELECT prism, COUNT(*) AS n FROM applause_dr4.plate GROUP BY prism

That grouping returns 8650 plates with a non-empty `prism` value, spread over 29
distinct prism descriptions. Not all of them are objective prisms. The
descriptions on the Hamburg 1m reflector name a Steinheil spectrograph and
prism trains at fixed focal lengths, which is spectrograph work rather than a
wide-field objective prism, and the Potsdam Zeiss Triplet entries are the bare
codes P1, P2 and P3, which say nothing either way.

Restricting to descriptions naming an objective prism:

    QUERY=SELECT archive_id, COUNT(*) AS n FROM applause_dr4.plate
          WHERE prism LIKE '%Obj%' GROUP BY archive_id ORDER BY COUNT(*) DESC
    102 | 2094
    101 | 2091
    104 | 1733
    111 | 318
    110 | 150
    107 | 1

which is 6387 plates. The archive identifiers resolve through
`applause_dr4.archive`: 101 is the Lippert-Astrograph in Hamburg, 102 the
Grosser Schmidt-Spiegel in Hamburg, 104 the Hamburger Schmidt-Spiegel at Calar
Alto, 107 the Doppel-Reflektor in Hamburg, 110 the Kleiner Schmidt-Spiegel II in
Hamburg, 111 the Schmidtsches Spiegelteleskop in Hamburg.

That string match is a floor and not a boundary. The three Potsdam Small Schmidt
plates described as an `8-degrees prism` are almost certainly objective-prism
plates and are excluded by the match because the description is worded
differently, and the 1993 plates on the Hamburg 1m reflector are excluded on a
reading of their descriptions rather than on a field that declares it. There is
no field in this schema that separates objective prism from spectrograph prism,
so any count here rests on reading free text.

How many are scanned:

    QUERY=SELECT COUNT(DISTINCT p.plate_id) AS n
          FROM applause_dr4.plate AS p
          JOIN applause_dr4.scan AS s ON s.plate_id = p.plate_id
          WHERE p.prism LIKE '%Obj%'
    6314

So 6314 of the 6387 carry a scan. Across all 8650 prism plates the figure is
8546.

Dispersion, wavelength range and limiting magnitude are not established for any
of these plates, and that is a property of the archive rather than of this
survey. The `dispersion` column exists and is empty on every prism plate:

    QUERY=SELECT COUNT(*) AS n FROM applause_dr4.plate
          WHERE prism IS NOT NULL AND LENGTH(prism) > 0 AND dispersion IS NOT NULL
    0

There is no wavelength-range column and no limiting-magnitude column in
`applause_dr4.plate`. The full column list is what the service returns for
`SELECT TOP 1 * FROM applause_dr4.plate`, and it carries `prism`, `prism_angle`,
`dispersion` and `grating` as the whole of its spectroscopic description.

Crowding, for these plates, was derived rather than read, and the derivation is
stated so it can be disputed. The first exposure of each objective-prism plate
was taken from the exposure table:

    QUERY=SELECT exposure.plate_id, exposure.ra_icrs, exposure.dec_icrs
          FROM applause_dr4.exposure
          JOIN applause_dr4.plate
            ON applause_dr4.plate.plate_id = applause_dr4.exposure.plate_id
          WHERE applause_dr4.plate.prism LIKE '%Obj%'
            AND applause_dr4.exposure.exposure_num = 1

That returns 6387 rows, of which 5784 carry usable coordinates. Converting each
to galactic latitude with the J2000 pole at right ascension 192.85948 degrees
and declination 27.12825 degrees, 2314 of the 5784 lie at galactic latitude
below 15 degrees in absolute value.

Read that as a proxy and not as a crowding measurement. Galactic latitude is not
star density, a plate at high latitude can still contain a cluster, and 603
plates have no usable coordinate at all. What it does establish is that the
Hamburg objective-prism material is not a high-latitude survey the way the
Byurakan one is: about two in five of the plates that can be placed sit within
15 degrees of the plane, which is where traces overlap.

No published extraction of these plates was established by this survey. Nothing
was found and nothing was searched exhaustively, so this is an absence of
evidence and is recorded as such.

## The Harvard plates

DASCH states on its own scope page which plates it digitised and which it did
not:

    curl -sS https://dasch.cfa.harvard.edu/dr7/scope/

It gives approximately 430,000 plates digitised, described as virtually all of
the plates believed viable for photometric analysis, and it names what was left
out: "The remaining plates include spectrum observations, ones made with
Pickering wedges or other items in the optical path, severely damaged plates,
lost plates, and so on."

So the largest plate collection on this board contributes no machine-readable
prism spectra at all. That is a decision about what the digitisation was for
rather than a statement that the plates do not exist, and the physical plates
remain in the collection. For this milestone the consequence is simple: an
adapter for this archive is not a route to prism data, and any plan that assumed
it was has to be rewritten.

## NAROO

Not established. The host does not resolve:

    curl -sS -o /dev/null -w "%{http_code}\n" --max-time 20 https://naroo.obspm.fr/
    curl: (6) Could not resolve host: naroo.obspm.fr

    curl -sS -o /dev/null -w "%{http_code}\n" --max-time 20 https://www.obspm.fr/
    301

The second command is there to show that this is the one name and not a general
network failure from this route. Nothing about this archive's prism holdings is
claimed here.

## The ground truth

The load-bearing question is how many of these spectra carry a classification
that a supervised method could be evaluated against, because that number is the
ceiling on what this milestone can measure.

What is published, per catalogue, with the command that produced each count:

    curl -sS https://cdsarc.cds.unistra.fr/ftp/<catalogue>/ReadMe | grep -nE '^[a-z0-9_.]+\.dat'

    VII/172         table7.dat    1469   FBS catalogue of Markarian galaxies
    III/258         fbs.dat       1103   FBS blue stellar objects
    II/223          fbs2.dat      1103   FBS second part
    III/246         catalog.dat    995   FBS late-type stars
    III/266         catalog.dat   1045   revised FBS late-type stars
    J/MNRAS/539/223 catalog.dat   1091   DFBS red objects, third revision
    III/237A        catalog.dat    276   Byurakan-IRAS stars
    VII/276         table6.dat    1863   SBS galaxies
    VII/276         table11.dat   1700   SBS stellar objects
    VII/276         table12.dat    595   SBS quasars

These are not summable and this document does not sum them. III/246, III/266 and
J/MNRAS/539/223 are successive revisions of one late-type star list, and the
Markarian galaxies appear again inside the revised survey catalogues. The order
of magnitude is what matters: a few thousand classified objects against the
20,000,000 spectra the survey overview claims.

Then the harder half. Every catalogue above was classified from these same
plates, by eye, by the people who took them. A method trained on those labels and
evaluated against them is being measured against the classical practice rather
than against the sky, which is a different claim from the one this board wants to
make.

Independent classification, meaning a classification of the same object from a
source other than these plates, was established for one sample at the level of
objects this document can name:

    curl -sS https://cdsarc.cds.unistra.fr/ftp/J/PAZh/44/383/ReadMe | grep -nE '^[a-z0-9_.]+\.dat'
    46:table2.dat     246         81    Parameters of the main emission lines of
    48:table3.dat     605         83    Cross-correlation with 2MASS, IRAS PSC,

That is 83 Byurakan-IRAS galaxies cross-correlated with external surveys and 81
with emission-line parameters measured from SDSS spectra. The section below is a
different kind of number and it is much larger.

## How many spectra carry an independent classification

The count is made from the modern side, because the plate side cannot be queried.
The DFBS object list is not published anywhere a query reaches. VizieR holds seven
tables for this survey and none of them is that list:

    curl -sS -G https://tapvizier.cds.unistra.fr/TAPVizieR/tap/sync \
      --data-urlencode "REQUEST=doQuery" --data-urlencode "LANG=ADQL" \
      --data-urlencode "FORMAT=text" \
      --data-urlencode "QUERY=SELECT table_name FROM TAP_SCHEMA.tables WHERE description LIKE '%Byurakan%'"
    "II/223/fbs2"  "III/237A/catalog"  "III/246/catalog"  "III/266/catalog"
    "J/MNRAS/489/2030/catv2"  "J/PAZh/44/383/bigs"  "VI/116/dfbs"

Six of those are catalogues of objects somebody selected off these plates, and the
seventh is the plate database. The 20,000,000 objects the overview page claims are
not among them, so a match keyed on a DFBS object identifier cannot be made from
here at all.

The question is therefore turned around. Rather than asking which DFBS objects
carry a modern classification, ask how many modern classifications fall inside the
area the digitised plates cover, at a brightness those plates reach.

### The footprint the count is made over

The survey definition is in the plate database's own documentation:

    curl -sS https://cdsarc.cds.unistra.fr/ftp/VI/116/ReadMe

It gives 4 by 4 degree fields, 17,056 square degrees covered, declination above
-15 and galactic latitude above 15 degrees in absolute value. The count uses
exactly that boundary, with galactic latitude computed from the J2000 pole this
document already uses for the APPLAUSE plates, right ascension 192.85948 degrees
and declination 27.12825 degrees. That conversion returns 90.0 at the north
galactic pole, -90.0 at the south, -0.0 at the galactic centre and -21.573 for
M31, whose accepted latitude is -21.57.

The published plate database sits inside that definition rather than filling it
exactly. Its 1729 rows have plate centres from declination -20.81 to +88.76:

    QUERY=SELECT MIN(DEJ2000) AS dmin, MAX(DEJ2000) AS dmax FROM "VI/116/dfbs"
    -20.814166666666665 | 88.76416666666665

and all but nine of them carry an objective prism:

    QUERY=SELECT Prism, COUNT(*) AS n FROM "VI/116/dfbs" GROUP BY Prism
    1.5 | 1720
    3.0 | 4
    4.0 | 1
        | 4

1720 plates of 16 square degrees each is 27,520 square degrees of plate area
against 17,056 square degrees of survey area, so the digitised plates overlap
rather than sampling the footprint sparsely. Read that as an area argument and not
as a coverage map. It does not establish that every point in the footprint lies
under a digitised plate, and no gap map was produced here.

### The count

LAMOST is a modern fibre survey with no relation to these plates, and its data
release 11 low-resolution general catalogue carries a spectral class per spectrum.
The whole catalogue is 11,931,197 rows. Restricted to the footprint above:

    curl -sS -G https://tapvizier.cds.unistra.fr/TAPVizieR/tap/sync \
      --data-urlencode "REQUEST=doQuery" --data-urlencode "LANG=ADQL" \
      --data-urlencode "FORMAT=text" \
      --data-urlencode "QUERY=SELECT Class, COUNT(*) AS n FROM \"V/162/dr11l\"
        WHERE DEJ2000 >= -15
          AND ABS(DEGREES(ASIN(SIN(RADIANS(DEJ2000))*SIN(RADIANS(27.12825))
              + COS(RADIANS(DEJ2000))*COS(RADIANS(27.12825))
              * COS(RADIANS(RAJ2000 - 192.85948))))) >= 15
        GROUP BY Class"
    GALAXY | 275331
    QSO    | 81665
    STAR   | 8282026

8,639,022 classified spectra inside the footprint. The plates reach 17.5 to 18.0
in V, so the same query with `AND "V/162/dr11l"."Gmag" <= 17.5` appended to the
WHERE clause:

    GALAXY | 2242
    QSO    | 4396
    STAR   | 7646682

7,653,320 spectra, which come from

    QUERY=SELECT COUNT(DISTINCT "V/162/dr11l"."GaiaDR3") AS n_obj FROM "V/162/dr11l"
          WHERE <the same footprint clause> AND "V/162/dr11l"."Gmag" <= 17.5
    5071272

distinct sources. That is the count this document can defend for the question at
the head of this section, against the 83 named objects above.

### What that number is not

Each limit below moves the number in a direction that is stated rather than
assumed.

It is a position count and not an association. Every row above is a modern
spectrum whose sky position falls in the footprint. Whether a trace for that
object exists on a digitised plate, and which plate, is not established by this
query and cannot be until the object list exists or a detection run is made on the
scans.

Gaia G is not photographic V. The magnitude cut is applied in Gaia G because that
is the column the catalogue carries for most rows, and the plate limit is quoted
in V. The two agree to within a few tenths for ordinary stars and disagree by more
for red and for extended objects.

The magnitude cut also drops every row that has no Gaia magnitude at all, and
198,634 rows in the footprint have none:

    QUERY=SELECT COUNT(*) AS n FROM "V/162/dr11l"
          WHERE <the same footprint clause> AND "V/162/dr11l"."Gmag" IS NULL

That is part of why the galaxy figure falls from 275,331 to 2,242 and it is not
the whole of it: 273,089 galaxy rows are dropped and at most 198,634 rows of all
classes together can be dropped for a missing magnitude, so the rest are galaxies
the cut reads as fainter than 17.5. Gaia G is a point-source magnitude and an
extended object is measured badly by it either way, so 2,242 is a floor on the
galaxies rather than a count of them. The stellar figure does not have this
problem and it is where almost all of the 5,071,272 sits.

Rows are spectra and repeat observations of one object are separate rows, which is
why the distinct-source figure is given beside the spectrum count.

SDSS was tried on the same footprint and has not answered. The spectroscopic class
in the VizieR copy of data release 16 sits on the photometric catalogue, which is
what makes a grouped count over it expensive. A synchronous request was cut off
after nine minutes with nothing returned, and an asynchronous job carrying the
same query was still reported as `EXECUTING` when this was written. The SDSS side
is not established here, and the LAMOST count stands on its own rather than
standing in for both.

## What this board would need and does not have

The ceiling is no longer the problem. What this board needs and does not have is
the association: a way to say that a particular classified object has a particular
trace on a particular digitised plate. That needs the DFBS object list, which is
not published, or a detection run over the scans, which is the work of #61. Until
one of those exists, five million independent classifications sit next to the
plates without being attached to anything on them.
