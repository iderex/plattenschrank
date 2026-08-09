"""The four entities, held against the records that define them.

``src/plattenschrank/model.py`` is three decision records expressed as types,
and a type layer that has drifted from its record is worse than one that never
had a record: the record is what a reader trusts when they are deciding whether
a column means what they think it means.

So the field names here are read out of the records rather than written down a
second time. A field dropped from a type reds the suite naming that field, and
a version moved in one place and not the other reds it naming both values.

## What the record comparison can and cannot see

It reads the field tables and it is bounded by what a table says. Two of the
measurement record's entries are prose rather than names, and both are expanded
here with the reason next to them rather than silently: ``and its plate keys``
names three columns without writing them, and ``uncertainty`` is one entry that
0003's own text says is carried per component. Those two expansions are the
only place this file restates rather than reads, and each is a comparison a
reader can make by opening the record.

What no comparison here makes is whether a field *means* what its row of the
record says. That is a judgement, no reading of the tree makes it, and the
review is where a wrong one is caught.

## The refusal, and how it is proved

Each of the five provenance fields is refused separately rather than as a set,
because a check that asserts over all five at once passes when one of them is
quietly made optional. Both shapes of absence are covered per field. ``None`` is
the obvious one and the blank string is the one worth aiming at: it is what a
mapping from an archive record with a missing column produces, and it passes
every check that asks only whether a field is present.
"""

from __future__ import annotations

import re
from dataclasses import fields
from pathlib import Path
from typing import Any

import pytest

from plattenschrank.model import (
    MANDATORY_PROVENANCE,
    NO_MODEL,
    SCHEMA_VERSION,
    UNATTRIBUTED,
    Detection,
    Entity,
    Exposure,
    Measurement,
    MissingRequiredField,
    Plate,
    optional_fields,
)

pytestmark = pytest.mark.unit

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
DATA_MODEL_RECORD = REPOSITORY_ROOT / "docs/decisions/0003-data-model.md"
PROVENANCE_RECORD = (
    REPOSITORY_ROOT / "docs/decisions/0013-determinism-and-provenance.md"
)
VERSIONING_RECORD = REPOSITORY_ROOT / "docs/decisions/0015-schema-versioning.md"

# A field name as the records write one: lower case, words joined by
# underscores, inside backticks. Anything else in a table cell is prose.
FIELD_IN_A_TABLE = re.compile(r"`([a-z_]+)`")

# The two entries of the measurement table that name columns without writing
# them. Each is expanded to what the record's own text says it covers, and this
# mapping is the whole of what this file restates.
PROSE_IN_THE_MEASUREMENT_TABLE = {
    # "`detection_id` and its plate keys". The plate keys are the three fields
    # the Plate table names, and 0003 closes with the sentence that every row of
    # every entity carries the collection.
    "detection_id": ("detection_id", "collection_id", "plate_id", "scan_id"),
    # "Carried per component rather than as one figure". Which components, and
    # why one that was not estimated is absent rather than zero, is issue #48.
    "uncertainty": (
        "uncertainty_measurement",
        "uncertainty_calibration",
        "uncertainty_transformation",
    ),
}

# Fields on a type that no table in 0003 names, each with the record it comes
# from. Without this the comparison below would either miss an invented field or
# refuse three fields that are required by a different record.
SOURCED_ELSEWHERE = {
    "software_version": "docs/decisions/0013-determinism-and-provenance.md",
    "model_id": "docs/decisions/0013-determinism-and-provenance.md",
    "schema_version": "docs/decisions/0015-schema-versioning.md",
}

ENTITIES: tuple[type[Entity], ...] = (Plate, Exposure, Detection, Measurement)


def fields_named_by(record: Path) -> dict[str, tuple[str, ...]]:
    """The field names each `###` section of a record's tables writes.

    A table cell that carries no backticked name contributes nothing, which is
    what makes the header row and the separator row need no special case.
    """
    named: dict[str, list[str]] = {}
    section = None
    for line in record.read_text(encoding="utf-8").splitlines():
        if line.startswith("### "):
            section = line.removeprefix("### ").strip()
            named.setdefault(section, [])
            continue
        if section is not None and line.startswith("|"):
            named[section].extend(FIELD_IN_A_TABLE.findall(line.split("|")[1]))
    return {section: tuple(names) for section, names in named.items()}


