"""What the entry point owes, checked against the installed distribution.

These tests import the installed package rather than the working tree, which is
the whole reason for the ``src/`` layout in
``docs/decisions/0002-repository-layout.md``.
"""

from __future__ import annotations

import subprocess
import sys
from importlib.metadata import entry_points, version
from pathlib import Path

import pytest

from plattenschrank import DISTRIBUTION, cli
from plattenschrank.cli import EXIT_NOT_IMPLEMENTED, STAGES, Stage, build_parser, main

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent

# Everything here runs in a subprocess of this interpreter and touches nothing
# outside the repository, so the whole module belongs to the gated set.
pytestmark = pytest.mark.unit


def run_entry_point(*args: str) -> subprocess.CompletedProcess[str]:
    """Run the entry point in a subprocess, the way an operator would.

    Reached through ``python -m`` rather than by the console script name,
    because the directory a console script is installed into is not on every
    PATH and this suite has to pass without arranging that. That the console
    script itself is declared and installed is checked separately below.
    """
    return subprocess.run(
        [sys.executable, "-m", DISTRIBUTION, *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_version_matches_installed_distribution_metadata() -> None:
    """The guard this package exists to carry first.

    A version typed into the source instead of read from metadata makes this
    fail. That was checked by doing it, not by assuming it.
    """
    result = run_entry_point("--version")
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == version(DISTRIBUTION)


def test_the_version_option_reports_whatever_metadata_says(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The test above passes for the wrong reason on its own.

    A version literal typed into the source is caught by it only while the
    literal disagrees with the metadata, and the mistake somebody actually makes
    is bumping the version in one place and not the other, which starts from
    agreement. This replaces what metadata reports and asserts the command
    follows it, so a literal fails here whatever it says.
    """
    monkeypatch.setattr(cli, "version", lambda distribution: "424242.0.0")
    parser = cli.build_parser()
    with pytest.raises(SystemExit) as exit_info:
        parser.parse_args(["--version"])
    assert exit_info.value.code == 0
    assert capsys.readouterr().out.strip() == "424242.0.0"


def test_the_console_script_is_declared_and_installed() -> None:
    scripts = entry_points(group="console_scripts")
    matching = [entry for entry in scripts if entry.name == DISTRIBUTION]
    assert len(matching) == 1, [entry.name for entry in scripts]
    assert matching[0].value == "plattenschrank.cli:main"


def test_help_lists_every_stage() -> None:
    result = run_entry_point("--help")
    assert result.returncode == 0, result.stderr
    for stage in STAGES:
        assert stage.name in result.stdout


@pytest.mark.parametrize("stage", STAGES, ids=[stage.name for stage in STAGES])
def test_a_stage_that_is_not_built_exits_non_zero(stage: Stage) -> None:
    """An empty run may not look like a clean one.

    Success here would mean a stage that did nothing reports the same exit code
    as a stage that examined a collection and found nothing.
    """
    result = run_entry_point(stage.name)
    assert result.returncode == EXIT_NOT_IMPLEMENTED
    assert "examined: nothing." in result.stdout
    assert stage.record in result.stdout


def test_no_arguments_prints_help_and_does_not_succeed() -> None:
    assert main([]) == EXIT_NOT_IMPLEMENTED


def test_every_stage_names_a_record_that_is_in_the_tree() -> None:
    """A stage pointing at a record that does not exist is a broken promise.

    The paths resolve against the repository root rather than the installed
    package, because the records are documentation and are not shipped.
    """
    missing = [
        stage.record
        for stage in STAGES
        if not (REPOSITORY_ROOT / stage.record).is_file()
    ]
    assert missing == []


def test_parser_prog_is_the_distribution_name() -> None:
    assert build_parser().prog == DISTRIBUTION
