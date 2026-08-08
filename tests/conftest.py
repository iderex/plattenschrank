"""The collection hook that refuses a test whose requirements nobody stated.

The marker scheme is in ``pyproject.toml`` under ``[tool.pytest.ini_options]``:
four markers, one line of meaning each, and ``-m unit`` as the default
selection. This file is the half of the scheme that refuses rather than
describes.

The rule is one sentence. Every collected test carries at least one of the
markers the scheme names, and collection fails naming the ones that do not.

That single rule covers both shapes of the mistake. A test with no marker at all
is the obvious one. The one worth aiming at is a test whose marker is
misspelled, because ``@pytest.mark.unti`` reads as ``unit`` in review and is not
one, so the test states no requirement and, without this hook, quietly leaves
the default selection while looking like it is inside it.

``--strict-markers`` would also refuse the misspelling, and it is deliberately
not set. Two mechanisms answering for one property make a red fixture unable to
say which of them refused, and the proof this board asks for is that deleting
the guard reds the suite. There is one guard here, and
``tests/test_marker_scheme.py`` runs the source of this file against fixtures
that trip it.

The scheme is read from its own ``requirement_markers`` setting rather than from
pytest's ``markers`` list, because that list also carries pytest's own built-in
markers and there would then be no way to say which four the scheme is. Two of
those built-ins, ``tryfirst`` and ``trylast``, are bare names that survive the
parse intact, so a guard reading the scheme out of that list accepts a test
carrying one of them and nothing else. The rest arrive with their argument
lists attached and are refused for the accidental reason that their names do
not parse to a bare word, which is not a property to rely on.

The hook runs ``tryfirst`` because pytest's own ``-m`` filtering deselects in
this same hook. Running after it would mean an unmarked test had already been
deselected by the default selection and there would be nothing left to refuse,
which is the failure this ordering exists to prevent and which
``test_the_hook_sees_a_test_the_default_selection_would_have_deselected``
demonstrates.
"""

from __future__ import annotations

import os

import pytest

pytest_plugins = ["pytester"]

SCHEME = "requirement_markers"

# The non-interactive plotting backend, selected here and not in an environment
# variable a contributor sets on their own machine. A guard that depends on
# somebody remembering is not a guard, and the failure it prevents is a plotting
# call selecting a window toolkit on the first machine that has one, which turns
# a green suite into one that hangs waiting for a window nobody will close.
#
# This line is the forcing and `tests/test_headless.py` is what refuses its
# absence. The bound on both is stated there: no plotting library is in the
# locked graph yet, so what is proved is the selection this suite makes and not
# a backend observed in force.
NON_INTERACTIVE_BACKEND = "Agg"
os.environ["MPLBACKEND"] = NON_INTERACTIVE_BACKEND


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addini(
        SCHEME,
        "the markers a test states its requirements with, one of which every "
        "test carries",
        type="args",
        default=[],
    )


def requirement_markers(config: pytest.Config) -> frozenset[str]:
    """The marker names the scheme declares, read from the configuration."""
    return frozenset(config.getini(SCHEME))


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    declared = requirement_markers(config)
    if not declared:
        # Fail closed. An empty scheme would make the loop below accept every
        # test, so the guard would report nothing and read exactly like a guard
        # that found nothing wrong.
        raise pytest.UsageError(
            f"the {SCHEME} setting names no marker, so nothing here states a "
            "requirement and this hook would accept every test. It belongs in "
            "pyproject.toml under [tool.pytest.ini_options]."
        )
    unstated = [
        item.nodeid
        for item in items
        if not declared & {mark.name for mark in item.iter_markers()}
    ]
    if not unstated:
        return
    raise pytest.UsageError(
        "every test states its requirements with one of the markers "
        f"{', '.join(sorted(declared))}. These state none, either by carrying no "
        "marker or by carrying one the scheme does not name: "
        + ", ".join(unstated)
    )
