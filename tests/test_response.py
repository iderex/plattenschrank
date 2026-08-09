"""The characteristic curve, held against a plate whose true curve is known.

``src/plattenschrank/synthetic.py`` builds its plates through a response with a
toe, a shoulder and a ceiling, and it records the parameters it used. That is
what makes this file possible: the recovered curve can be compared against the
curve the light actually went through rather than against another estimate of
it.

## What the comparison is against, and what it is not

The generator applies its vignette to the exposure before the response, so the
emulsion at a source sees less light than the catalogue says the source emits.
The curve fitted here maps a recorded value back to the CATALOGUE intensity, so
the truth it is compared against is the generator's own inverse divided by the
vignette where the calibrators sit. Comparing against the undivided inverse
would be comparing two different quantities, and it fails by about the size of
the vignette, which is large enough to notice and small enough to be mistaken
for a fit that is merely poor.

## What a passing number here does and does not say

It says the arithmetic recovers a curve from the failures somebody enumerated
in that generator. It says nothing about plate photometry, because a synthetic
plate carries the failures it was told about and no others. The generator's own
first sentence says this and it is repeated here because a recovery number is
exactly the kind of result that travels without its caveat.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from plattenschrank import synthetic
from plattenschrank.model import MissingRequiredField
from plattenschrank.response import (
    MINIMUM_CALIBRATORS,
    OUTSIDE_CALIBRATED_BAND,
    OUTSIDE_SUPPORTED_RANGE,
    Calibrator,
    Curve,
    NotEnoughCalibrators,
    UnsupportedRange,
    estimate,
    measurement,
    peak_at,
    read,
)

pytestmark = pytest.mark.unit

# More than one, because a curve recovered from one plate is a curve recovered
# from one arrangement of grain, one scratch position and one dust grain. The
# seeds are fixed rather than drawn, so a failure names the plate that produced
# it in four characters.
SEEDS = (7, 11, 42, 101, 2024)

# How many points across the supported interval the recovered curve is compared
# against the true one at. The ends are where a wrong shape shows first, and
# `numpy.linspace` includes both.
SAMPLES = 40


def catalogue_intensity(source: synthetic.Source, background: float) -> float:
    """The peak exposure this source delivers, before the plate does anything.

    A Gaussian of total flux ``F`` and width ``sigma`` peaks at ``F / (2 pi
    sigma^2)``, and the sky it sits on adds the background. This is the number a
    modern catalogue plays the part of here.
    """
    return background + source.flux / (2.0 * math.pi * source.sigma**2)


def calibrators_of(built: synthetic.Plate) -> list[Calibrator]:
    """The sources on this plate a caller would hand the stage as calibrators.

    Saturated and contaminated sources are left out, and that is the caller's
    exclusion rather than the stage's. The stage drops a calibrator recorded at
    the scan's ceiling because a clipped pixel is visible in the file; it cannot
    see that a source sits under a halo, and `test_a_clipped_calibrator_is_the
    _one_exclusion_the_stage_makes_for_itself` is what holds those two apart.
    """
    return [
        Calibrator(
            x=source.x,
            y=source.y,
            intensity=catalogue_intensity(source, built.truth.background),
        )
        for source in built.truth.sources
        if not source.saturated and not source.contaminated
    ]


def vignette_where_calibrated(
    built: synthetic.Plate, calibrators: list[Calibrator]
) -> float:
    """The generator's falloff averaged over the positions the curve was fitted at."""
    return float(np.mean([built.vignette[round(c.y), round(c.x)] for c in calibrators]))


def true_intensity(built: synthetic.Plate, recorded: float, vignette: float) -> float:
    """The catalogue intensity behind a recorded value, from the generator itself."""
    density = np.array([recorded * built.truth.d_max / synthetic.FULL_SCALE])
    return float(synthetic.incident(density)[0] / vignette)


def fitted(seed: int) -> tuple[synthetic.Plate, list[Calibrator], Curve]:
    built = synthetic.plate(seed)
    calibrators = calibrators_of(built)
    return built, calibrators, estimate(built.image, calibrators)


