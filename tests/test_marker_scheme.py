"""What the marker scheme owes, and the fixtures that make its guard bite.

Every isolated run below is given the real guard and the real scheme. The
conftest source is read from disk rather than copied, and the marker names are
read from the running configuration, so a fixture cannot pass against a guard
that is no longer the one this suite uses. Deleting the hook from
``tests/conftest.py`` reds the refusal tests here, and the pull request that
landed this records what was deleted and what failed.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from conftest import SCHEME, requirement_markers

pytestmark = pytest.mark.unit

THE_SCHEME = frozenset({"unit", "integration_network", "integration_gpu", "slow"})

GUARD = Path(__file__).resolve().parent / "conftest.py"


def isolate(
    pytester: pytest.Pytester,
    config: pytest.Config,
    addopts: str = "",
    scheme: str | None = None,
) -> None:
    """Give a scratch suite the guard and the scheme this repository uses.

    The guard arrives as its own source and the marker names as the ones the
    running configuration reports, so neither is a second copy that could
    disagree with the one under test. ``scheme`` overrides the names for the one
    case that is about the scheme being wrong rather than a test being wrong.
    """
    pytester.makeconftest(GUARD.read_text(encoding="utf-8"))
    names = config.getini(SCHEME) if scheme is None else scheme.split()
    pytester.makeini(
        "[pytest]\n"
        f"{SCHEME} = {' '.join(names)}\n"
        f"addopts = {addopts}\n"
        "markers =\n" + "".join(f"    {line}\n" for line in config.getini("markers"))
    )


def output(result: pytest.RunResult) -> str:
    """Everything the run said, so a refusal is read wherever it was printed."""
    return result.stdout.str() + result.stderr.str()


def test_the_scheme_declares_four_markers_and_no_more(
    pytestconfig: pytest.Config,
) -> None:
    assert requirement_markers(pytestconfig) == THE_SCHEME


def test_every_marker_in_the_scheme_is_registered_with_its_meaning(
    pytestconfig: pytest.Config,
) -> None:
    """The two declarations cannot drift apart in silence.

    The scheme is one setting and the sentence that says what each marker means
    is another. A name in the first that is missing from the second is a marker
    the guard accepts and ``--markers`` never mentions.
    """
    meanings = {
        line.split(":", 1)[0].strip(): line.split(":", 1)[-1].strip()
        for line in pytestconfig.getini("markers")
        if ":" in line
    }
    for name in sorted(requirement_markers(pytestconfig)):
        assert meanings.get(name), name


def test_the_default_selection_is_unit_alone(pytestconfig: pytest.Config) -> None:
    assert pytestconfig.getini("addopts") == ["-m", "unit"]


def test_a_test_with_no_marker_fails_collection(
    pytester: pytest.Pytester, pytestconfig: pytest.Config
) -> None:
    isolate(pytester, pytestconfig)
    pytester.makepyfile("def test_nothing_was_stated(): pass")
    result = pytester.runpytest()
    assert result.ret != 0
    assert "test_nothing_was_stated" in output(result)


def test_a_test_whose_marker_is_misspelled_fails_collection(
    pytester: pytest.Pytester, pytestconfig: pytest.Config
) -> None:
    """The near miss this hook is aimed at.

    ``unti`` reads as ``unit`` in review. Without the hook it is a marker the
    scheme does not name, so the test states no requirement and leaves the
    default selection while looking like it is inside it.
    """
    isolate(pytester, pytestconfig)
    pytester.makepyfile(
        "import pytest\n"
        "@pytest.mark.unti\n"
        "def test_the_marker_is_one_letter_wrong(): pass\n"
    )
    result = pytester.runpytest()
    assert result.ret != 0
    assert "test_the_marker_is_one_letter_wrong" in output(result)


def test_a_built_in_marker_alone_is_not_a_stated_requirement(
    pytester: pytest.Pytester, pytestconfig: pytest.Config
) -> None:
    """Why the scheme has a setting of its own.

    The first version of this guard read the scheme out of pytest's ``markers``
    list, which carries pytest's own built-in markers as well. ``tryfirst`` and
    ``trylast`` are in there as bare names, so a test carrying one of them and
    nothing else stated no requirement and was accepted anyway.
    """
    isolate(pytester, pytestconfig)
    pytester.makepyfile(
        "import pytest\n"
        "@pytest.mark.tryfirst\n"
        "def test_only_a_built_in_marker(): pass\n"
    )
    result = pytester.runpytest()
    assert result.ret != 0
    assert "test_only_a_built_in_marker" in output(result)


def test_an_empty_scheme_refuses_rather_than_accepting_everything(
    pytester: pytest.Pytester, pytestconfig: pytest.Config
) -> None:
    """The guard fails closed when its own setting is missing.

    A scheme naming nothing would make every test pass the check, and a run that
    checked nothing reads exactly like a run that found nothing wrong. This is
    the one shape of this failure that no test in the suite could reveal on its
    own.
    """
    isolate(pytester, pytestconfig, scheme=" ")
    pytester.makepyfile(
        "import pytest\n@pytest.mark.unit\ndef test_properly_marked(): pass\n"
    )
    result = pytester.runpytest()
    assert result.ret != 0
    assert SCHEME in output(result)


def test_the_hook_sees_a_test_the_default_selection_would_have_deselected(
    pytester: pytest.Pytester, pytestconfig: pytest.Config
) -> None:
    """The ordering is the guard here, and it is invisible without this case.

    pytest deselects by marker inside the same hook this guard runs in. A guard
    registered after it is handed a list the unmarked test has already been
    removed from, so it refuses nothing and the suite stays green. The
    difference between the two orderings is exactly this run.
    """
    isolate(pytester, pytestconfig, addopts="-m unit")
    pytester.makepyfile("def test_nothing_was_stated(): pass")
    result = pytester.runpytest()
    assert result.ret != 0
    assert "test_nothing_was_stated" in output(result)


def test_a_marked_test_is_collected_and_passes(
    pytester: pytest.Pytester, pytestconfig: pytest.Config
) -> None:
    """The control, without which the refusals above prove only that it refuses."""
    isolate(pytester, pytestconfig)
    pytester.makepyfile(
        "import pytest\n@pytest.mark.unit\ndef test_it_states_unit(): pass\n"
    )
    pytester.runpytest().assert_outcomes(passed=1)


def test_the_default_selection_leaves_a_non_unit_test_out(
    pytester: pytest.Pytester, pytestconfig: pytest.Config
) -> None:
    """Selection, not only refusal.

    Every test in this repository carries ``unit`` today, so the default
    selection deselects nothing here and a run of it proves nothing about
    selecting. This is where the selection is shown, on a scratch suite that has
    a test outside the gated set to leave behind.
    """
    isolate(pytester, pytestconfig, addopts="-m unit")
    pytester.makepyfile(
        "import pytest\n"
        "@pytest.mark.unit\n"
        "def test_gated(): pass\n"
        "@pytest.mark.slow\n"
        "def test_not_gated(): pass\n"
    )
    pytester.runpytest().assert_outcomes(passed=1, deselected=1)


def test_naming_the_marker_reaches_the_test_the_default_leaves_out(
    pytester: pytest.Pytester, pytestconfig: pytest.Config
) -> None:
    """The other half of the same property.

    A test outside the gated set is reachable, and only by naming its marker on
    the command line. Without this the case above is satisfied by a selection
    that can never run anything but ``unit``.
    """
    isolate(pytester, pytestconfig, addopts="-m unit")
    pytester.makepyfile(
        "import pytest\n"
        "@pytest.mark.unit\n"
        "def test_gated(): pass\n"
        "@pytest.mark.slow\n"
        "def test_not_gated(): pass\n"
    )
    pytester.runpytest("-m", "slow").assert_outcomes(passed=1, deselected=1)
