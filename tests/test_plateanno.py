"""What a plateanno batch may be, and the four things it may not.

Issue #66 asks for a schema, a validator that refuses three named shapes, a
round trip that loses nothing including disagreement and abstention, and a test
about personal data. Each is below, and the last one is narrower than the issue
words it, deliberately.

## The personal data test, and why it is narrower than the issue asked

The issue asks for a test that no field in the default schema holds personal
data. That test cannot be written truthfully.
``docs/personal-data-inventory.md`` entry 5 is about this format and says the
opposite: timing and pace single out a person with no name field present
anywhere, and this format carries the time each annotation took because
agreement and cost are what the scarcity programme is measured in.

So what is asserted here is the narrow claim: no property in the schema is a
direct identifier, under any of the names one arrives under, and the fields that
carry the residual are named. A test written for the wide claim and proving the
narrow one is how a negative disclosure quietly becomes a positive assurance,
which is the failure this docstring exists to prevent.

## The classes are an argument

The artefact taxonomy is issue #49 and does not exist. The validator is handed
the classes a taxonomy holds, so the fixtures here declare their own, and
nothing in the package names a class. What that leaves unchecked is whether the
``taxonomy_id`` a batch names is the taxonomy those classes came from, and
nothing in this tree can check it.
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from plattenschrank.plateanno import (
    ANNOTATION_KEYS,
    BATCH_KEYS,
    CONFIDENCE_BOUNDS,
    FORMAT_VERSION,
    REGION_KEYS,
    SCHEMA,
    SCHEMA_RESOURCE,
    THE_RESIDUAL,
    Batch,
    BatchRefused,
    read_batch,
    validate_batch,
    write_batch,
)

pytestmark = pytest.mark.unit

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
PUBLISHED_SCHEMA = REPOSITORY_ROOT / "docs" / "schemas" / "plateanno" / "1.0.json"
SHIPPED_SCHEMA = REPOSITORY_ROOT / "src" / "plattenschrank" / SCHEMA_RESOURCE

# A fixture taxonomy. It is here rather than in the package because #49 has not
# built one, and a class list in the package would be this format inventing the
# taxonomy it is supposed to reference.
CLASSES = frozenset({"source", "plate-defect", "emulsion-scratch"})

# The names a direct identifier arrives under. This is a refusal vocabulary
# rather than a description of the schema: it fails when one of these is added,
# which is the only moment it could be useful.
DIRECT_IDENTIFIERS = (
    "name",
    "email",
    "mail",
    "address",
    "account",
    "user",
    "username",
    "login",
    "signature",
    "person",
    "orcid",
    "phone",
)


def an_annotation(**changed: Any) -> dict[str, Any]:
    """One conforming annotation, with whatever a test needs changed."""
    annotation: dict[str, Any] = {
        "subject_id": "cutout-1",
        "collection_id": "hamburg",
        "plate_id": "p-1",
        "scan_id": "s-1",
        "region": {"x": 10.0, "y": 20.0, "width": 32.0, "height": 32.0},
        "class_id": "source",
        "abstained": False,
        "confidence": 0.8,
        "seconds_taken": 4.5,
        "annotator_ref": "a",
    }
    annotation.update(changed)
    return annotation


def a_batch(*annotations: dict[str, Any]) -> dict[str, Any]:
    """One conforming batch, carrying the annotations a test gives it."""
    return {
        "plateanno_version": FORMAT_VERSION,
        "batch_id": "batch-0001",
        "taxonomy_id": "artefacts-0",
        "annotations": list(annotations) or [an_annotation()],
    }


AN_ABSTENTION = an_annotation(
    subject_id="cutout-2",
    class_id=None,
    abstained=True,
    confidence=None,
    annotator_ref="b",
)


def test_the_published_schema_and_the_shipped_one_say_the_same_thing() -> None:
    """The copy the package carries may not drift from the published one.

    `docs/decisions/0009-label-scarcity-is-the-binding-constraint.md` fixes the
    published location and `docs/` is not shipped, so the package carries a
    copy. This is what stops the shipped rules and the published ones parting.

    Compared as text rather than as bytes, and the difference matters here. This
    repository declares no `.gitattributes`, so on a clone that translates line
    endings the two files can be checked out with different ones while saying
    exactly the same thing, and a byte comparison would red for a reason that is
    about the checkout. `read_text` translates newlines, so what is compared is
    every character that decides a rule. Whitespace inside a line is still a
    difference and is still refused.
    """
    assert PUBLISHED_SCHEMA.read_text(encoding="utf-8") == SHIPPED_SCHEMA.read_text(
        encoding="utf-8"
    )


def test_the_schema_states_the_version_inside_the_file() -> None:
    """The record asks for this, because a copied file loses its name first."""
    assert SCHEMA["properties"]["plateanno_version"]["const"] == FORMAT_VERSION
    assert PUBLISHED_SCHEMA.name == f"{FORMAT_VERSION}.json"


def test_a_conforming_batch_is_accepted() -> None:
    validate_batch(a_batch(), CLASSES)


def test_a_batch_naming_a_class_the_taxonomy_does_not_hold_is_refused() -> None:
    """The first of the three refusals the issue names."""
    with pytest.raises(BatchRefused, match="does not hold"):
        validate_batch(
            a_batch(an_annotation(class_id="a-class-nobody-declared")), CLASSES
        )


def test_a_batch_with_a_missing_region_is_refused() -> None:
    """The second. A region that is not there cannot be shown to a second reader."""
    without = an_annotation()
    del without["region"]
    with pytest.raises(BatchRefused, match="region"):
        validate_batch(a_batch(without), CLASSES)


@pytest.mark.parametrize("side", ["width", "height"])
def test_a_region_with_no_extent_is_refused(side: str) -> None:
    """The near miss of the same refusal, and the one a click produces.

    A region present and zero-sized passes every check that asks whether a
    region is there, and it covers no pixel.
    """
    region = {"x": 1.0, "y": 2.0, "width": 4.0, "height": 4.0, side: 0.0}
    with pytest.raises(BatchRefused, match="covers no pixel"):
        validate_batch(a_batch(an_annotation(region=region)), CLASSES)


@pytest.mark.parametrize(
    "confidence", [-0.1, 1.5, "high", True], ids=["below", "above", "text", "boolean"]
)
def test_a_malformed_confidence_is_refused(confidence: object) -> None:
    """The third, in the four shapes it arrives in."""
    with pytest.raises(BatchRefused, match="confidence"):
        validate_batch(a_batch(an_annotation(confidence=confidence)), CLASSES)


def test_a_confidence_at_either_bound_is_accepted() -> None:
    """The other direction, which a refusal that refused everything would fail."""
    low, high = CONFIDENCE_BOUNDS
    validate_batch(a_batch(an_annotation(confidence=low)), CLASSES)
    validate_batch(a_batch(an_annotation(confidence=high)), CLASSES)


def test_an_abstention_is_accepted_and_carries_no_class_and_no_confidence() -> None:
    validate_batch(a_batch(AN_ABSTENTION), CLASSES)


def test_an_annotation_that_abstained_and_named_a_class_is_refused() -> None:
    """A row saying both says neither."""
    with pytest.raises(BatchRefused, match="also names a class"):
        validate_batch(a_batch(an_annotation(abstained=True, confidence=None)), CLASSES)


def test_an_annotation_that_abstained_and_carried_a_confidence_is_refused() -> None:
    with pytest.raises(BatchRefused, match="also carries a confidence"):
        validate_batch(
            a_batch(an_annotation(class_id=None, abstained=True, confidence=0.5)),
            CLASSES,
        )


def test_an_annotation_that_named_no_class_and_did_not_abstain_is_refused() -> None:
    """The missing row an abstention must not be allowed to become."""
    with pytest.raises(BatchRefused, match="says nothing"):
        validate_batch(a_batch(an_annotation(class_id=None)), CLASSES)


def test_a_batch_written_against_another_version_is_refused() -> None:
    document = a_batch()
    document["plateanno_version"] = "9.9"
    with pytest.raises(BatchRefused, match="plateanno"):
        validate_batch(document, CLASSES)


def test_a_batch_with_no_annotation_is_refused() -> None:
    """An empty batch and a batch whose rows were dropped look the same."""
    document = a_batch()
    document["annotations"] = []
    with pytest.raises(BatchRefused, match="no annotation"):
        validate_batch(document, CLASSES)


def test_a_key_the_schema_does_not_declare_is_refused() -> None:
    """Both directions, because an unknown key read as understood is how a
    field silently stops arriving."""
    document = a_batch()
    document["campaign_notes"] = "anything"
    with pytest.raises(BatchRefused, match="campaign_notes"):
        validate_batch(document, CLASSES)


@pytest.mark.parametrize(
    "annotator_ref",
    ["", "H. Kaiser", "kaiser@example.org", "A"],
    ids=["empty", "a name", "an address", "shouted"],
)
def test_an_annotator_reference_that_is_not_a_batch_local_token_is_refused(
    annotator_ref: str,
) -> None:
    """The shape is what keeps an account identity out of the default schema.

    It is a floor and not a guarantee: a platform writing an initial or a
    pseudonym passes this, and no reading of the file can tell.
    """
    with pytest.raises(BatchRefused, match="annotator_ref"):
        validate_batch(a_batch(an_annotation(annotator_ref=annotator_ref)), CLASSES)


def test_the_format_round_trips_with_disagreement_and_abstention() -> None:
    """The property the issue asks for, over the case that would lose data.

    Two annotators answered about one subject and differently, and a third
    subject was abstained on. A reader that kept one answer per subject, which
    is the majority-collapsing this format exists to refuse, loses a row here
    and this comparison reds.
    """
    document = a_batch(
        an_annotation(subject_id="cutout-1", class_id="source", annotator_ref="a"),
        an_annotation(
            subject_id="cutout-1", class_id="plate-defect", annotator_ref="b"
        ),
        AN_ABSTENTION,
    )
    text = json.dumps(document)
    once = read_batch(text, CLASSES)
    twice = read_batch(write_batch(once, CLASSES), CLASSES)
    assert once == twice
    assert once.to_document() == document
    assert len(once.annotations) == 3
    assert once.disagreements() == ("cutout-1",)


def test_two_annotators_agreeing_is_not_reported_as_a_disagreement() -> None:
    """The other direction, which a reader reporting everything would fail."""
    document = a_batch(
        an_annotation(subject_id="cutout-1", annotator_ref="a"),
        an_annotation(subject_id="cutout-1", annotator_ref="b"),
    )
    assert read_batch(json.dumps(document), CLASSES).disagreements() == ()


def test_a_batch_is_refused_on_the_way_out_as_well_as_on_the_way_in() -> None:
    """A batch this software assembled is as capable of being wrong as one it
    read, and the file is what somebody else will trust."""
    batch = Batch.from_document(deepcopy(a_batch()))
    with pytest.raises(BatchRefused, match="does not hold"):
        write_batch(batch, frozenset({"something-else"}))


def test_something_that_is_not_a_plateanno_file_is_a_refusal() -> None:
    with pytest.raises(BatchRefused, match="not a plateanno file"):
        read_batch("{not json", CLASSES)


def test_no_property_in_the_schema_is_a_direct_identifier() -> None:
    """The narrow claim, and the whole claim this file makes about identity.

    It reads every property name the schema declares at any level, so a field
    added under `$defs` is covered without this test being edited.
    """
    offending = sorted(
        name
        for name in property_names(SCHEMA)
        for identifier in DIRECT_IDENTIFIERS
        if identifier in name.lower().split("_")
    )
    assert offending == []


def test_the_residual_this_format_keeps_is_named_and_is_in_the_schema() -> None:
    """What stops the test above being read as saying a batch is anonymous.

    `docs/personal-data-inventory.md` entry 5 says timing separates two people
    with no name present. The fields that carry it are named in the module, and
    they are fields the schema really declares rather than a phrase in a
    docstring.
    """
    assert THE_RESIDUAL
    assert THE_RESIDUAL <= ANNOTATION_KEYS


def test_the_key_sets_are_read_out_of_the_schema() -> None:
    """What shows the constants above are derived rather than typed twice."""
    assert BATCH_KEYS == set(SCHEMA["properties"])
    assert ANNOTATION_KEYS == set(SCHEMA["$defs"]["annotation"]["properties"])
    assert REGION_KEYS == set(SCHEMA["$defs"]["region"]["properties"])


def property_names(node: object) -> set[str]:
    """Every property name declared anywhere in a schema document."""
    found: set[str] = set()
    if isinstance(node, dict):
        properties = node.get("properties")
        if isinstance(properties, dict):
            found.update(str(name) for name in properties)
        for value in node.values():
            found |= property_names(value)
    elif isinstance(node, list):
        for value in node:
            found |= property_names(value)
    return found
