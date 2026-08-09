"""The check that keeps the ignore count at zero, and the fixtures that trip it.

`pyproject.toml` turns mypy's strict mode on over `src/`. Strict mode is worth
what it refuses, and there are two ways to stop it refusing anything without
changing a line of the checker's configuration in a way a reader would notice.

An inline `# type: ignore` comment switches the checker off for one line. That
is the one that arrives in a hurry, next to the line that would not pass, and it
is invisible in a diff read from the top.

A `[[tool.mypy.overrides]]` block switches it off for a whole module. That is the
one that arrives with a reason, gets one module, and is still there two years
later covering forty.

So the rule is a count rather than a judgement: `src/` carries no ignore comment
and the mypy configuration carries no entry that relaxes a rule. Zero is a bar a
check can hold. "Only where it is justified" is not.

The near miss this is built against is a substring match, and it is a real one
rather than an invented one, because both arms have a legitimate neighbour that
reads almost the same.

In the comment arm, mypy honours `# type: ignore` only where the comment begins
with it. A comment saying that a `type: ignore` would be wrong here is prose
about the rule and suppresses nothing, and a check keyed on the substring
refuses the sentence explaining itself. The docstring you are reading would be
refused by that version if it were in `src/`.

In the configuration arm the neighbours are worse, because they are settings
that make the checker stricter and whose names contain the ones that make it
weaker. `warn_unused_ignores` contains `ignore` and is the setting that refuses
an ignore comment nobody needs any more. `enable_error_code` contains
`error_code` and is the setting that turns extra refusals on. A check matching
either substring reds on the two settings a reader would most want to see in
this file.
"""

from __future__ import annotations

import io
import re
import subprocess
import tokenize
import tomllib
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent

# The directory strict mode covers, which is what `[tool.mypy] files` names.
CHECKED_DIRECTORY = "src"

# A suppression comment, matched only where the comment begins with it, because
# that is the only place mypy reads one.
IGNORE_COMMENT = re.compile(r"^#\s*type\s*:\s*ignore\b")

# mypy's inline configuration comment, which carries the same option names as
# the configuration file and can relax the same rules from inside a module.
MYPY_COMMENT = re.compile(r"^#\s*mypy\s*:\s*(?P<settings>.+)$")

# Options that can only ever weaken what the checker refuses. Named one by one
# rather than matched by shape, so the settings that strengthen it and happen to
# share a word are not caught with them.
RELAXING_OPTIONS = frozenset(
    {
        "ignore_errors",
        "ignore_missing_imports",
        "disable_error_code",
    }
)

# `follow_imports` is not on the list above because two of its four values are
# fine. These two stop the checker reading an imported module, which silently
# turns everything that comes out of it into `Any`.
FOLLOW_IMPORTS_THAT_RELAX = frozenset({"skip", "silent"})


def ignore_entries_in_source(path: str, text: str) -> list[str]:
    """Every suppression a module carries, each with the reason it is one."""
    found = []
    try:
        tokens = list(tokenize.tokenize(io.BytesIO(text.encode("utf-8")).readline))
    except tokenize.TokenError as broken:
        # Fail rather than pass. A module this cannot read has not been found
        # clean, and the two must not look the same.
        return [f"{path}: could not be tokenised, so it was not checked: {broken}"]
    for token in tokens:
        if token.type != tokenize.COMMENT:
            continue
        line = token.start[0]
        if IGNORE_COMMENT.match(token.string):
            found.append(f"{path}:{line}: a type: ignore comment")
            continue
        inline = MYPY_COMMENT.match(token.string)
        if inline is None:
            continue
        for option in inline.group("settings").split(","):
            name = option.split("=")[0].strip().replace("-", "_")
            if name in RELAXING_OPTIONS:
                found.append(f"{path}:{line}: an inline mypy {name} setting")
    return found


