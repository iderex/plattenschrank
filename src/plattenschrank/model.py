"""The four entities every stage of this pipeline passes across its boundaries.

``docs/decisions/0003-data-model.md`` names them and names their required
fields. This module is that record expressed as types, and
``tests/test_model.py`` is what stops the two drifting apart: it reads the field
names out of the record and refuses a type that has lost one.

Three fields on a measurement come from other records rather than from 0003, and
each is named here so that a reader comparing this module against one record
does not read them as inventions. ``software_version`` and ``model_id`` are two
of the five that ``docs/decisions/0013-determinism-and-provenance.md`` makes
mandatory, and ``schema_version`` is
``docs/decisions/0015-schema-versioning.md``. The single ``uncertainty`` that
0003 names is carried as three fields, which is that record's own instruction
that it is carried per component rather than as one figure; which three, and why
a component that was not estimated is absent rather than zero, is issue #48.

## What refusal means here

A required field is refused at construction and never at the far end of the
pipeline, because construction is the last point at which the missing
information is still recoverable. The refusal covers two shapes of absence. A
value that is ``None`` is the obvious one. A string that is empty or blank is
the one worth aiming at: it is what a mapping from an archive record with a
missing column produces, it satisfies every check that asks whether a field is
present, and a row carrying it says nothing about which collection it came from
while looking exactly like a row that does.

Which fields are required is derived from the annotations rather than listed. A
field that may legitimately be absent is annotated as admitting ``None``, and
everything else is required, so adding a field to one of these types makes it
required unless its author says otherwise in the signature. A list here would be
a second place to update and the one that goes stale.

## The two explicit markers

Two fields are required and still have to be able to say "no such thing". A
detection the pipeline cannot attribute to one exposure carries
``UNATTRIBUTED``, and a measurement produced by a classical path rather than a
learned one carries ``NO_MODEL``. Both are values rather than absences, because
0013 asks for an explicit none: a blank in either place reads as a field nobody
filled in, and these two are fields somebody filled in with an answer.

## What a row is

``to_row`` returns one mapping per row, column name to value, which is what a
columnar writer consumes and what ``from_row`` reads back. The writer itself is
not here. Parquet is what 0003 names for bulk output and no library in the
locked graph writes it, so adding one is a change to ``pyproject.toml`` and
``uv.lock``, which are outside the ``Scope:`` issue #37 declares. What this
module carries is the mapping the writer would be handed, round-tripped exactly.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, fields
from typing import Self, get_args, get_type_hints

# The schema version this code holds. ``docs/decisions/0015-schema-versioning.md``
# is where it is decided and what it means to move it, and
# ``tests/test_model.py`` reads the version out of that record and refuses a
# mismatch, so the two cannot move apart without the suite saying so.
SCHEMA_VERSION = "1.0"

# The exposure a detection is attributed to, where the pipeline cannot say which
# one. A plate carrying several exposures produces detections that belong to one
# of them and the attribution is not always recoverable from the scan.
UNATTRIBUTED = "unattributed"

# The model identifier on a measurement produced without one.
NO_MODEL = "none"


class MissingRequiredField(ValueError):
    """Raised where a required field was absent or blank at construction.

    Its own type rather than a bare ``ValueError`` so that a caller mapping an
    archive record can catch this and let every other ``ValueError`` through. A
    handler that caught both would swallow a genuine parse failure and report it
    as a missing field, which are opposite statements about the archive.
    """


def optional_fields(entity: type[Entity]) -> frozenset[str]:
    """The field names whose annotation admits ``None``.

    Read from the annotations rather than from a list, so the signature is the
    single place a field's requiredness is declared.
    """
    return frozenset(
        name
        for name, hint in get_type_hints(entity).items()
        if type(None) in get_args(hint)
    )


@dataclass(frozen=True)
class Entity:
    """What the four entities share: refusal at construction and the row form.

    Frozen because a row that has been written and a row that is still being
    assembled are different things, and a mutable row makes them the same thing.
    A stage that needs a changed value builds a new row from this one, which
    leaves the original readable in the place it came from.
    """

    def __post_init__(self) -> None:
        optional = optional_fields(type(self))
        absent = [
            field.name
            for field in fields(self)
            if field.name not in optional and _says_nothing(getattr(self, field.name))
        ]
        if absent:
            raise MissingRequiredField(
                f"{type(self).__name__} requires "
                f"{', '.join(sorted(absent))}, and this one gave no value for "
                "them. A row that cannot say what it is about is refused here "
                "rather than written with a blank, because this is the last "
                "point at which what is missing is still recoverable. "
                "docs/decisions/0003-data-model.md and "
                "docs/decisions/0013-determinism-and-provenance.md are where "
                "the requirement is."
            )

    def to_row(self) -> dict[str, object]:
        """This entity as one row of columns, in the order the type declares."""
        return {field.name: getattr(self, field.name) for field in fields(self)}

    @classmethod
    def from_row(cls, row: Mapping[str, object]) -> Self:
        """Build this entity back out of a row, refusing a row of another shape.

        Both directions are refused rather than only the missing one. A column
        the type does not know is as much a mismatch as a column it wanted and
        did not get, and reading a row that carries an unknown column as though
        it were understood is how a field silently stops arriving.
        """
        declared = {field.name for field in fields(cls)}
        given = set(row)
        unknown = sorted(given - declared)
        missing = sorted(declared - given)
        if unknown or missing:
            raise MissingRequiredField(
                f"{cls.__name__} is written as the columns "
                f"{', '.join(sorted(declared))}. This row "
                f"{_column_complaint(unknown, missing)}."
            )
        # The row is untyped by construction: it came off a file or a wire, and
        # nothing about its shape is known until the checks above have run and
        # the constructor below has refused what it refuses.
        build: Callable[..., Self] = cls
        return build(**row)


def _says_nothing(value: object) -> bool:
    """Whether this value fails to say anything, for a field that must."""
    if value is None:
        return True
    return isinstance(value, str) and not value.strip()


def _column_complaint(unknown: list[str], missing: list[str]) -> str:
    parts: list[str] = []
    if missing:
        parts.append(f"is missing {', '.join(missing)}")
    if unknown:
        parts.append(f"carries {', '.join(unknown)}, which it does not know")
    return " and ".join(parts)


@dataclass(frozen=True)
class Plate(Entity):
    """The physical object, as one digitisation of it."""

    # The archive the plate belongs to. Required on this and on every other
    # entity here, because the evaluation protocol holds out whole collections
    # and a row that has lost this cannot be put on either side of that split.
    collection_id: str
    # Unique inside its collection and only inside it. Two archives numbering a
    # plate the same way is the normal case rather than a collision to resolve.
    plate_id: str
    # The digitisation being described. One plate can be scanned more than once,
    # and two scans of one plate disagree about pixel positions.
    scan_id: str


@dataclass(frozen=True)
class Exposure(Entity):
    """One shutter opening on a plate, of which a plate may carry several."""

    exposure_id: str
    collection_id: str
    plate_id: str
    # When the shutter opened, as the archive records it, and absent where the
    # archive does not record it. Kept as the archive's own text rather than
    # parsed into a moment here: these are records written by hand over a
    # century, and a stage that parses is a stage that can refuse one, which is
    # a decision that belongs where the parsing happens rather than in the type
    # everything crosses.
    start_time: str | None
    # How long it stayed open, in seconds. Absent is recorded as absent, and
    # never as zero, because a zero-second exposure and an exposure whose length
    # nobody wrote down read the same to every consumer and mean opposite
    # things.
    duration: float | None


@dataclass(frozen=True)
class Detection(Entity):
    """Something found on a scan at a pixel position."""

    detection_id: str
    collection_id: str
    plate_id: str
    scan_id: str
    # The exposure this is attributed to, or ``UNATTRIBUTED`` where the pipeline
    # cannot say. Required either way: the field always carries an answer, and
    # one of the answers is that there is not one.
    exposure_id: str
    # Pixel position on the scan, in the scan's own frame. Not sky coordinates:
    # those depend on a world coordinate solution that a detection is found
    # without and that can be replaced afterwards.
    x: float
    y: float
    # The detection stage that produced it, so that two detectors run over one
    # scan produce rows that can be told apart.
    detector_id: str


@dataclass(frozen=True)
class Measurement(Entity):
    """A calibrated number attached to a detection."""

    detection_id: str
    collection_id: str
    plate_id: str
    scan_id: str
    # What is being measured, and the unit it is measured in. The unit is on the
    # row rather than in a document, because a document that says what the unit
    # is stops travelling with the file on the first copy.
    quantity: str
    value: float
    unit: str
    # The calibration that produced the number, from
    # docs/decisions/0005-photometric-response.md, and the version of this
    # software and the model that produced it, from
    # docs/decisions/0013-determinism-and-provenance.md. All three are required.
    # A number that cannot say which calibration produced it cannot be withdrawn
    # cleanly when that calibration turns out to be wrong.
    calibration_id: str
    software_version: str
    # The model used, or ``NO_MODEL`` where the path was classical.
    model_id: str
    # The three components of the uncertainty, kept apart. A consumer who wants
    # one number can add them; a consumer who wants to know why an error bar is
    # large cannot recover the parts from a sum. Absent where a component was
    # not estimated, which is not the same as zero. Which three and what each
    # one covers is issue #48.
    uncertainty_measurement: float | None
    uncertainty_calibration: float | None
    uncertainty_transformation: float | None
    # Last because it has a default, and it has a default because every
    # measurement this code writes is written against the version this code
    # holds. A row read back from a file carries whatever version it was written
    # against, which is the case the field exists for.
    schema_version: str = SCHEMA_VERSION


# The five fields docs/decisions/0013-determinism-and-provenance.md makes
# mandatory on a measurement row. Named here so that the suite can refuse the
# loss of any one of them by name rather than by asserting over every field,
# which would pass if one of the five were quietly made optional.
MANDATORY_PROVENANCE = (
    "plate_id",
    "collection_id",
    "software_version",
    "calibration_id",
    "model_id",
)