def expand(names: tuple[str, ...]) -> tuple[str, ...]:
    """Replace the measurement table's two prose entries with what they cover."""
    expanded: list[str] = []
    for name in names:
        expanded.extend(PROSE_IN_THE_MEASUREMENT_TABLE.get(name, (name,)))
    return tuple(expanded)


def a_plate() -> Plate:
    return Plate(collection_id="dasch", plate_id="mc12345", scan_id="scan-1")


def an_exposure(*, sparse: bool = False) -> Exposure:
    return Exposure(
        exposure_id="exp-2",
        collection_id="dasch",
        plate_id="mc12345",
        start_time=None if sparse else "1913-11-04T21:40:00",
        duration=None if sparse else 3600.0,
    )


def a_detection() -> Detection:
    return Detection(
        detection_id="det-7",
        collection_id="dasch",
        plate_id="mc12345",
        scan_id="scan-1",
        exposure_id=UNATTRIBUTED,
        x=1024.5,
        y=2048.25,
        detector_id="classical-baseline",
    )


def a_measurement(*, sparse: bool = False) -> Measurement:
    return Measurement(
        detection_id="det-7",
        collection_id="dasch",
        plate_id="mc12345",
        scan_id="scan-1",
        quantity="instrumental_magnitude",
        value=13.75,
        unit="mag",
        calibration_id="curve-4",
        software_version="0.0.0",
        model_id=NO_MODEL,
        uncertainty_measurement=None if sparse else 0.02,
        uncertainty_calibration=None if sparse else 0.11,
        uncertainty_transformation=None if sparse else 0.08,
    )


# Both shapes of every entity that has an optional field: one with every
# optional field populated and one with every one of them absent. Without the
# second, a round trip proves nothing about the columns that are allowed to be
# empty, which are the columns a writer is most likely to mishandle.
EVERY_SHAPE: tuple[Entity, ...] = (
    a_plate(),
    an_exposure(),
    an_exposure(sparse=True),
    a_detection(),
    a_measurement(),
    a_measurement(sparse=True),
)


@pytest.mark.parametrize("entity", EVERY_SHAPE, ids=lambda e: type(e).__name__)
def test_a_row_written_and_read_back_is_the_row_it_started_as(entity: Entity) -> None:
    assert type(entity).from_row(entity.to_row()) == entity


def test_the_round_trip_covers_every_field_of_every_entity() -> None:
    """The parametrised case above is only worth what its instances reach.

    An instance that left a field out would round trip perfectly and prove
    nothing about that field, so what is asserted here is coverage rather than
    equality: every field of every entity is populated by at least one shape,
    and every optional field is absent in at least one.
    """
    for entity_type in ENTITIES:
        shapes = [row for row in EVERY_SHAPE if type(row) is entity_type]
        assert shapes, f"no shape of {entity_type.__name__} is round tripped"
        declared = {field.name for field in fields(entity_type)}
        populated = {
            name
            for shape in shapes
            for name, value in shape.to_row().items()
            if value is not None
        }
        assert populated == declared, (
            f"{entity_type.__name__} is round tripped without a value in "
            f"{', '.join(sorted(declared - populated))}"
        )
        for name in optional_fields(entity_type):
            assert any(shape.to_row()[name] is None for shape in shapes), (
                f"{entity_type.__name__}.{name} may be absent and no shape here "
                "is missing it, so the round trip never reads an absent column"
            )


@pytest.mark.parametrize("missing", MANDATORY_PROVENANCE)
@pytest.mark.parametrize("instead", [None, "", "   "], ids=["none", "blank", "spaces"])
def test_a_measurement_without_a_provenance_field_is_refused(
    missing: str, instead: object
) -> None:
    row = a_measurement().to_row()
    row[missing] = instead
    with pytest.raises(MissingRequiredField) as refusal:
        Measurement.from_row(row)
    assert missing in str(refusal.value)


def test_the_five_mandatory_fields_are_the_five_the_record_names() -> None:
    named = fields_named_by(PROVENANCE_RECORD)["The five mandatory fields"]
    assert named == MANDATORY_PROVENANCE


