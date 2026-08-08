"""What the gated suite owes a machine with no display and no elevation.

`docs/decisions/0012-headless-and-cpu-by-default.md` makes this a birth
requirement, and the record's own reasoning is that the alternative cannot be
repaired later. A suite that grew up with a display available grows plotting
calls into assertions and grows a window toolkit into an import, and undoing
that means rewriting the tests rather than adding a flag.

Three properties, proved separately, because they fail separately.

The backend selection. `tests/conftest.py` sets `MPLBACKEND` to the
non-interactive backend at import time, before any test runs and before
anything can import a plotting library. This file refuses the absence of that
line.

WHAT THAT DOES NOT PROVE, and the line is negative and stays negative: no
plotting library is in the locked graph today, so nothing here observes a
backend in force. What is proved is that the suite makes the selection and that
removing the selection reds the suite. A plotting library arriving in the graph
is what turns this into a measurement of a backend, and until then reading it as
one would be wrong.

The toolkit imports. A window toolkit reached at import time is the failure that
does not wait for a plotting call, and it is the one that hangs a suite on a
machine with no display. This is measured in a fresh interpreter rather than in
this one, because by the time this file runs pytest has already imported a great
deal and a toolkit pulled in by the harness would be indistinguishable from one
pulled in by the package.

The privilege level. A test that reaches a path needing elevation and passes has
not covered that path on any machine an operator has. This asks the operating
system rather than reading an environment variable, and it answers on both
platforms this suite runs on.
"""

from __future__ import annotations

import os
import subprocess
import sys

import pytest

from plattenschrank import DISTRIBUTION

pytestmark = pytest.mark.unit

# Every matplotlib backend that draws to a file rather than to a window. The
# check is membership in this set rather than "not one of the interactive ones",
# because the interactive list grows with every toolkit anybody writes a binding
# for and a check keyed on it fails open the day a new one appears.
NON_INTERACTIVE_BACKENDS = frozenset(
    {"Agg", "Cairo", "PDF", "PGF", "PS", "SVG", "Template"}
)

# Window toolkits, which is what an interactive backend is made of. A module
# here in a fresh interpreter that imported the package means the package
# reached a toolkit at import time.
WINDOW_TOOLKITS = (
    "tkinter",
    "PyQt5",
    "PyQt6",
    "PySide2",
    "PySide6",
    "wx",
    "gi.repository.Gtk",
)


def running_privileged() -> bool:
    """Whether this process holds administrative privilege, asked of the system.

    Two implementations because the question has two shapes. On a POSIX system
    it is the effective user id. On Windows there is no such id and the
    equivalent is whether the process token is elevated, which `IsUserAnAdmin`
    reports. Both are reads. Neither raises a prompt, and nothing here attempts
    to acquire privilege it does not have.
    """
    posix_user_id = getattr(os, "geteuid", None)
    if posix_user_id is not None:
        return posix_user_id() == 0
    import ctypes

    return bool(ctypes.windll.shell32.IsUserAnAdmin())


def test_the_plotting_backend_is_forced_to_a_non_interactive_one() -> None:
    """The guard, and deleting the line in `tests/conftest.py` reds this.

    It reds by `KeyError` rather than by a comparison, which is deliberate:
    absent and set-to-something-interactive are different failures and a reader
    of the red should be able to tell which happened.
    """
    assert os.environ["MPLBACKEND"] in NON_INTERACTIVE_BACKENDS


def test_the_forced_backend_is_not_read_from_the_environment_this_suite_inherited() -> None:
    """The near miss, which is a suite that passes for somebody else's reason.

    A contributor with `MPLBACKEND` already exported would make the test above
    green with the forcing line deleted, so on their machine the guard would be
    absent and invisible. Reading the value out of `tests/conftest.py` rather
    than out of the environment is what separates the two.
    """
    from conftest import NON_INTERACTIVE_BACKEND

    assert NON_INTERACTIVE_BACKEND in NON_INTERACTIVE_BACKENDS
    assert os.environ["MPLBACKEND"] == NON_INTERACTIVE_BACKEND


def test_importing_the_package_reaches_no_window_toolkit() -> None:
    """Measured in a fresh interpreter, for the reason in the module docstring."""
    probe = (
        "import sys, importlib;"
        f"importlib.import_module('{DISTRIBUTION}.cli');"
        "print(','.join(sorted(sys.modules)))"
    )
    result = subprocess.run(
        [sys.executable, "-c", probe],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    imported = set(result.stdout.strip().split(","))
    assert [toolkit for toolkit in WINDOW_TOOLKITS if toolkit in imported] == []


def test_the_probe_read_a_real_interpreter_rather_than_an_empty_list() -> None:
    """The test above is green over an empty set, and this is what says it was
    not one."""
    result = subprocess.run(
        [sys.executable, "-c", "import sys; print(','.join(sorted(sys.modules)))"],
        capture_output=True,
        text=True,
        check=False,
    )
    imported = set(result.stdout.strip().split(","))
    assert "sys" in imported
    assert len(imported) > 10


def test_the_suite_does_not_run_with_administrative_privilege() -> None:
    """A path that needs elevation is not covered by a suite that had it."""
    assert not running_privileged()
