"""The synthetic plate every gated test draws its fixtures from.

Synthetic plates prove that code handles the failures it was told about, and
they prove nothing whatever about the failures nobody has enumerated.

That sentence is the reason this module exists in the shape it does. What it
produces is a plate carrying, at known positions and with known amplitudes, the
things this pipeline was built to survive: a response curve with a toe and a
shoulder, saturation on the bright end, grain, a vignette, a scratch, a dust
grain, a ghost and a halo. A test that recovers a source through all of that has
shown the arithmetic works on the enumerated set. It has shown nothing about the
emulsion defect nobody has seen yet, and a test that reads a recovery number off
this generator and calls it plate photometry is making a claim this module
cannot support.

Everything is a function of the seed. Two runs with one seed produce identical
bytes, so a fixture is a number in a test rather than a file in the repository,
and a plate that broke something can be named in an issue in four characters.
That identity holds inside one resolved dependency graph, which is what
``uv.lock`` fixes; it is not a claim about two different versions of numpy, and
``numpy.random.RandomState`` is used rather than the newer generator because
numpy's compatibility guarantee covers exactly the former.

The FITS writing here is a writer and not a reader. It emits the smallest header
that is a real one, and ``tests/test_synthetic_plate.py`` proves that with a
reference implementation reading the bytes back rather than with a second reader
written here, which would only prove this file agrees with itself.

The array holds density rather than transmission, scaled into the 16-bit range a
scanner delivers, and ``DATAKIND`` in the header says so. Archives ship both
conventions and a file that does not say which it is is a file that gets
inverted by somebody later.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

# The scan's full range. 16-bit is what the four collections deliver and what a
# plate scanner produces, so a fixture at 8-bit would be easier and would not be
# the thing.
FULL_SCALE = 65535

# FITS is a stream of 2880-byte blocks and an 80-character card. Both numbers are
# the format's, not choices made here.
BLOCK = 2880
CARD = 80

# The characteristic curve. `HALF` is the incident exposure that reaches half of
# `D_MAX`, and `GAMMA` is the contrast: together they put a toe below `HALF` and
# a shoulder above it, which is the shape the emulsion actually has and the shape
# a linear calibration gets wrong at both ends.
D_MAX = 3.2
HALF = 120.0
GAMMA = 1.7

# Where the density ceiling counts as saturation. A source whose peak lands at or
# above this has lost its bright end and its flux cannot be recovered, which is a
# fact the truth table carries rather than something a test rediscovers.
SATURATION = 0.985 * D_MAX


@dataclass(frozen=True)
class Source:
    """A source with a position and a flux that are known rather than measured.

    The three flags are computed from the plate rather than assigned by hand, so
    a change to the recipe that pushes a source into saturation or under an
    artefact moves the flag with it instead of leaving a fixture that quietly
    lies about which of its sources are measurable.
    """

    x: float
    y: float
    flux: float
    sigma: float
    saturated: bool
    contaminated: bool
    in_toe: bool

    @property
    def recoverable(self) -> bool:
        """Whether a flux measured off this source can be compared to its truth.

        The three exclusions are different failures and they are kept apart.
        Saturation destroys the bright end, an artefact adds light that is not
        the source, and the toe compresses the faint end into the grain. A
        fixture that reported one number for all three would hide which of them
        a measurement actually hit.
        """
        return not (self.saturated or self.contaminated or self.in_toe)


@dataclass(frozen=True)
class Artefact:
    """Something on the plate that is not sky, named by what it is.

    Named rather than filtered, which is
    ``docs/decisions/0006-artefacts-are-a-class.md``. A generator that removed
    these would produce fixtures that cannot show a detector confusing one with
    a faint source, and that confusion is the failure this board is about.
    """

    kind: str
    x: float
    y: float
    radius: float


@dataclass(frozen=True)
class Truth:
    """What the generator knows and a measurement is compared against."""

    seed: int
    shape: tuple[int, int]
    background: float
    d_max: float
    half: float
    gamma: float
    saturation: float
    collection: str
    sources: list[Source] = field(default_factory=list)
    artefacts: list[Artefact] = field(default_factory=list)

    def as_json(self) -> str:
        """The truth table as text, so a fixture's answer can leave the process."""
        return json.dumps(asdict(self), indent=2, sort_keys=True)