def test_the_schema_version_is_the_one_the_record_names() -> None:
    text = VERSIONING_RECORD.read_text(encoding="utf-8")
    named = re.search(r"names as current is `([0-9]+\.[0-9]+)`", text)
    assert named is not None, (
        f"{VERSIONING_RECORD.name} no longer says which version it names as "
        "current, so nothing here can be compared against it"
    )
    assert named.group(1) == SCHEMA_VERSION


def test_every_measurement_row_carries_the_schema_version() -> None:
    assert a_measurement().to_row()["schema_version"] == SCHEMA_VERSION


@pytest.mark.parametrize("entity_type", ENTITIES, ids=lambda t: t.__name__)
def test_a_type_carries_every_field_its_record_names(
    entity_type: type[Entity],
) -> None:
    named = expand(fields_named_by(DATA_MODEL_RECORD)[entity_type.__name__])
    declared = {field.name for field in fields(entity_type)}
    assert set(named) <= declared, (
        f"docs/decisions/0003-data-model.md names "
        f"{', '.join(sorted(set(named) - declared))} on {entity_type.__name__} "
        "and the type does not carry it"
    )


@pytest.mark.parametrize("entity_type", ENTITIES, ids=lambda t: t.__name__)
def test_a_type_carries_no_field_no_record_names(entity_type: type[Entity]) -> None:
    """The other direction, which is what catches a field somebody invented."""
    named = set(expand(fields_named_by(DATA_MODEL_RECORD)[entity_type.__name__]))
    declared = {field.name for field in fields(entity_type)}
    unsourced = declared - named - set(SOURCED_ELSEWHERE)
    assert not unsourced, (
        f"{entity_type.__name__} carries {', '.join(sorted(unsourced))}, which no "
        "record names. A field on the type layer is a column in every output, "
        "and a column no record names is one nobody can look up."
    )


def test_the_record_comparison_reads_a_record_that_names_fields() -> None:
    """The comparison above passes vacuously against a record it cannot read.

    A renamed heading or a table rewritten as prose would leave both directions
    comparing against an empty set, which is green and means nothing. This is
    what tells that case from a real pass.
    """
    named = fields_named_by(DATA_MODEL_RECORD)
    for entity_type in ENTITIES:
        assert named.get(entity_type.__name__), (
            f"docs/decisions/0003-data-model.md has no field table under "
            f"{entity_type.__name__}, so the comparisons above read nothing"
        )


def test_a_row_missing_a_column_is_refused_by_name() -> None:
    row = a_plate().to_row()
    del row["scan_id"]
    with pytest.raises(MissingRequiredField, match="scan_id"):
        Plate.from_row(row)


def test_a_row_carrying_a_column_the_type_does_not_know_is_refused() -> None:
    """An unknown column is refused rather than dropped.

    Dropping it reads the row as understood, which is how a field silently stops
    arriving: a writer renames a column, every reader keeps working, and the
    values that used to be there are gone from every row written afterwards.
    """
    row = a_measurement().to_row()
    row["sky_background"] = 42.0
    with pytest.raises(MissingRequiredField, match="sky_background"):
        Measurement.from_row(row)


@pytest.mark.parametrize("marker", [UNATTRIBUTED, NO_MODEL])
def test_an_explicit_marker_is_a_value_rather_than_an_absence(marker: str) -> None:
    """Both markers have to survive the check that refuses a blank.

    A marker defined as the empty string would be refused by the same rule that
    refuses a field nobody filled in, and the two are opposite statements: one
    says the pipeline cannot attribute this row, the other says nobody looked.
    """
    assert marker.strip()


def test_a_detection_that_cannot_be_attributed_still_states_an_exposure() -> None:
    attributed: Any = None
    with pytest.raises(MissingRequiredField, match="exposure_id"):
        Detection(
            detection_id="det-7",
            collection_id="dasch",
            plate_id="mc12345",
            scan_id="scan-1",
            exposure_id=attributed,
            x=1024.5,
            y=2048.25,
            detector_id="classical-baseline",
        )
    assert a_detection().exposure_id == UNATTRIBUTED
