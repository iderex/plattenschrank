"""What the synthetic plate owes, measured rather than asserted.

Two things are worth saying about the shape of this file before the tests.

The reader is not ours. `src/plattenschrank/synthetic.py` writes FITS bytes with
no library underneath it, and everything here that judges those bytes reads them
with astropy. A writer checked by a reader from the same tree proves that the
tree agrees with itself, which is the weaker claim and the one easy to reach by
accident.

The recovery test is a measurement and not a smoke test. It inverts the response
curve pixel by pixel, corrects the vignette, sums an aperture and compares the
result with the flux the generator put there, for the sources the truth table
says are recoverable. The tolerance it holds to was measured across seeds rather
than tuned until it passed, and the pull request that landed this records the
sweep and the worst case in it.

What none of it proves is that the pipeline works on a plate. These fixtures
carry the failures somebody enumerated, and the module says so in its own first
sentence.
"""

from __future__ import annotations

import io
import json
from pathlib import Path

import numpy as np
import pytest
from astropy.io import fits
from astropy.wcs import WCS
from numpy.typing import NDArray

from plattenschrank import synthetic
from plattenschrank.synthetic import APERTURE, BLOCK, D_MAX, FULL_SCALE, Plate

pytestmark = pytest.mark.unit

# The seed everything below is measured on. One number, which is the point of a
# generator whose output is a function of it.
SEED = 7

# The bound the recovery measurement holds to. The worst relative error over
# seeds 0 to 24 was 0.0282, recorded in the pull request that landed this, so
# this is that number with room for a seed nobody has run rather than a limit
# raised until the suite went green.
TOLERANCE = 0.05


@pytest.fixture(name="built")
def fixture_built() -> Plate:
    return synthetic.plate(SEED)


def measured_flux(built: Plate, x: float, y: float, sigma: float) -> float:
    """The flux an honest measurement gets out of the scan at one position.

    Each step is one the pipeline will have to do for real: undo the 16-bit
    scaling, invert the response curve per pixel because it is not linear and a
    sum of densities means nothing, divide out the vignette, subtract the sky and
    sum inside the aperture.
    """
    density_values = built.image.astype(np.float64) / FULL_SCALE * D_MAX
    exposure = synthetic.incident(density_values) / built.vignette
    sky = float(np.median(exposure))
    rows, columns = built.truth.shape
    grid_y, grid_x = np.mgrid[0:rows, 0:columns]
    aperture: NDArray[np.bool_] = (grid_x - x) ** 2 + (grid_y - y) ** 2 <= (
        APERTURE * sigma
    ) ** 2
    return float((exposure[aperture] - sky).sum())


def test_one_seed_produces_identical_bytes_on_two_runs() -> None:
    """A fixture is a number in a test rather than a file in the repository."""
    assert synthetic.fits_bytes(synthetic.plate(SEED)) == synthetic.fits_bytes(
        synthetic.plate(SEED)
    )


def test_two_seeds_produce_different_bytes() -> None:
    """The control. Without it the case above passes on a constant image."""
    assert synthetic.fits_bytes(synthetic.plate(SEED)) != synthetic.fits_bytes(
        synthetic.plate(SEED + 1)
    )


def test_the_file_on_disk_is_the_bytes_in_memory(tmp_path: Path) -> None:
    built = synthetic.plate(SEED)
    written = tmp_path / "plate.fits"
    synthetic.write_fits(built, written)
    assert written.read_bytes() == synthetic.fits_bytes(built)


def test_a_reference_reader_accepts_the_file(built: Plate) -> None:
    """astropy reads the bytes and verifies the header against the standard.

    This is the whole reason the writer here has no library under it. If it did,
    this test would be the same library agreeing with itself.
    """
    with fits.open(io.BytesIO(synthetic.fits_bytes(built))) as opened:
        hdu = opened[0]
        hdu.verify("exception")
        assert hdu.data.shape == built.truth.shape
        assert np.array_equal(hdu.data, built.image)


def test_the_file_is_a_whole_number_of_blocks(built: Plate) -> None:
    """FITS is a stream of 2880-byte blocks and a reader is entitled to assume it."""
    assert len(synthetic.fits_bytes(built)) % BLOCK == 0


def test_the_world_coordinate_solution_round_trips(built: Plate) -> None:
    """A solution that is present is not the same as a solution that is real.

    astropy converts pixels to sky and back, so what passes here is a tangent
    plane a reduction could use rather than a set of keywords that parse.
    """
    with fits.open(io.BytesIO(synthetic.fits_bytes(built))) as opened:
        solution = WCS(opened[0].header)
    pixels = np.array([[10.0, 20.0], [100.0, 140.0], [180.0, 30.0]])
    sky = solution.wcs_pix2world(pixels, 0)
    back = solution.wcs_world2pix(sky, 0)
    assert np.allclose(back, pixels, atol=1e-6)


def test_the_header_carries_the_collection_identifier(built: Plate) -> None:
    """`docs/decisions/0004-archive-adapters.md` requires it on every row.

    A fixture is where a row starts, so it is where the identifier has to be
    present or the rule has nothing to be true of.
    """
    with fits.open(io.BytesIO(synthetic.fits_bytes(built))) as opened:
        header = opened[0].header
    assert header["COLLECT"] == built.truth.collection
    for keyword in ("PLATEID", "DATE-OBS", "EXPTIME", "EMULSION", "TELESCOP"):
        assert keyword in header, keyword