@pytest.mark.parametrize("seed", SEEDS)
def test_the_curve_produces_the_three_things_the_record_asks_for(seed: int) -> None:
    """A curve, an uncertainty and a supported range, and none of them empty.

    An interval whose ends are equal is not a range, and an uncertainty of zero
    from five noisy calibrators would be a number nobody should believe, so both
    are checked for being a measurement rather than a placeholder.
    """
    _, calibrators, curve = fitted(seed)
    assert curve.contrast > 0.0
    assert curve.half_intensity > 0.0
    assert curve.ceiling > curve.supported_high
    assert curve.supported_low < curve.supported_high
    assert curve.radial_low <= curve.radial_high
    assert curve.relative_uncertainty > 0.0
    assert curve.calibrators_used == len(calibrators)


@pytest.mark.parametrize("seed", SEEDS)
def test_the_recovered_curve_is_inside_its_stated_uncertainty(seed: int) -> None:
    """The done-condition of #45, over the whole interval rather than at a point.

    The comparison is in the logarithm because the quantity is an intensity
    spanning more than a factor of twenty across this interval, and an absolute
    difference there is a statement about the bright end and nothing else.
    """
    built, calibrators, curve = fitted(seed)
    vignette = vignette_where_calibrated(built, calibrators)
    worst = 0.0
    for recorded in np.linspace(curve.supported_low, curve.supported_high, SAMPLES):
        recovered = curve.intensity_at(float(recorded))
        truth = true_intensity(built, float(recorded), vignette)
        worst = max(worst, abs(math.log(recovered / truth)))
    assert worst <= curve.relative_uncertainty, (
        f"the recovered curve leaves its own stated uncertainty by {worst:.4f} "
        f"against {curve.relative_uncertainty:.4f} somewhere inside the "
        "supported range, so the uncertainty this stage publishes does not "
        "cover the error it makes"
    )


@pytest.mark.parametrize("seed", SEEDS)
def test_the_curve_is_not_a_straight_line_through_the_calibrators(seed: int) -> None:
    """The near miss, and the one worth the effort.

    A response proportional to intensity would satisfy every assertion above
    about a curve existing, and it would be wrong in exactly the place plate
    photometry is hard. What is asserted here is not that the two differ, which
    says nothing about how much, but that the test above would refuse the
    proportional one: fitted through the same calibrators by least squares
    through the origin, it leaves the stated uncertainty somewhere inside the
    same interval.

    Without this the whole file would pass on a stage that had thrown the
    emulsion away, as long as the uncertainty it published was wide enough to
    cover the damage.
    """
    built, calibrators, curve = fitted(seed)
    vignette = vignette_where_calibrated(built, calibrators)
    recorded = np.array(
        [peak_at(built.image, c.x, c.y) for c in calibrators], dtype=np.float64
    )
    intensity = np.array([c.intensity for c in calibrators], dtype=np.float64)
    # Least squares through the origin, which is what proportional means.
    scale = float(recorded @ intensity / (intensity @ intensity))

    worst = 0.0
    for value in np.linspace(curve.supported_low, curve.supported_high, SAMPLES):
        proportional = float(value) / scale
        truth = true_intensity(built, float(value), vignette)
        worst = max(worst, abs(math.log(proportional / truth)))
    assert worst > curve.relative_uncertainty, (
        "a response proportional to intensity stays inside the uncertainty "
        f"{curve.relative_uncertainty:.4f} this curve publishes, over the same "
        "interval, so the comparison above would pass on a stage that never "
        "estimated a curve at all"
    )


@pytest.mark.parametrize("seed", SEEDS)
def test_a_source_outside_the_supported_range_is_flagged_and_not_measured(
    seed: int,
) -> None:
    """The refusal `docs/decisions/0005-photometric-response.md` asks for.

    The saturated source is the case: it is the brightest thing on the plate,
    its recorded value is at the ceiling, and a curve asked to invert it returns
    a number. Returning that number is the failure, because nothing downstream
    could tell it from one the calibrators actually reached.
    """
    built, _, curve = fitted(seed)
    saturated = max(built.truth.sources, key=lambda source: source.flux)
    assert saturated.saturated

    reading = read(curve, built.image, saturated.x, saturated.y)
    assert OUTSIDE_SUPPORTED_RANGE in reading.outside
    assert reading.intensity is None
    assert not reading.supported

    with pytest.raises(UnsupportedRange) as refusal:
        measurement(
            curve,
            reading,
            detection_id="det-1",
            collection_id=built.truth.collection,
            plate_id=f"synthetic-{seed}",
            scan_id="scan-1",
            quantity="incident_intensity",
            unit="exposure",
            software_version="0.0.0",
            model_id="none",
        )
    assert OUTSIDE_SUPPORTED_RANGE in str(refusal.value)