@dataclass(frozen=True)
class Plate:
    """One synthetic plate: the scan, the header it is written with, the truth."""

    image: NDArray[np.uint16]
    header: list[tuple[str, object, str]]
    truth: Truth
    vignette: NDArray[np.float64]


def density(incident: NDArray[np.float64]) -> NDArray[np.float64]:
    """Incident exposure to density, with a toe below `HALF` and a shoulder above.

    A logistic in the logarithm of exposure, which is the Hurter and Driffield
    shape written in the one line that has it. Below the toe an increase in light
    produces almost no density and above the shoulder it produces almost none
    either, so the same detector step means a different number of photons at the
    two ends. That is the whole reason the response is its own stage in
    ``docs/decisions/0005-photometric-response.md``.
    """
    safe = np.maximum(incident, 1e-9)
    return np.asarray(D_MAX / (1.0 + (HALF / safe) ** GAMMA), dtype=np.float64)


def incident(density_values: NDArray[np.float64]) -> NDArray[np.float64]:
    """Density back to incident exposure, which is the inverse of `density`.

    It is defined only below `D_MAX` and it loses its meaning as it approaches
    it, which is what saturation is. A caller that inverts a saturated pixel gets
    a number, and the number is not a flux.
    """
    clipped = np.clip(density_values, 1e-9, D_MAX - 1e-9)
    return np.asarray(HALF * (clipped / (D_MAX - clipped)) ** (1.0 / GAMMA), dtype=np.float64)


def vignette_field(shape: tuple[int, int]) -> NDArray[np.float64]:
    """The multiplicative falloff from plate centre to corner.

    Deterministic and independent of the seed, so a test that has to correct for
    it can ask for it rather than fit it. A real reduction fits it; a test of
    something else should not have to.
    """
    rows, columns = shape
    y, x = np.mgrid[0:rows, 0:columns].astype(np.float64)
    centre_y, centre_x = (rows - 1) / 2.0, (columns - 1) / 2.0
    radius = np.hypot(y - centre_y, x - centre_x)
    edge = float(np.hypot(centre_y, centre_x))
    return np.asarray(1.0 - 0.35 * (radius / edge) ** 2, dtype=np.float64)


def _gaussian(
    shape: tuple[int, int], x: float, y: float, sigma: float, amplitude: float
) -> NDArray[np.float64]:
    rows, columns = shape
    grid_y, grid_x = np.mgrid[0:rows, 0:columns].astype(np.float64)
    squared = (grid_x - x) ** 2 + (grid_y - y) ** 2
    return np.asarray(
        amplitude * np.exp(-squared / (2.0 * sigma**2)), dtype=np.float64
    )


def _disc(
    shape: tuple[int, int], x: float, y: float, radius: float
) -> NDArray[np.bool_]:
    rows, columns = shape
    grid_y, grid_x = np.mgrid[0:rows, 0:columns].astype(np.float64)
    return np.asarray(
        (grid_x - x) ** 2 + (grid_y - y) ** 2 <= radius**2, dtype=np.bool_
    )


def _annulus(
    shape: tuple[int, int], x: float, y: float, inner: float, outer: float
) -> NDArray[np.bool_]:
    return np.asarray(
        _disc(shape, x, y, outer) & ~_disc(shape, x, y, inner), dtype=np.bool_
    )


def _line(
    shape: tuple[int, int], x0: float, y0: float, x1: float, y1: float, width: float
) -> NDArray[np.bool_]:
    rows, columns = shape
    grid_y, grid_x = np.mgrid[0:rows, 0:columns].astype(np.float64)
    dx, dy = x1 - x0, y1 - y0
    length = float(np.hypot(dx, dy))
    along = ((grid_x - x0) * dx + (grid_y - y0) * dy) / length**2
    nearest_x = x0 + np.clip(along, 0.0, 1.0) * dx
    nearest_y = y0 + np.clip(along, 0.0, 1.0) * dy
    distance = np.hypot(grid_x - nearest_x, grid_y - nearest_y)
    return np.asarray(distance <= width, dtype=np.bool_)