def test_the_header_is_a_function_of_the_seed_and_not_of_the_clock() -> None:
    """A generator that reads a clock has no identity to promise."""
    first = dict((key, value) for key, value, _ in synthetic.plate(SEED).header)
    second = dict((key, value) for key, value, _ in synthetic.plate(SEED).header)
    assert first == second
    assert first["DATE-OBS"] != dict(
        (key, value) for key, value, _ in synthetic.plate(SEED + 3).header
    )["DATE-OBS"]


def test_the_recovered_flux_matches_the_truth_for_every_recoverable_source(
    built: Plate,
) -> None:
    """The measurement the whole generator exists to make possible."""
    recoverable = [source for source in built.truth.sources if source.recoverable]
    assert recoverable, "the fixture has nothing to measure"
    for source in recoverable:
        measured = measured_flux(built, source.x, source.y, source.sigma)
        assert abs(measured / source.flux - 1.0) < TOLERANCE, source


def test_the_fixture_carries_a_source_of_each_excluded_kind(built: Plate) -> None:
    """The exclusions are not decoration and each needs a case to be about."""
    assert any(source.saturated for source in built.truth.sources)
    assert any(source.contaminated for source in built.truth.sources)
    assert any(source.in_toe for source in built.truth.sources)


def test_a_saturated_source_measures_wrong_rather_than_merely_being_labelled(
    built: Plate,
) -> None:
    """What the saturation flag is worth.

    A flag that could be removed without anything measuring differently is a
    comment. Inverting the curve over a source whose peak sits at the ceiling
    returns a number, and this is the case that shows the number is not a flux.
    """
    saturated = [source for source in built.truth.sources if source.saturated]
    assert saturated
    for source in saturated:
        measured = measured_flux(built, source.x, source.y, source.sigma)
        assert abs(measured / source.flux - 1.0) > TOLERANCE


def test_a_source_under_an_artefact_measures_wrong_for_the_same_reason(
    built: Plate,
) -> None:
    contaminated = [
        source
        for source in built.truth.sources
        if source.contaminated and not source.saturated
    ]
    assert contaminated
    for source in contaminated:
        measured = measured_flux(built, source.x, source.y, source.sigma)
        assert abs(measured / source.flux - 1.0) > TOLERANCE


def test_every_artefact_the_truth_names_is_on_the_plate(built: Plate) -> None:
    """A taxonomy entry with nothing behind it is a fixture that lies quietly."""
    rows, columns = built.truth.shape
    grid_y, grid_x = np.mgrid[0:rows, 0:columns]
    density_values = built.image.astype(np.float64) / FULL_SCALE * D_MAX
    sky = float(np.median(density_values))
    for artefact in built.truth.artefacts:
        near = (grid_x - artefact.x) ** 2 + (grid_y - artefact.y) ** 2 <= (
            artefact.radius + 2.0
        ) ** 2
        assert near.any(), artefact
        assert float(density_values[near].max()) > sky, artefact


def test_the_four_artefact_kinds_are_all_present(built: Plate) -> None:
    kinds = {artefact.kind for artefact in built.truth.artefacts}
    assert kinds == {"halo", "ghost", "scratch", "dust"}


def test_the_truth_table_is_text_and_says_what_it_knows(built: Plate) -> None:
    """The truth leaves the process, so a fixture's answer can be compared later."""
    restored = json.loads(built.truth.as_json())
    assert restored["seed"] == SEED
    assert len(restored["sources"]) == len(built.truth.sources)
    assert restored["sources"][0]["flux"] == built.truth.sources[0].flux
    assert {entry["kind"] for entry in restored["artefacts"]} == {
        "halo",
        "ghost",
        "scratch",
        "dust",
    }


def test_the_response_curve_is_invertible_where_it_is_defined() -> None:
    """The two directions are each other's inverse away from the ceiling."""
    exposure = np.geomspace(1.0, 4000.0, 64)
    assert np.allclose(synthetic.incident(synthetic.density(exposure)), exposure)


def test_the_response_curve_has_a_toe_and_a_shoulder() -> None:
    """Not linear, and not linear at both ends for different reasons.

    A straight response would make every calibration test pass without the
    calibration, which is the failure this fixture exists to prevent.
    """
    low = synthetic.density(np.array([1.0, 2.0]))
    high = synthetic.density(np.array([20000.0, 40000.0]))
    middle = synthetic.density(np.array([100.0, 200.0]))
    assert (low[1] - low[0]) < (middle[1] - middle[0])
    assert (high[1] - high[0]) < (middle[1] - middle[0])
    assert float(high[1]) < D_MAX


def test_the_module_says_what_synthetic_fixtures_do_not_prove() -> None:
    """The clause of #25 that is about the docstring rather than the code.

    A generator that does not say what it cannot support gets quoted as though
    it could, which on this board is the failure that matters more than a wrong
    number.
    """
    docstring = synthetic.__doc__ or ""
    assert "prove nothing" in docstring
    assert "nobody has enumerated" in docstring