def test_the_two_refusals_are_reported_apart_from_each_other() -> None:
    """Leaving the density interval and leaving the calibrated band are different.

    A reading can leave one without leaving the other, and a caller told only
    that something was refused cannot tell an extrapolation in brightness from
    an extrapolation across the plate. The centre of the plate is inside the
    supported interval here and outside the band the calibrators cover, which is
    the case that separates them.
    """
    built, calibrators, curve = fitted(7)
    rows, columns = built.image.shape
    centre_x, centre_y = (columns - 1) / 2.0, (rows - 1) / 2.0
    assert curve.radius(centre_x, centre_y) < curve.radial_low

    somewhere_supported = float(
        np.clip(
            built.image[round(centre_y), round(centre_x)],
            curve.supported_low,
            curve.supported_high,
        )
    )
    assert curve.supports_recorded(somewhere_supported)
    assert not curve.supports_position(centre_x, centre_y)

    # And the reading that comes back names the band it left, so a caller is
    # told which of the two extrapolations was refused rather than only that
    # one of them was.
    at_the_centre = read(curve, built.image, centre_x, centre_y)
    assert OUTSIDE_CALIBRATED_BAND in at_the_centre.outside
    calibrated = read(curve, built.image, calibrators[0].x, calibrators[0].y)
    assert OUTSIDE_CALIBRATED_BAND not in calibrated.outside
    assert OUTSIDE_SUPPORTED_RANGE not in calibrated.outside


@pytest.mark.parametrize("seed", SEEDS)
def test_every_measurement_carries_the_identifier_of_its_curve(seed: int) -> None:
    built, _, curve = fitted(seed)
    supported = [source for source in built.truth.sources if source.recoverable]
    assert supported, "this plate has no source a measurement could be made from"
    # Counted rather than assumed. Every source here is inside both ranges, and
    # a change that quietly put them all outside would leave the loop below
    # asserting nothing and reporting green.
    measured = 0
    for index, source in enumerate(supported):
        reading = read(curve, built.image, source.x, source.y)
        if not reading.supported:
            continue
        measured += 1
        produced = measurement(
            curve,
            reading,
            detection_id=f"det-{index}",
            collection_id=built.truth.collection,
            plate_id=f"synthetic-{seed}",
            scan_id="scan-1",
            quantity="incident_intensity",
            unit="exposure",
            software_version="0.0.0",
            model_id="none",
        )
        assert produced.calibration_id == curve.calibration_id
        assert produced.to_row()["calibration_id"] == curve.calibration_id
    assert measured == len(supported), (
        f"{len(supported) - measured} of this plate's recoverable sources were "
        "refused by the curve fitted from them, so the loop above carried no "
        "measurement for them"
    )


def test_a_measurement_carries_the_curve_uncertainty_and_no_other() -> None:
    """The calibration component is filled in and the other two stay absent.

    This stage estimated the curve and nothing else, so writing a zero into
    either of the other two would say it estimated them and found no
    uncertainty, which is the reading `#48` exists to prevent.
    """
    built, _, curve = fitted(7)
    source = next(s for s in built.truth.sources if s.recoverable)
    reading = read(curve, built.image, source.x, source.y)
    assert reading.supported
    produced = measurement(
        curve,
        reading,
        detection_id="det-1",
        collection_id=built.truth.collection,
        plate_id="synthetic-7",
        scan_id="scan-1",
        quantity="incident_intensity",
        unit="exposure",
        software_version="0.0.0",
        model_id="none",
    )
    assert produced.uncertainty_calibration is not None
    assert produced.uncertainty_calibration > 0.0
    assert produced.uncertainty_measurement is None
    assert produced.uncertainty_transformation is None