def ignore_entries_in_configuration(configuration: dict[str, object]) -> list[str]:
    """Every entry in the mypy configuration that relaxes one of its rules.

    Takes the whole parsed `pyproject.toml` rather than the mypy table, because
    a configuration with no mypy table at all is a different failure from one
    with a clean table and has to be told apart from it.
    """
    tool = configuration.get("tool")
    if not isinstance(tool, dict) or "mypy" not in tool:
        return ["pyproject.toml: there is no [tool.mypy] table to check"]
    mypy = tool["mypy"]
    if not isinstance(mypy, dict):
        return ["pyproject.toml: [tool.mypy] is not a table"]

    found = []
    if mypy.get("strict") is not True:
        found.append("[tool.mypy]: strict is not on")

    overrides = mypy.get("overrides", [])
    sections: list[tuple[str, dict[str, object]]] = [("[tool.mypy]", mypy)]
    if isinstance(overrides, list):
        for index, override in enumerate(overrides):
            if isinstance(override, dict):
                module = override.get("module", "no module")
                sections.append((f"[[tool.mypy.overrides]] {module!r}", override))
            else:
                found.append(f"[[tool.mypy.overrides]] entry {index} is not a table")

    for label, section in sections:
        for name, value in section.items():
            if name in RELAXING_OPTIONS and value not in (False, [], ""):
                found.append(f"{label}: {name} is set to {value!r}")
            if name == "follow_imports" and value in FOLLOW_IMPORTS_THAT_RELAX:
                found.append(f"{label}: follow_imports is {value!r}")
            if name == "strict" and value is False:
                found.append(f"{label}: strict is turned off")
    return found


