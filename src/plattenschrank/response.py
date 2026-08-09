"""The characteristic curve of one plate, with the range it is supported over.

``docs/decisions/0005-photometric-response.md`` makes the relation between
recorded density and incident intensity its own stage with its own output, its
own uncertainty and its own identifier, and says that outside the range the
curve is claimed to hold a measurement is flagged rather than produced. This
module is that stage.

## What the curve is

A logistic in the logarithm of intensity, which is the Hurter and Driffield
shape an emulsion has: a toe where a large increase in light produces almost no
density, a roughly straight middle, and a shoulder where it produces almost none
again. Three parameters carry it. ``ceiling`` is the recorded value the response
approaches and never reaches, ``half_intensity`` is the intensity that reaches
half of it, and ``contrast`` is how sharply it turns.

Nothing here assumes a recorded value is proportional to intensity, which is the
sentence 0005 exists for.

## What it refuses

Two refusals, and they are separate because they are different failures.

The recorded value has to lie inside the interval the calibrators covered. Below
it the emulsion is in its toe and the same step in recorded value covers a
factor in intensity that nothing here measured; above it the shoulder does the
same thing in the other direction. A value outside that interval is flagged and
no measurement is produced from it.

The position has to lie inside the radial band the calibrators covered. The
response varies across a plate through vignetting and development, so an
intensity recovered at a radius nothing was calibrated at is an extrapolation in
a second direction that a curve fitted at one radius cannot see. Position is
part of what the curve is claimed over rather than a correction applied to it
afterwards.

## What it does not do

It does not decide which detections are fit to be calibrators. A source sitting
under a halo reads far too bright for its catalogue intensity and would drag the
fit with it, and nothing here can tell that source from a correctly measured
one. Flagging contamination is ``#46`` and the caller supplies what survives it.

The one exclusion this stage does make for itself is a calibrator recorded at
the scan's ceiling, which is a clipped pixel rather than a measurement, and it
reports how many it dropped.

It fits no term for how the response varies with position. With calibrators
spread over a narrow band of radii there is nothing in the data to fit such a
term from, and a fitted number nobody can constrain is worse than a stated
absence. What the stage does instead is record the band it was fitted over and
refuse outside it.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from plattenschrank.model import Measurement

# How far either side of a detection the recorded peak is read, in pixels. A
# detection's position carries a fraction of a pixel, so reading the single
# rounded pixel would sample the flank of a source rather than its peak and
# would do it by a different amount for every calibrator.
PEAK_RADIUS = 2

# The least number of usable calibrators a curve may be fitted from. Three
# parameters are fitted, so three calibrators determine them exactly and leave
# nothing over to say whether the shape was right. The fourth is what makes the
# leave-one-out estimate below an out-of-sample number rather than a restatement
# of the fit.
MINIMUM_CALIBRATORS = 4

# The search for the ceiling, which is the one parameter the linear step below
# cannot carry. It runs from just above the brightest calibrator, because a
# ceiling at or below it makes the logarithm undefined, to well past the scan's
# full scale, because an emulsion that saturates before the digitiser does is
# the normal case and a search stopping at full scale would pin the answer to
# its own edge.
CEILING_STEPS = 6000
CEILING_HEADROOM = 1.6


class UnsupportedRange(ValueError):
    """Raised where a curve was asked for a number outside what it is claimed over.

    Its own type rather than a bare ``ValueError`` so that a caller can catch
    this and let a genuine arithmetic failure through. An extrapolation refused
    and a fit that went wrong are opposite statements about the stage.
    """


class NotEnoughCalibrators(ValueError):
    """Raised where the calibrators given cannot constrain a curve at all."""


@dataclass(frozen=True)
class Calibrator:
    """A source on this scan whose intensity is known from a modern catalogue.

    The intensity is the catalogue's, before anything this plate did to it. What
    the plate did is what the curve is being fitted to describe, so a caller who
    corrected for it first would be handing the stage its own answer.
    """

    x: float
    y: float
    intensity: float


@dataclass(frozen=True)
class Reading:
    """One recorded value put through a curve, or refused by it.

    ``intensity`` is ``None`` exactly where ``outside`` is not empty, and the
    two are written separately rather than one being derived from the other so
    that a reader of a refusal is told which of the two ranges it left.
    """

    recorded: float
    x: float
    y: float
    intensity: float | None
    relative_uncertainty: float | None
    outside: tuple[str, ...]

    @property
    def supported(self) -> bool:
        return not self.outside


@dataclass(frozen=True)
class Curve:
    """The estimated response of one plate, and everything it is claimed over.

    Every field a consumer needs to dispute this is here, which is 0005's own
    requirement that the curve is something a person can plot and argue with:
    the three parameters, the two ranges, the uncertainty and how many
    calibrators went in and how many were dropped.
    """

    calibration_id: str
    ceiling: float
    half_intensity: float
    contrast: float
    # The recorded interval the calibrators covered, in the scan's own units.
    supported_low: float
    supported_high: float
    # The radial band they covered, as a fraction of the distance from the
    # centre of the scan to its corner.
    radial_low: float
    radial_high: float
    # One sigma on an intensity this curve returns, as a fraction of it. What it
    # is measured from is written at `_leave_one_out` below.
    relative_uncertainty: float
    calibrators_used: int
    calibrators_at_ceiling: int
    shape: tuple[int, int]

    def recorded_at(self, intensity: float) -> float:
        """The value this plate would record for a source of this intensity."""
        turn = (self.half_intensity / intensity) ** self.contrast
        return float(self.ceiling / (1.0 + turn))

    def intensity_at(self, recorded: float) -> float:
        """The intensity behind a recorded value, which is the inverse above.

        It is defined for any value below the ceiling and it means something
        only inside the supported interval, which is why `read` refuses rather
        than calling this everywhere.
        """
        return _intensity_at(self.ceiling, self.half_intensity, self.contrast, recorded)

    def radius(self, x: float, y: float) -> float:
        """Distance from the centre of the scan, as a fraction of its corner."""
        return _radius(self.shape, x, y)

    def supports_recorded(self, recorded: float) -> bool:
        return self.supported_low <= recorded <= self.supported_high

    def supports_position(self, x: float, y: float) -> bool:
        return self.radial_low <= self.radius(x, y) <= self.radial_high


def _intensity_at(
    ceiling: float, half_intensity: float, contrast: float, recorded: float
) -> float:
    """The inverse of the curve, as three numbers rather than as a `Curve`.

    It is here rather than only on `Curve` because the leave-one-out estimate
    below inverts curves that are never returned to anybody, and building a
    `Curve` around each of them would mean filling in ranges and an identifier
    that would be answers to nothing.
    """
    bounded = min(max(recorded, 1e-9), ceiling * (1.0 - 1e-12))
    return float(half_intensity * (bounded / (ceiling - bounded)) ** (1.0 / contrast))


def _radius(shape: tuple[int, int], x: float, y: float) -> float:
    rows, columns = shape
    centre_y, centre_x = (rows - 1) / 2.0, (columns - 1) / 2.0
    corner = math.hypot(centre_y, centre_x)
    return float(math.hypot(y - centre_y, x - centre_x) / corner)


def peak_at(scan: NDArray[np.uint16], x: float, y: float) -> float:
    """The largest recorded value within `PEAK_RADIUS` of this position."""
    rows, columns = scan.shape
    column, row = round(x), round(y)
    window = scan[
        max(0, row - PEAK_RADIUS) : min(rows, row + PEAK_RADIUS + 1),
        max(0, column - PEAK_RADIUS) : min(columns, column + PEAK_RADIUS + 1),
    ]
    if window.size == 0:
        raise UnsupportedRange(
            f"the position ({x}, {y}) is off a scan of {columns} by {rows}, so "
            "there is nothing there to read"
        )
    return float(window.max())


def _fit(
    recorded: NDArray[np.float64], intensity: NDArray[np.float64], full_scale: float
) -> tuple[float, float, float]:
    """The three parameters, from a search over one and a line fit for two.

    With the ceiling fixed, the model is a straight line: taking the logarithm
    of ``ceiling / recorded - 1`` gives ``contrast * log(half) - contrast *
    log(intensity)``, so the slope is the contrast and the intercept carries the
    half-intensity. Only the ceiling has to be searched for, and it is searched
    over rather than solved because the shoulder is the part of the curve the
    calibrators constrain least and a solver started in the wrong place there
    walks off.
    """
    logged = np.log(intensity)
    spread = logged - logged.mean()
    if float(spread @ spread) <= 0.0:
        raise NotEnoughCalibrators(
            "every calibrator has the same catalogue intensity, so they cover "
            "no part of the response and there is no curve through them. The "
            "calibrators have to span the brightness range the curve is wanted "
            "over."
        )

    ceilings = np.linspace(
        float(recorded.max()) * (1.0 + 1e-4),
        full_scale * CEILING_HEADROOM,
        CEILING_STEPS,
    )
    # One row per candidate ceiling, one column per calibrator.
    turned = np.log(ceilings[:, None] / recorded[None, :] - 1.0)
    centred = turned - turned.mean(axis=1)[:, None]
    slope = centred @ spread / float(spread @ spread)
    intercept = turned.mean(axis=1) - slope * logged.mean()
    residual = turned - (intercept[:, None] + slope[:, None] * logged[None, :])
    chosen = int(np.argmin((residual**2).sum(axis=1)))

    contrast = float(-slope[chosen])
    if contrast <= 0.0:
        raise NotEnoughCalibrators(
            "the best fit through these calibrators has a recorded value that "
            "falls as intensity rises, which is not a response curve. Either "
            "the intensities or the scan are inverted."
        )
    return (
        float(ceilings[chosen]),
        float(math.exp(float(intercept[chosen]) / contrast)),
        contrast,
    )


def _leave_one_out(
    recorded: NDArray[np.float64], intensity: NDArray[np.float64], full_scale: float
) -> float:
    """One sigma on a recovered intensity, measured out of sample.

    Each calibrator is held out in turn, the curve is refitted without it, and
    the held-out intensity is recovered from the curve that never saw it. What
    is reported is the largest of those errors rather than their spread, so the
    number means that no calibrator held out of this fit was recovered worse
    than this. A spread would be the smaller number and the one a reader would
    over-trust.

    The bound on it is that it is measured from these calibrators. It says
    nothing about a plate whose calibrators are distributed differently, and
    nothing at all outside the ranges the curve carries.
    """
    worst = 0.0
    for held in range(recorded.size):
        kept = np.delete(np.arange(recorded.size), held)
        ceiling, half, contrast = _fit(recorded[kept], intensity[kept], full_scale)
        recovered = _intensity_at(ceiling, half, contrast, float(recorded[held]))
        worst = max(worst, abs(math.log(recovered / float(intensity[held]))))
    return worst


def _identity(
    shape: tuple[int, int],
    used: list[Calibrator],
    recorded: NDArray[np.float64],
    parameters: tuple[float, float, float],
) -> str:
    """An identifier derived from what the curve was estimated from.

    Derived rather than drawn, so that the same scan and the same calibrators
    produce the same identifier on two machines, which is what
    ``docs/decisions/0013-determinism-and-provenance.md`` asks of every
    identifier a row carries. It also makes the identifier the thing 0005 calls
    for under "the inputs it was estimated from": two rows carrying different
    identifiers were calibrated from different inputs, and that can be seen
    without holding either.
    """
    described = "|".join(
        [
            f"shape={shape[0]}x{shape[1]}",
            *(
                f"cal={c.x!r},{c.y!r},{c.intensity!r},{float(value)!r}"
                for c, value in zip(used, recorded, strict=True)
            ),
            f"curve={parameters[0]!r},{parameters[1]!r},{parameters[2]!r}",
        ]
    )
    return "curve-" + hashlib.sha256(described.encode("utf-8")).hexdigest()[:16]


def estimate(scan: NDArray[np.uint16], calibrators: list[Calibrator]) -> Curve:
    """The curve of one plate, from the sources on it whose intensity is known.

    The scan's full scale comes from its own type rather than from an argument,
    because it is a property of the digitisation the archive performed and not
    of anything decided here.
    """
    full_scale = float(np.iinfo(scan.dtype).max)
    read = [(c, peak_at(scan, c.x, c.y)) for c in calibrators]
    # A calibrator recorded at the ceiling is a clipped pixel. Its true value is
    # somewhere above what the file says and nothing here can find out where, so
    # it is dropped and counted rather than fitted as though the file were right.
    usable = [(c, value) for c, value in read if value < full_scale]
    at_ceiling = len(read) - len(usable)
    if len(usable) < MINIMUM_CALIBRATORS:
        raise NotEnoughCalibrators(
            f"{len(usable)} calibrator(s) are usable and a curve needs at least "
            f"{MINIMUM_CALIBRATORS}. {at_ceiling} of the {len(read)} given "
            "were recorded at the scan's ceiling, which is a clipped pixel "
            "rather than a measurement of anything."
        )

    used = [c for c, _ in usable]
    recorded = np.array([value for _, value in usable], dtype=np.float64)
    intensity = np.array([c.intensity for c in used], dtype=np.float64)
    ceiling, half, contrast = _fit(recorded, intensity, full_scale)
    radii = [_radius((scan.shape[0], scan.shape[1]), c.x, c.y) for c in used]

    return Curve(
        calibration_id=_identity(
            (scan.shape[0], scan.shape[1]), used, recorded, (ceiling, half, contrast)
        ),
        ceiling=ceiling,
        half_intensity=half,
        contrast=contrast,
        supported_low=float(recorded.min()),
        supported_high=float(recorded.max()),
        radial_low=min(radii),
        radial_high=max(radii),
        relative_uncertainty=_leave_one_out(recorded, intensity, full_scale),
        calibrators_used=len(used),
        calibrators_at_ceiling=at_ceiling,
        shape=(scan.shape[0], scan.shape[1]),
    )


# The two names a refusal is reported under. They are strings rather than a
# flag each, because a reading may leave both ranges at once and a reader of the
# row should be told both rather than the first one that was checked.
OUTSIDE_SUPPORTED_RANGE = "outside the supported range"
OUTSIDE_CALIBRATED_BAND = "outside the calibrated radial band"


def read(curve: Curve, scan: NDArray[np.uint16], x: float, y: float) -> Reading:
    """One detection put through the curve, or refused with the reason.

    Refused rather than extrapolated, which is the sentence
    ``docs/decisions/0005-photometric-response.md`` writes about the supported
    range. A number returned here for a recorded value the calibrators never
    reached would be a number nobody could tell from a measured one.
    """
    recorded = peak_at(scan, x, y)
    outside: list[str] = []
    if not curve.supports_recorded(recorded):
        outside.append(OUTSIDE_SUPPORTED_RANGE)
    if not curve.supports_position(x, y):
        outside.append(OUTSIDE_CALIBRATED_BAND)
    if outside:
        return Reading(
            recorded=recorded,
            x=x,
            y=y,
            intensity=None,
            relative_uncertainty=None,
            outside=tuple(outside),
        )
    return Reading(
        recorded=recorded,
        x=x,
        y=y,
        intensity=curve.intensity_at(recorded),
        relative_uncertainty=curve.relative_uncertainty,
        outside=(),
    )


def measurement(
    curve: Curve,
    reading: Reading,
    *,
    detection_id: str,
    collection_id: str,
    plate_id: str,
    scan_id: str,
    quantity: str,
    unit: str,
    software_version: str,
    model_id: str,
) -> Measurement:
    """The measurement a supported reading produces, carrying the curve's id.

    A reading that left either range produces no measurement at all. 0005 says
    a measurement there is flagged rather than produced, and returning one with
    a flag attached would put the two on the same row for anybody who did not
    read the flag.

    The uncertainty this stage knows about is the curve's, and it goes in the
    calibration component. The other two components stay absent, because this
    stage did not estimate them and an absence is not a zero.
    """
    if reading.intensity is None or reading.relative_uncertainty is None:
        raise UnsupportedRange(
            f"this reading is {', '.join(reading.outside)}, so no measurement "
            f"is produced from it. Its recorded value is {reading.recorded} "
            f"against a supported interval of {curve.supported_low} to "
            f"{curve.supported_high}, and it sits at radius "
            f"{curve.radius(reading.x, reading.y):.3f} against a calibrated "
            f"band of {curve.radial_low:.3f} to {curve.radial_high:.3f}."
        )
    return Measurement(
        detection_id=detection_id,
        collection_id=collection_id,
        plate_id=plate_id,
        scan_id=scan_id,
        quantity=quantity,
        value=reading.intensity,
        unit=unit,
        calibration_id=curve.calibration_id,
        software_version=software_version,
        model_id=model_id,
        uncertainty_measurement=None,
        uncertainty_calibration=reading.intensity * reading.relative_uncertainty,
        uncertainty_transformation=None,
    )