# How far out a flux is summed, in units of the source width. At four widths a
# Gaussian has given up 0.03 per cent of itself, so what a measurement misses at
# this radius is below everything else on the plate. It is here rather than in
# the test because it is also what decides whether a source counts as sitting
# under an artefact.
APERTURE = 4.0

# The fixed grid the sources are laid on, in fractions of the plate. Fixed
# rather than drawn, because a source whose position moves with the seed lands
# under the halo on some seeds and not others, and a fixture whose properties
# depend on which seed you picked is not a fixture. The seed moves the grain,
# the scratch, the dust and a jitter of a couple of pixels, which is what it
# should move.
GRID = (
    (0.18, 0.24),
    (0.72, 0.19),
    (0.24, 0.78),
    (0.80, 0.73),
    (0.45, 0.88),
    (0.55, 0.44),
)

# Fluxes spanning the response curve. The first is in the toe and the last is
# driven past the ceiling, because those two ends are what a linear calibration
# gets wrong and a fixture without them passes a wrong calibration.
FLUXES = (90.0, 520.0, 2100.0, 9000.0, 4200.0, 900000.0)


def plate(seed: int, size: int = 192, collection: str = "synthetic") -> Plate:
    """One plate from one seed, with every parameter derived from it.

    The source list is deliberately spread across the response curve rather than
    placed at comfortable brightnesses: the faintest sits in the toe, the
    brightest is driven past `SATURATION`, and one is placed under the halo, so
    that a recovery measurement has each of the three exclusions to make and a
    test of the exclusions has something to exclude.
    """
    shape = (size, size)
    random = np.random.RandomState(seed)

    background = 18.0
    field_exposure = np.full(shape, background, dtype=np.float64)

    sigma = 1.9
    jitter = random.uniform(-2.0, 2.0, size=(len(GRID) + 1, 2))
    positions = [
        (fx * size + float(jitter[index][0]), fy * size + float(jitter[index][1]))
        for index, (fx, fy) in enumerate(GRID)
    ]
    brightest = int(np.argmax(FLUXES))

    for (x, y), flux in zip(positions, FLUXES, strict=True):
        field_exposure += _gaussian(
            shape, x, y, sigma, flux / (2.0 * np.pi * sigma**2)
        )

    # The halo and the ghost come off the brightest source, so they are placed
    # from it rather than drawn. An optical artefact whose parent moved with the
    # seed would be an artefact with no parent on some seeds.
    halo_x, halo_y = positions[brightest]
    halo_outer, halo_inner = 26.0, 13.0
    field_exposure[_annulus(shape, halo_x, halo_y, halo_inner, halo_outer)] += 260.0

    ghost_x, ghost_y = size - halo_x, size - halo_y
    ghost_radius = 9.0
    field_exposure[_disc(shape, ghost_x, ghost_y, ghost_radius)] += 130.0

    # One source under the halo, bright enough to detect and wrong enough that a
    # measurement which forgot to exclude it reports a number nobody notices is
    # wrong.
    under_halo = (
        halo_x + 17.0 + float(jitter[len(GRID)][0]),
        halo_y + 7.0 + float(jitter[len(GRID)][1]),
    )
    under_halo_flux = 2600.0
    field_exposure += _gaussian(
        shape, under_halo[0], under_halo[1], sigma,
        under_halo_flux / (2.0 * np.pi * sigma**2),
    )

    field_exposure *= vignette_field(shape)
    plate_density = density(field_exposure)

    scratch_x0 = float(random.randint(10, size // 3))
    scratch_width = 1.2
    scratch = _line(
        shape, scratch_x0, 4.0, scratch_x0 + size * 0.6, size - 9.0, scratch_width
    )
    plate_density[scratch] = D_MAX * 0.93

    dust_x = float(random.randint(28, size - 28))
    dust_y = float(random.randint(28, size - 28))
    dust_radius = 3.4
    plate_density[_disc(shape, dust_x, dust_y, dust_radius)] = D_MAX * 0.97

    # Grain last, over everything including the artefacts, because it is a
    # property of the emulsion the whole plate is made of rather than a layer on
    # top of the sky.
    plate_density += random.normal(0.0, 0.012, size=shape)
    plate_density = np.clip(plate_density, 0.0, D_MAX)

    image = np.rint(plate_density / D_MAX * FULL_SCALE).astype(np.uint16)

    artefacts = [
        Artefact("halo", halo_x, halo_y, halo_outer),
        Artefact("ghost", ghost_x, ghost_y, ghost_radius),
        Artefact("scratch", scratch_x0, float(size) / 2.0, scratch_width),
        Artefact("dust", dust_x, dust_y, dust_radius),
    ]
    artefact_mask = (
        _annulus(shape, halo_x, halo_y, halo_inner, halo_outer)
        | _disc(shape, ghost_x, ghost_y, ghost_radius)
        | scratch
        | _disc(shape, dust_x, dust_y, dust_radius)
    )

    catalogue = [*zip(positions, FLUXES, strict=True), (under_halo, under_halo_flux)]
    vignette = vignette_field(shape)
    sources = [
        _describe(
            shape, plate_density, vignette, x, y, flux, sigma, artefact_mask, catalogue
        )
        for (x, y), flux in catalogue
    ]

    truth = Truth(
        seed=seed,
        shape=shape,
        background=background,
        d_max=D_MAX,
        half=HALF,
        gamma=GAMMA,
        saturation=SATURATION,
        collection=collection,
        sources=sources,
        artefacts=artefacts,
    )

    return Plate(
        image=image,
        header=_header(shape, seed, collection),
        truth=truth,
        vignette=vignette,
    )


def _describe(
    shape: tuple[int, int],
    plate_density: NDArray[np.float64],
    vignette: NDArray[np.float64],
    x: float,
    y: float,
    flux: float,
    sigma: float,
    artefact_mask: NDArray[np.bool_],
    catalogue: list[tuple[tuple[float, float], float]],
) -> Source:
    """One catalogue entry with its three exclusions measured off the plate.

    Measured rather than declared. The saturation flag is read out of the
    density that was actually written, the contamination flag out of an
    intersection of masks, and the toe flag out of the exposure the source
    contributes where it sits. A recipe change that moves a source under the
    halo moves its flag with it.
    """
    aperture = _disc(shape, x, y, APERTURE * sigma)
    peak = float(plate_density[aperture].max())

    neighbours = [
        (nx, ny)
        for (nx, ny), _ in catalogue
        if (nx, ny) != (x, y) and np.hypot(nx - x, ny - y) < 2.0 * APERTURE * sigma
    ]
    contaminated = bool((aperture & artefact_mask).any()) or bool(neighbours)

    row, column = int(round(y)), int(round(x))
    row = min(max(row, 0), shape[0] - 1)
    column = min(max(column, 0), shape[1] - 1)
    amplitude = flux / (2.0 * np.pi * sigma**2) * float(vignette[row, column])

    return Source(
        x=x,
        y=y,
        flux=flux,
        sigma=sigma,
        saturated=peak >= SATURATION,
        contaminated=contaminated,
        # Half the half-way exposure. Below it the curve has compressed the
        # source into a density step comparable with the grain, and the flux a
        # measurement returns is a number about the noise.
        in_toe=amplitude < HALF / 2.0,
    )


def _header(
    shape: tuple[int, int], seed: int, collection: str
) -> list[tuple[str, object, str]]:
    """A header shaped like an archive's rather than like a textbook's.

    Every keyword here appears on real plate scans from the four collections:
    the plate identifier, the observer, the emulsion, the scanner and its
    resolution, and a tangent-plane solution in the `CD` form. `COLLECT` carries
    the collection identifier that
    ``docs/decisions/0004-archive-adapters.md`` requires on every row, at the
    only place a fixture can carry it.

    The date is derived from the seed rather than taken from a clock, because a
    generator that reads the time produces a different file every run and the
    identity this module promises would be gone.
    """
    rows, columns = shape
    year = 1908 + seed % 74
    month = 1 + seed % 12
    day = 1 + seed % 28
    return [
        ("SIMPLE", True, "conforms to the FITS standard"),
        ("BITPIX", 16, "16-bit integers, as the scanner delivers"),
        ("NAXIS", 2, ""),
        ("NAXIS1", columns, ""),
        ("NAXIS2", rows, ""),
        ("BZERO", 32768, "offset that makes the signed store unsigned"),
        ("BSCALE", 1, ""),
        ("DATAKIND", "DENSITY", "density, not transmission"),
        ("ORIGIN", "plattenschrank", "written by the synthetic generator"),
        ("COLLECT", collection, "collection identifier, mandatory downstream"),
        ("PLATEID", f"SYN{seed:05d}", "plate identifier within the collection"),
        ("OBJECT", "synthetic field", ""),
        ("TELESCOP", "synthetic refractor", ""),
        ("INSTRUME", "synthetic plate camera", ""),
        ("OBSERVER", "unrecorded", "on a real plate this is a hand on an envelope"),
        ("EMULSION", "synthetic", ""),
        ("DATE-OBS", f"{year:04d}-{month:02d}-{day:02d}", "derived from the seed"),
        ("EXPTIME", 3600.0, "seconds"),
        ("SCANNER", "synthetic", ""),
        ("SCANRES", 1600, "scan resolution in samples per inch"),
        ("EQUINOX", 2000.0, ""),
        ("RADESYS", "ICRS", ""),
        ("CTYPE1", "RA---TAN", "tangent plane, as the four collections use"),
        ("CTYPE2", "DEC--TAN", ""),
        ("CRPIX1", columns / 2.0 + 0.5, ""),
        ("CRPIX2", rows / 2.0 + 0.5, ""),
        ("CRVAL1", 83.822, "degrees"),
        ("CRVAL2", -5.391, "degrees"),
        ("CD1_1", -0.000178, "degrees per pixel"),
        ("CD1_2", 0.0, ""),
        ("CD2_1", 0.0, ""),
        ("CD2_2", 0.000178, "degrees per pixel"),
        ("SEED", seed, "the whole plate is a function of this"),
    ]


def _card(keyword: str, value: object, comment: str) -> bytes:
    """One 80-character FITS card, in the fixed format the standard defines."""
    if isinstance(value, bool):
        rendered = "T" if value else "F"
        body = f"{keyword:<8}= {rendered:>20}"
    elif isinstance(value, str):
        quoted = "'" + value.replace("'", "''").ljust(8) + "'"
        body = f"{keyword:<8}= {quoted:<20}"
    elif isinstance(value, int):
        body = f"{keyword:<8}= {value:>20d}"
    elif isinstance(value, float):
        body = f"{keyword:<8}= {value:>20.10G}"
    else:
        raise TypeError(f"{keyword} carries a {type(value).__name__}, which no card holds")
    if comment:
        body = f"{body} / {comment}"
    if len(body) > CARD:
        body = body[:CARD]
    return body.ljust(CARD).encode("ascii")


def fits_bytes(built: Plate) -> bytes:
    """The whole file, as the bytes that go on disk.

    Returned rather than written, so the identity this module promises is
    testable without a filesystem and so a caller comparing two plates compares
    what a reader would see.
    """
    cards = b"".join(_card(*entry) for entry in built.header)
    cards += b"END".ljust(CARD)
    padding = (-len(cards)) % BLOCK
    header = cards + b" " * padding

    signed = (built.image.astype(np.int32) - 32768).astype(">i2")
    data = signed.tobytes()
    data += b"\x00" * ((-len(data)) % BLOCK)
    return header + data


def write_fits(built: Plate, path: Path) -> None:
    """The same bytes, on disk, for a test that needs a file rather than a buffer."""
    path.write_bytes(fits_bytes(built))
