"""The command line entry point and its subcommand structure.

No stage logic lives here. Each subcommand names the decision record that
defines the stage it will carry, reports that it examined nothing, and exits
non-zero, so that a run which did no work cannot be read as a run that covered
a collection and found nothing.

One subcommand is not a stage and is built. ``federate`` is the deliberate act
``docs/decisions/0014-local-first-and-no-default-egress.md`` reserves, and what
it does lives in ``src/plattenschrank/federate.py`` for the same reason the
stages will: this file arranges arguments and prints, and decides nothing.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import TextIO

from plattenschrank import DISTRIBUTION
from plattenschrank.egress import EgressRefused
from plattenschrank.federate import (
    CONFIRMATION,
    FederationRefused,
    federate,
    read_rows,
)

# A stage that is not built yet exits with this rather than with success. Zero
# would make an empty run indistinguishable from a run that examined a
# collection and found nothing, which is the reading this board most needs to
# prevent.
EXIT_NOT_IMPLEMENTED = 3

# This software declined to do what it was asked, which is a different answer
# from a stage that does not exist. A caller that could not tell the two apart
# would read a refusal to federate as a feature nobody had written yet.
EXIT_REFUSED = 4

# The subcommand that is not a stage.
FEDERATE = "federate"


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
    add_federate_parser(stages)
    return parser


def add_federate_parser(
    stages: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    """The one subcommand that is not a pipeline stage, and the one that acts.

    Three options and no fourth, and the absence is the point rather than an
    omission. Every option here is something the operator has to say; none of
    them is a setting that could stand between them and the confirmation.
    ``tests/test_federate.py`` holds this set to what it is, so a fourth option
    reds the suite and is argued for in the pull request that adds it.
    """
    federating = stages.add_parser(
        FEDERATE,
        help="Send measurement rows off this host, deliberately",
        description=(
            "Print a manifest of every column that would leave this host, how "
            "many rows, and what each column may carry, then send nothing "
            "unless the confirmation is given exactly. "
            "docs/decisions/0014-local-first-and-no-default-egress.md is why."
        ),
    )
    federating.add_argument(
        "--to",
        dest="destination",
        required=True,
        metavar="HOST:PORT",
        help="where the rows go, stated every time and never defaulted",
    )
    federating.add_argument(
        "--rows",
        dest="rows_path",
        required=True,
        type=Path,
        metavar="PATH",
        help="a file holding one JSON object per line, which is what is sent",
    )
    federating.add_argument(
        "--confirm",
        dest="confirmation",
        default=None,
        metavar="WORD",
        help=(
            f"send, rather than describe. Sends only for the exact word "
            f"{CONFIRMATION!r}; anything else, and its absence, describes and "
            f"sends nothing"
        ),
    )


def report_unbuilt(stage: Stage, out: TextIO) -> int:
    print(f"{stage.name}: not built yet, so nothing ran.", file=out)
    print("examined: nothing.", file=out)
    print(f"not examined: {stage.examines}.", file=out)
    print(f"the stage is decided in {stage.record}.", file=out)
    return EXIT_NOT_IMPLEMENTED


def run_federation(args: argparse.Namespace, out: TextIO) -> int:
    """Read the rows, print the manifest, and report a refusal as a refusal.

    Only this package's own refusals are caught, and they are the two types that
    exist for it. Anything else reaches the caller, because a connection that
    failed and a run this software declined are opposite statements and a
    handler that caught both would report one of them as the other.
    """
    try:
        rows = read_rows(args.rows_path)
        federate(
            args.destination,
            rows,
            confirmation=args.confirmation,
            out=out,
        )
    except (FederationRefused, EgressRefused) as refusal:
        print(f"{FEDERATE}: {refusal}", file=out)
        return EXIT_REFUSED
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "stage", None) == FEDERATE:
        return run_federation(args, sys.stdout)
    stage: Stage | None = getattr(args, "stage_spec", None)
    if stage is None:
        parser.print_help()
        return EXIT_NOT_IMPLEMENTED
    return report_unbuilt(stage, sys.stdout)


if __name__ == "__main__":
    raise SystemExit(main())
