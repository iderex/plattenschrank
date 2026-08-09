"""What the selection disclosure owes, and the fixtures that make it bite.

The line under test is the one thing standing between a green ``build`` and a
reader who takes it for coverage of the whole suite. It is printed by
``pytest_collection_finish`` in ``tests/conftest.py``.

Every run below is an isolated suite given the real guard source and the real
marker names, the same arrangement ``tests/test_marker_scheme.py`` uses, so a
fixture cannot pass against a hook that is no longer the one this repository
runs. Deleting ``pytest_collection_finish`` from ``tests/conftest.py`` reds the
refusal tests here, and the pull request that landed this records what was
deleted and what failed.

The disclosure is a statement rather than a refusal, so what these tests hold is
that it is printed, that it names the sets this run did not reach, and that it
carries what running each of those would need. Whether a reader acts on it is
not something a test can hold.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from conftest import DISCLOSURE, SCHEME, marker_meanings, requirement_markers

pytestmark = pytest.mark.unit

GUARD = Path(__file__).resolve().parent / "conftest.py"


def suite_covering(names: list[str]) -> str:
    """A scratch suite with one test per named marker.

    The names come from the running scheme rather than from a list here, so a
    marker added to the scheme arrives in these fixtures instead of being
    silently untested.
    """
    return "import pytest\n" + "".join(
        f"@pytest.mark.{name}\ndef test_{name}(): pass\n" for name in names
    )


def isolate(
    pytester: pytest.Pytester, config: pytest.Config, addopts: str = ""
) -> None:
    """Give a scratch suite the hook, the scheme and the marker meanings."""
    pytester.makeconftest(GUARD.read_text(encoding="utf-8"))
    pytester.makeini(
        "[pytest]\n"
        f"{SCHEME} = {' '.join(config.getini(SCHEME))}\n"
        f"addopts = {addopts}\n"
        "markers =\n" + "".join(f"    {line}\n" for line in config.getini("markers"))
    )


def output(result: pytest.RunResult) -> str:
    return result.stdout.str() + result.stderr.str()


def test_the_line_is_printed_by_a_run_of_the_gated_set(
    pytester: pytest.Pytester, pytestconfig: pytest.Config
) -> None:
    isolate(pytester, pytestconfig, addopts="-m unit")
    pytester.makepyfile(suite_covering(sorted(requirement_markers(pytestconfig))))
    result = pytester.runpytest()
    assert DISCLOSURE in output(result)


def test_the_line_names_every_set_the_selection_left_out(
    pytester: pytest.Pytester, pytestconfig: pytest.Config
) -> None:
    """The whole point of it.

    A run of the gated set reached ``unit`` and nothing else, and the three
    other sets have to be in the line by name. Naming only the one it covered
    would read as a complete statement about the suite.
    """
    isolate(pytester, pytestconfig, addopts="-m unit")
    pytester.makepyfile(suite_covering(sorted(requirement_markers(pytestconfig))))
    printed = output(pytester.runpytest())
    line = next(text for text in printed.splitlines() if DISCLOSURE in text)
    for name in requirement_markers(pytestconfig) - {"unit"}:
        assert name in line, name
    assert "unit" in line


def test_the_line_carries_what_running_each_left_out_set_would_need(
    pytester: pytest.Pytester, pytestconfig: pytest.Config
) -> None:
    """The cost, read from the marker's own registration rather than restated.

    A set named without its cost tells a reader that something is missing and
    not what it would take, which is the half that decides whether anybody ever
    runs it.
    """
    isolate(pytester, pytestconfig, addopts="-m unit")
    pytester.makepyfile(suite_covering(sorted(requirement_markers(pytestconfig))))
    printed = output(pytester.runpytest())
    line = next(text for text in printed.splitlines() if DISCLOSURE in text)
    meanings = marker_meanings(pytestconfig)
    for name in requirement_markers(pytestconfig) - {"unit"}:
        assert meanings[name] in line, name


def test_a_selection_that_reaches_another_set_says_so(
    pytester: pytest.Pytester, pytestconfig: pytest.Config
) -> None:
    """The control, without which the cases above pass on a hard-coded line.

    Selecting the network-bound set has to move ``integration_network`` from the
    left-out half of the line to the covered half, and ``unit`` the other way.
    """
    isolate(pytester, pytestconfig, addopts="-m integration_network")
    pytester.makepyfile(suite_covering(sorted(requirement_markers(pytestconfig))))
    printed = output(pytester.runpytest())
    line = next(text for text in printed.splitlines() if DISCLOSURE in text)
    covered, _, left = line.partition("It did not run")
    assert "integration_network" in covered
    assert "unit" in left


def test_a_selection_naming_a_set_no_test_carries_reports_covering_nothing(
    pytester: pytest.Pytester, pytestconfig: pytest.Config
) -> None:
    """The case the two integration harnesses are in today.

    ``.github/workflows/integration.yml`` selects sets that no test in this
    repository carries yet. The honest report of that run is that it covered
    nothing, and the failure this refuses is a line that names the requested
    marker as covered because it was asked for rather than because it ran.
    """
    isolate(pytester, pytestconfig, addopts="-m integration_gpu")
    pytester.makepyfile(suite_covering(["unit"]))
    printed = output(pytester.runpytest())
    line = next(text for text in printed.splitlines() if DISCLOSURE in text)
    covered, _, left = line.partition("It did not run")
    assert "integration_gpu" not in covered
    assert "integration_gpu" in left


def test_a_run_that_reaches_every_set_says_it_left_none_out(
    pytester: pytest.Pytester, pytestconfig: pytest.Config
) -> None:
    """The other end, so the line cannot be a fixed list of three names."""
    isolate(pytester, pytestconfig)
    pytester.makepyfile(suite_covering(sorted(requirement_markers(pytestconfig))))
    printed = output(pytester.runpytest())
    line = next(text for text in printed.splitlines() if DISCLOSURE in text)
    assert "left no set out" in line


def test_the_line_is_printed_before_the_first_test_result(
    pytester: pytest.Pytester, pytestconfig: pytest.Config
) -> None:
    """Position, because a disclosure under a green summary is one nobody reads.

    ``pytest_collection_finish`` runs after selection and before the first test,
    which is what puts the line above the progress output rather than in the
    trailer a reader skips once the last line says everything passed.
    """
    isolate(pytester, pytestconfig, addopts="-m unit")
    pytester.makepyfile(suite_covering(sorted(requirement_markers(pytestconfig))))
    printed = output(pytester.runpytest()).splitlines()
    disclosed = next(i for i, text in enumerate(printed) if DISCLOSURE in text)
    passed = next(i for i, text in enumerate(printed) if " passed" in text)
    assert disclosed < passed
