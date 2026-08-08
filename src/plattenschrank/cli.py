"""The command line entry point and its subcommand structure.

No stage logic lives here. Each subcommand names the decision record that
defines the stage it will carry, reports that it examined nothing, and exits
non-zero, so that a run which did no work cannot be read as a run that covered
a collection and found nothing.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version
from typing import TextIO

from plattenschrank import DISTRIBUTION

# A stage that is not built yet exits with this rather than with success. Zero
# would make an empty run indistinguishable from a run that examined a
# collection and found nothing, which is the reading this board most needs to
# prevent.
EXIT_NOT_IMPLEMENTED = 3


@dataclass(frozen=True)
class Stage:
    """One pipeline subcommand, and what it will examine once it exists."""

    name: str
    summary: str
    examines: str
    record: str


# One entry per stage that already has a decision record on the mainline. A
# stage with no record does not get a subcommand here, because this list would
# then be the place a stage was decided. Transcription is the deliberate
# absence: decision 0016 puts it outside the pipeline, and whether it is a
# separate distributable at all is entry 4 of issue #1, which is open.
STAGES: tuple[Stage, ...] = (
    Stage(
        name="ingest",
        summary="Read plates from an archive through its adapter",
        examines="the plates an adapter returns for a collection",
        record="docs/decisions/0004-archive-adapters.md",
    ),
    Stage(
        name="calibrate",
        summary="Estimate the photometric response and apply it",
        examines="the characteristic curve of each plate and its supported range",
        record="docs/decisions/0005-photometric-response.md",
    ),
    Stage(
        name="detect",
        summary="Find sources and artefacts on direct plates",
        examines="the scans of each plate, and every artefact class in the taxonomy",
        record="docs/decisions/0006-artefacts-are-a-class.md",
    ),
    Stage(
        name="extract",
        summary="Extract spectra from objective-prism plates",
        examines="the traces on each prism plate, including the overlapping ones",
        record="docs/decisions/0007-prism-spectra-as-segmentation.md",
    ),
    Stage(
        name="evaluate",
        summary="Report the held-out-collection numbers",
        examines="one held-out collection per fold, and never the fold it selected on",
        record="docs/decisions/0008-evaluation-splits-by-collection.md",
    ),
)


def installed_version() -> str:
    """Return the version from installed distribution metadata.

    Reading it from anywhere else is what this function exists to avoid.
    """
    try:
        return version(DISTRIBUTION)
    except PackageNotFoundError:
        raise SystemExit(
            f"{DISTRIBUTION} is not installed, and --version reports installed "
            f"distribution metadata rather than a string in the source. Install "
            f"it and run this again."
        ) from None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=DISTRIBUTION,
        description=(
            "Machine learning for digitised astronomical photographic plates. "
            "Every subcommand reports what it examined and what it did not."
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version=installed_version(),
        help="print the installed version and exit",
    )
    stages = parser.add_subparsers(
        dest="stage",
        metavar="STAGE",
        title="stages",
        description=(
            "One subcommand per pipeline stage that has a decision record. "
            "None of them is built yet and each says so."
        ),
    )
    for stage in STAGES:
        child = stages.add_parser(stage.name, help=stage.summary)
        child.set_defaults(stage_spec=stage)
    return parser


def report_unbuilt(stage: Stage, out: TextIO) -> int:
    print(f"{stage.name}: not built yet, so nothing ran.", file=out)
    print("examined: nothing.", file=out)
    print(f"not examined: {stage.examines}.", file=out)
    print(f"the stage is decided in {stage.record}.", file=out)
    return EXIT_NOT_IMPLEMENTED


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    stage: Stage | None = getattr(args, "stage_spec", None)
    if stage is None:
        parser.print_help()
        return EXIT_NOT_IMPLEMENTED
    return report_unbuilt(stage, sys.stdout)


if __name__ == "__main__":
    raise SystemExit(main())
