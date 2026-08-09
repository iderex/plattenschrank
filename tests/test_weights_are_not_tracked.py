"""The check that refuses a tracked weight file, and the fixtures that trip it.

`docs/decisions/0011-model-weights-are-not-tracked.md` says no trained model
weights are committed here. Until this file existed that was a sentence in a
document, which the record's own closing section said in as many words.

The refusal has two arms, because one of them alone leaves a hole a reader would
not see.

By size, under a directory named `weights`. That is the shape the record
describes, and it is what catches a weight file that arrives with an
unremarkable name.

By suffix, wherever the file sits. A `.safetensors` file at the root is a weight
file and no directory name makes it one, so a check keyed only on the directory
would pass it. This arm is what the first is measured against rather than an
extra: between them, a weight file has to be both outside the directory and
under an unrecognised suffix to get in, and that residue is stated below rather
than left for a reader to work out.

The directory match is on a path segment and never on a substring. The record
this check exists for is called
`docs/decisions/0011-model-weights-are-not-tracked.md`, so a substring match on
`weights` refuses the document that asks for the check. That is not a
hypothetical near miss, it is the first file in the tree that a careless version
would red on, and `test_a_file_merely_named_for_weights_is_not_refused` holds it.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

import pytest

pytestmark = pytest.mark.unit

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent

# The directory a weight file is expected to arrive in, matched as a path
# segment.
WEIGHTS_DIRECTORY = "weights"

# Suffixes that make a file a weight file whatever it is called and wherever it
# sits. Serialisation formats only. `.bin` is deliberately absent: it is the one
# suffix on this kind of list that has a hundred innocent uses, and a check that
# reds on an unrelated file is a check somebody turns off.
WEIGHT_SUFFIXES = frozenset(
    {".ckpt", ".h5", ".onnx", ".pb", ".pt", ".pth", ".safetensors"}
)

# One mebibyte. The largest file this repository tracks is 14666 bytes:
#
#     git ls-files -z | xargs -0 -I{} stat -c '%s %n' {} | sort -rn | head -1
#     14666 docs/prism-survey.md
#
# so the bar sits about seventy times above anything legitimate here and far
# below any weight file worth the name. It is a number a fixture can straddle,
# which is the property that matters more than where exactly it sits.
THRESHOLD_BYTES = 1024 * 1024


@dataclass(frozen=True)
class TrackedFile:
    path: str
    size: int


def refusals(tracked: list[TrackedFile]) -> list[str]:
    """Every tracked file this check refuses, each with the reason it was."""
    refused = []
    for entry in tracked:
        segments = PurePosixPath(entry.path)
        if segments.suffix.lower() in WEIGHT_SUFFIXES:
            refused.append(f"{entry.path}: a weight file by its suffix")
        elif WEIGHTS_DIRECTORY in segments.parts[:-1] and entry.size > THRESHOLD_BYTES:
            refused.append(
                f"{entry.path}: {entry.size} bytes under {WEIGHTS_DIRECTORY}/, "
                f"over the {THRESHOLD_BYTES} byte threshold"
            )
    return refused


def tracked_files() -> list[TrackedFile]:
    """What git carries, read from git rather than from the working tree.

    An untracked weight file sitting in a checkout is not what the record is
    about. What it forbids is a weight file the repository carries, and git is
    the only thing that knows which those are.
    """
    listing = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if listing.returncode != 0:
        # Fail rather than skip. A check that cannot read the tree has not found
        # the tree clean, and the two have to look different.
        pytest.fail(f"git ls-files did not run: {listing.stderr.strip()}")
    return [
        TrackedFile(path=name, size=(REPOSITORY_ROOT / name).stat().st_size)
        for name in listing.stdout.split("\0")
        if name and (REPOSITORY_ROOT / name).is_file()
    ]


def test_this_repository_tracks_no_weight_file() -> None:
    """The check itself, over the tree it is in."""
    assert refusals(tracked_files()) == []


def test_the_check_read_the_tree_rather_than_an_empty_list() -> None:
    """Without this, an empty listing passes the check above in silence.

    A green result over nothing and a green result over the whole tree are the
    same assertion, and this is what separates them.
    """
    paths = {entry.path for entry in tracked_files()}
    assert "docs/decisions/0011-model-weights-are-not-tracked.md" in paths
    assert len(paths) > 1


def test_a_large_file_under_the_weights_directory_is_refused() -> None:
    trips = [TrackedFile("weights/detector-2026-08.dat", THRESHOLD_BYTES + 1)]
    assert refusals(trips) == [
        f"weights/detector-2026-08.dat: {THRESHOLD_BYTES + 1} bytes under "
        f"weights/, over the {THRESHOLD_BYTES} byte threshold"
    ]


def test_the_threshold_is_a_bound_and_not_a_target() -> None:
    """The off-by-one, which is the mistake this arm is actually exposed to.

    A file exactly at the threshold is under the bar and a file one byte above
    it is over. Written the other way round the check is still green on this
    tree and still red on a weight file, so nothing else here would notice.
    """
    assert refusals([TrackedFile("weights/at-the-bar.dat", THRESHOLD_BYTES)]) == []
    assert refusals([TrackedFile("weights/over-the-bar.dat", THRESHOLD_BYTES + 1)])


def test_a_weight_file_is_refused_wherever_it_sits() -> None:
    """The arm the directory rule needs.

    Ten bytes, at the root, under no directory the first rule looks at. Only the
    suffix says what it is.
    """
    assert refusals([TrackedFile("detector.safetensors", 10)]) == [
        "detector.safetensors: a weight file by its suffix"
    ]


def test_a_weight_suffix_is_matched_whatever_its_case() -> None:
    assert refusals([TrackedFile("src/plattenschrank/Detector.PT", 10)])


def test_a_file_merely_named_for_weights_is_not_refused() -> None:
    """The near miss that would red this tree the day the check landed.

    `docs/decisions/0011-model-weights-are-not-tracked.md` carries `weights` in
    its filename. A check matching the substring rather than the path segment
    refuses the record that asked for the check, and it would do it at whatever
    size, so no threshold hides it.
    """
    trips = [
        TrackedFile(
            "docs/decisions/0011-model-weights-are-not-tracked.md",
            THRESHOLD_BYTES + 1,
        ),
        TrackedFile("docs/weights-and-what-they-cost.md", THRESHOLD_BYTES + 1),
    ]
    assert refusals(trips) == []


def test_a_directory_whose_name_merely_contains_weights_is_not_refused() -> None:
    """The same mistake one level up, where the segment is the directory."""
    assert (
        refusals([TrackedFile("docs/weights-notes/large.dat", THRESHOLD_BYTES + 1)])
        == []
    )


def test_the_directory_rule_reaches_any_depth() -> None:
    assert refusals(
        [TrackedFile("src/plattenschrank/weights/detector.dat", THRESHOLD_BYTES + 1)]
    )


def test_a_file_called_weights_is_not_a_directory_called_weights() -> None:
    """`weights` as the last segment is a file, and the rule is about the parent."""
    assert refusals([TrackedFile("docs/weights", THRESHOLD_BYTES + 1)]) == []