def checked_modules() -> list[tuple[str, str]]:
    """The tracked Python files strict mode covers, read from git.

    From git rather than from a directory walk, because a module sitting
    untracked in a checkout is not something this repository carries, and a
    build directory full of copies is not something the checker reads.
    """
    listing = subprocess.run(
        ["git", "ls-files", "-z", "--", CHECKED_DIRECTORY],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if listing.returncode != 0:
        pytest.fail(f"git ls-files did not run: {listing.stderr.strip()}")
    return [
        (name, (REPOSITORY_ROOT / name).read_text(encoding="utf-8"))
        for name in listing.stdout.split("\0")
        if name.endswith(".py")
    ]


def project_configuration() -> dict[str, object]:
    with (REPOSITORY_ROOT / "pyproject.toml").open("rb") as handle:
        return tomllib.load(handle)


def test_the_package_carries_no_ignore_comment() -> None:
    """The count the issue asks for, over the tree it is in."""
    found = [
        entry
        for path, text in checked_modules()
        for entry in ignore_entries_in_source(path, text)
    ]
    assert found == []


def test_the_mypy_configuration_relaxes_nothing() -> None:
    assert ignore_entries_in_configuration(project_configuration()) == []


def test_the_check_read_the_package_rather_than_an_empty_list() -> None:
    """A green result over nothing reads exactly like a green result over the
    package, and this is what separates them."""
    paths = {path for path, _ in checked_modules()}
    assert "src/plattenschrank/cli.py" in paths
    assert len(paths) > 1


def test_an_ignore_comment_is_refused() -> None:
    source = "x: int = 1\ny: str = x  # type: ignore[assignment]\n"
    assert ignore_entries_in_source("src/m.py", source) == [
        "src/m.py:2: a type: ignore comment"
    ]


def test_an_ignore_comment_is_refused_however_it_is_spaced() -> None:
    """The spellings mypy itself accepts, which a stricter pattern would miss."""
    for spelling in (
        "#type:ignore",
        "#  type :  ignore",
        "# type: ignore # and a note",
    ):
        assert ignore_entries_in_source("src/m.py", f"x = 1  {spelling}\n")


def test_prose_about_an_ignore_comment_is_not_refused() -> None:
    """The near miss, and the reason this reads comments rather than lines.

    Neither of these suppresses anything: mypy reads the comment only where it
    begins with `type:`, and it does not read a string at all. A substring match
    refuses both, which means it refuses every sentence explaining the rule.
    """
    trailing = "x = 1  # a type: ignore here would hide the bug\n"
    inside_a_string = 'NOTE = "write # type: ignore and this check refuses it"\n'
    assert ignore_entries_in_source("src/m.py", trailing) == []
    assert ignore_entries_in_source("src/m.py", inside_a_string) == []


def test_a_word_that_merely_starts_with_ignore_is_not_refused() -> None:
    """`# type: ignored` is not a suppression, and the word boundary is what
    says so."""
    assert (
        ignore_entries_in_source("src/m.py", "x = 1  # type: ignored by nobody\n") == []
    )


def test_an_inline_mypy_setting_that_relaxes_is_refused() -> None:
    source = "# mypy: ignore-errors\nx = 1\n"
    assert ignore_entries_in_source("src/m.py", source) == [
        "src/m.py:1: an inline mypy ignore_errors setting"
    ]


def test_an_inline_mypy_setting_that_tightens_is_not_refused() -> None:
    assert ignore_entries_in_source("src/m.py", "# mypy: strict\nx = 1\n") == []
    assert (
        ignore_entries_in_source(
            "src/m.py", "# mypy: enable-error-code=redundant-expr\n"
        )
        == []
    )


def test_a_module_that_cannot_be_read_is_refused_rather_than_passed() -> None:
    """A tokeniser that fell over has not found the module clean."""
    assert ignore_entries_in_source("src/m.py", "x = (\n")


def test_an_override_that_relaxes_is_refused() -> None:
    configuration = {
        "tool": {
            "mypy": {
                "strict": True,
                "overrides": [{"module": "plattenschrank.io", "ignore_errors": True}],
            }
        }
    }
    assert ignore_entries_in_configuration(configuration) == [
        "[[tool.mypy.overrides]] 'plattenschrank.io': ignore_errors is set to True"
    ]


def test_a_relaxing_setting_at_the_top_level_is_refused() -> None:
    configuration = {"tool": {"mypy": {"strict": True, "ignore_missing_imports": True}}}
    assert ignore_entries_in_configuration(configuration) == [
        "[tool.mypy]: ignore_missing_imports is set to True"
    ]


def test_strict_being_turned_off_is_refused() -> None:
    """The cheapest way to disable every rule at once, and it adds no entry that
    the word `ignore` appears in anywhere."""
    assert ignore_entries_in_configuration({"tool": {"mypy": {"strict": False}}})


def test_a_missing_mypy_table_is_refused() -> None:
    """Deleting the configuration is not the same as having a clean one, and a
    check that cannot tell them apart passes the day somebody removes it."""
    assert ignore_entries_in_configuration({"tool": {"pytest": {}}}) == [
        "pyproject.toml: there is no [tool.mypy] table to check"
    ]


def test_the_settings_that_tighten_are_not_refused() -> None:
    """The near miss in the configuration arm.

    `warn_unused_ignores` carries `ignore` and refuses a suppression that is no
    longer needed. `enable_error_code` carries `error_code` and turns extra
    refusals on. A substring match reds on the two settings this file most wants
    a reader to be able to add.
    """
    configuration = {
        "tool": {
            "mypy": {
                "strict": True,
                "warn_unused_ignores": True,
                "enable_error_code": ["redundant-expr"],
                "follow_imports": "normal",
            }
        }
    }
    assert ignore_entries_in_configuration(configuration) == []


def test_follow_imports_is_refused_only_where_it_stops_the_checker_reading() -> None:
    for value in sorted(FOLLOW_IMPORTS_THAT_RELAX):
        assert ignore_entries_in_configuration(
            {"tool": {"mypy": {"strict": True, "follow_imports": value}}}
        )
    for value in ("normal", "error"):
        assert (
            ignore_entries_in_configuration(
                {"tool": {"mypy": {"strict": True, "follow_imports": value}}}
            )
            == []
        )