def test_a_measurement_without_a_curve_identifier_is_refused_by_the_model() -> None:
    """The refusal 0005 states, met by the type layer rather than restated here.

    `src/plattenschrank/model.py` refuses a measurement with no
    `calibration_id`, so this stage cannot produce one whatever it does with the
    field. Asserting it here is what stops the two drifting: a curve that
    started returning a blank identifier would be caught at construction rather
    than in a catalogue.
    """
    built, _, curve = fitted(7)
    source = next(s for s in built.truth.sources if s.recoverable)
    reading = read(curve, built.image, source.x, source.y)
    blank = Curve(**{**vars(curve), "calibration_id": "   "})
    with pytest.raises(MissingRequiredField, match="calibration_id"):
        measurement(
            blank,
            reading,
            detection_id="det-1",
            collection_id=built.truth.collection,
            plate_id="synthetic-7",
            scan_id="scan-1",
            quantity="incident_intensity",
            unit="exposure",
            software_version="0.0.0",
            model_id="none",
        )


def test_the_identifier_is_the_same_for_the_same_inputs() -> None:
    """Determinism, which `docs/decisions/0013-determinism-and-provenance.md` asks.

    An identifier drawn rather than derived would put a different value on two
    runs over one scan, and every row written by the second run would look like
    it came from a calibration nobody could compare against the first.
    """
    built, calibrators, curve = fitted(7)
    assert estimate(built.image, calibrators).calibration_id == curve.calibration_id


def test_the_identifier_moves_when_the_inputs_do() -> None:
    """The other direction, which is what catches an identifier of nothing.

    A constant would satisfy the test above perfectly. Two curves fitted from
    different calibrators have to be told apart, because the identifier is what
    a row carries in place of the calibration itself.
    """
    built, calibrators, curve = fitted(7)
    fewer = estimate(built.image, calibrators[1:])
    assert fewer.calibration_id != curve.calibration_id


def test_a_clipped_calibrator_is_the_one_exclusion_the_stage_makes_for_itself() -> None:
    """A pixel at the scan's ceiling is dropped, counted, and not fitted.

    Its true recorded value is somewhere above what the file says and nothing
    here can find out where, so fitting it as though the file were right pulls
    the shoulder down towards a value the emulsion never produced.
    """
    built, calibrators, _ = fitted(7)
    saturated = max(built.truth.sources, key=lambda source: source.flux)
    with_clipped = [
        *calibrators,
        Calibrator(
            x=saturated.x,
            y=saturated.y,
            intensity=catalogue_intensity(saturated, built.truth.background),
        ),
    ]
    curve = estimate(built.image, with_clipped)
    assert curve.calibrators_at_ceiling == 1
    assert curve.calibrators_used == len(calibrators)


def test_too_few_calibrators_is_refused_rather_than_fitted() -> None:
    built, calibrators, _ = fitted(7)
    with pytest.raises(NotEnoughCalibrators, match=str(MINIMUM_CALIBRATORS)):
        estimate(built.image, calibrators[: MINIMUM_CALIBRATORS - 1])


def test_calibrators_that_cover_no_brightness_range_are_refused() -> None:
    """Four calibrators at one intensity determine nothing and are refused.

    They are four points on one vertical line. A fit through them has no slope
    to find, and the arithmetic that would report one is reporting the grain.
    """
    built, calibrators, _ = fitted(7)
    flat = [
        Calibrator(x=c.x, y=c.y, intensity=calibrators[0].intensity)
        for c in calibrators
    ]
    with pytest.raises(NotEnoughCalibrators, match="same catalogue intensity"):
        estimate(built.image, flat)


def test_reading_off_the_scan_is_refused_rather_than_wrapped() -> None:
    """A position outside the array is refused instead of indexing from the end.

    Negative indexing would read the opposite corner of the plate and return a
    number, which is the shape of failure this board is against: nothing raises
    and the answer is somewhere else's.
    """
    built, _, curve = fitted(7)
    rows, columns = built.image.shape
    with pytest.raises(UnsupportedRange, match="off a scan"):
        read(curve, built.image, float(columns + 50), float(rows + 50))
