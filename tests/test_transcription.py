"""What refuses a structured extraction, and what holds it to its record.

``docs/decisions/0016-transcription-component-scope.md`` states one rule in one
sentence: an extraction whose field carries a value and no source-line reference
is refused, under no configuration. Most of this file is that rule, taken one
field at a time, because a single case covering all eight passes while seven of
the eight refusals are missing.

The rest holds the schema against the record. The record's table names the eight
fields and the schema file names them again as keys, so the comparison runs in
both directions: a field in the record that the schema lacks, and a field in the
schema that the record does not name, are both red.
"""

from __future__ import annotations

import inspect
import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from plattenschrank.transcription import (
    FIELD_NAMES,
    PAGE_DESCRIPTION_SCHEMA,
    SCHEMA,
    ExtractionRefused,
    load_schema,
    validate_extraction,
)

pytestmark = pytest.mark.unit

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
TRANSCRIPTION_RECORD = (
    REPOSITORY_ROOT / "docs/decisions/0016-transcription-component-scope.md"
)

# A field name as the record writes one in its table: lower case, words joined
# by underscores, inside backticks. Anything else in a cell is prose.
FIELD_IN_A_TABLE = re.compile(r"`([a-z_]+)`")

# The section of the record whose table names the fields. Named here so that a
# table added elsewhere in the record does not silently join the comparison.
FIELD_TABLE_SECTION = "The fields of the structured extraction"

# The PAGE schema URL as the record writes it, in backticks and ending a
# sentence. Matched rather than compared, so the record can move the version in
# the URL and this still finds the one it names.
PAGE_SCHEMA_IN_THE_RECORD = r"`(https://www\.primaresearch\.org/schema/PAGE/[^`]+/)`\."


def fields_the_record_names() -> tuple[str, ...]:
    """The field names the record's own table writes, in the order it writes."""
    names: list[str] = []
    section = None
    for line in TRANSCRIPTION_RECORD.read_text(encoding="utf-8").splitlines():
        if line.startswith("### "):
            section = line.removeprefix("### ").strip()
            continue
        if section == FIELD_TABLE_SECTION and line.startswith("|"):
            names.extend(FIELD_IN_A_TABLE.findall(line.split("|")[1]))
    return tuple(names)


def an_extraction() -> dict[str, Any]:
    """A document that passes, with every field read and none declined."""
    return {
        "extraction_schema_version": "1.0",
        "page_description": "envelope-00417.page.xml",
        "fields": {
            name: {
                "value": f"what line {n} appears to say",
                "source_line": f"r1_l{n}",
                "confidence": 0.87,
            }
            for n, name in enumerate(sorted(FIELD_NAMES), start=1)
        },
        "declined": {},
    }


def test_a_conforming_extraction_passes() -> None:
    validate_extraction(an_extraction())


def test_a_declined_field_is_absent_from_fields_and_carries_its_reason() -> None:
    document = an_extraction()
    del document["fields"]["observer"]
    document["declined"]["observer"] = "the signature is a monogram nobody here reads"
    validate_extraction(document)


@pytest.mark.parametrize("name", sorted(FIELD_NAMES))
def test_a_field_with_a_value_and_no_source_line_is_refused(name: str) -> None:
    """The rule the record states, one field at a time.

    One case per field rather than one case for all eight, because a document
    that drops the reference from every field at once passes a validator that
    only ever looks at the first.
    """
    document = an_extraction()
    del document["fields"][name]["source_line"]
    with pytest.raises(ExtractionRefused, match=f"{name}.*source_line"):
        validate_extraction(document)


@pytest.mark.parametrize("name", sorted(FIELD_NAMES))
@pytest.mark.parametrize("reference", ["", " ", "\t"])
def test_a_field_whose_source_line_is_blank_is_refused(
    name: str, reference: str
) -> None:
    """The near-miss, and the one somebody will actually write.

    A reference that is present and says nothing satisfies every check that asks
    whether the key is there. It is what a mapping from a page description with
    no matching line produces, and the field it leaves behind is a value nobody
    can trace.
    """
    document = an_extraction()
    document["fields"][name]["source_line"] = reference
    with pytest.raises(ExtractionRefused, match=f"source_line.*{name}"):
        validate_extraction(document)


@pytest.mark.parametrize("name", sorted(FIELD_NAMES))
def test_a_field_with_no_confidence_is_refused(name: str) -> None:
    document = an_extraction()
    del document["fields"][name]["confidence"]
    with pytest.raises(ExtractionRefused, match=f"{name}.*confidence"):
        validate_extraction(document)


@pytest.mark.parametrize("confidence", [-0.1, 1.1, "high", True, None])
def test_a_confidence_outside_its_bounds_is_refused(confidence: object) -> None:
    document = an_extraction()
    document["fields"]["date"]["confidence"] = confidence
    with pytest.raises(ExtractionRefused, match="confidence"):
        validate_extraction(document)


def test_a_field_read_and_declined_at_once_is_refused() -> None:
    """Both readings at once is neither reading, so it is refused rather than
    resolved in favour of one of them."""
    document = an_extraction()
    document["declined"]["telescope"] = "the word is struck through"
    with pytest.raises(ExtractionRefused, match="telescope"):
        validate_extraction(document)


def test_a_decline_with_a_blank_reason_is_refused() -> None:
    document = an_extraction()
    del document["fields"]["emulsion"]
    document["declined"]["emulsion"] = "   "
    with pytest.raises(ExtractionRefused, match="emulsion"):
        validate_extraction(document)


@pytest.mark.parametrize("key", ["fields", "declined"])
def test_a_name_that_is_not_a_field_is_refused(key: str) -> None:
    document = an_extraction()
    entry: object = "the sky was clear" if key == "declined" else {"value": "2 arcsec"}
    document[key]["seeing"] = entry
    with pytest.raises(ExtractionRefused, match="seeing"):
        validate_extraction(document)


@pytest.mark.parametrize(
    "key", ["extraction_schema_version", "page_description", "fields", "declined"]
)
def test_a_document_missing_a_required_key_is_refused(key: str) -> None:
    document = an_extraction()
    del document[key]
    with pytest.raises(ExtractionRefused, match=key):
        validate_extraction(document)


def test_an_extraction_that_names_no_page_description_is_refused() -> None:
    """A source_line names a line in a document, so a document with no name
    leaves every reference in it pointing at nothing."""
    document = an_extraction()
    document["page_description"] = "  "
    with pytest.raises(ExtractionRefused, match="page description"):
        validate_extraction(document)


def test_the_validator_takes_the_document_and_nothing_else() -> None:
    """The record says there is no configuration under which a value with no
    source line is accepted.

    A test that greps for a configuration key nobody has added passes until
    somebody adds one. This refuses the shape instead: a second parameter is how
    the relaxation would arrive, whatever it were called.
    """
    parameters = list(inspect.signature(validate_extraction).parameters)
    assert parameters == ["document"], (
        "validate_extraction takes one argument. A second one is where a "
        "caller would be handed the choice the record says nobody has."
    )


def test_the_schema_names_the_fields_the_record_names() -> None:
    named = fields_the_record_names()
    assert set(named) == set(FIELD_NAMES), (
        "docs/decisions/0016-transcription-component-scope.md and "
        "src/plattenschrank/schemas/transcription_extraction.schema.json name "
        "different fields"
    )


def test_the_record_comparison_reads_a_record_that_names_fields() -> None:
    """Fail closed.

    The comparison above passes trivially against a record whose table moved or
    was renamed, because two empty sets are equal. This is what refuses that
    case rather than reporting it as agreement.
    """
    assert fields_the_record_names(), (
        f"docs/decisions/0016-transcription-component-scope.md has no field "
        f"table under '### {FIELD_TABLE_SECTION}', so the comparison above "
        "compares nothing"
    )


def test_the_page_description_schema_is_the_one_the_record_names() -> None:
    text = TRANSCRIPTION_RECORD.read_text(encoding="utf-8")
    named = re.search(PAGE_SCHEMA_IN_THE_RECORD, text)
    assert named is not None, (
        "the record names no PAGE schema URL in backticks, so there is nothing "
        "to hold the module against"
    )
    assert named.group(1) == PAGE_DESCRIPTION_SCHEMA


def test_the_schema_file_and_the_loaded_schema_are_the_same_document() -> None:
    """The module reads its rules out of the file that ships beside it.

    Without this, the file could be edited and the module go on deciding
    whatever it was built with, which is the drift the arrangement exists to
    prevent.
    """
    on_disk = json.loads(
        (
            REPOSITORY_ROOT
            / "src/plattenschrank/schemas/transcription_extraction.schema.json"
        ).read_text(encoding="utf-8")
    )
    assert on_disk == SCHEMA
    assert load_schema() == on_disk


def test_every_field_of_the_schema_requires_all_three_parts() -> None:
    """The rule is on every field rather than on the ones somebody remembered."""
    read_field = SCHEMA["$defs"]["read_field"]
    assert set(read_field["required"]) == {"value", "source_line", "confidence"}
    for name in FIELD_NAMES:
        entry = SCHEMA["properties"]["fields"]["properties"][name]
        assert entry == {"$ref": "#/$defs/read_field"}, (
            f"the field {name} in the schema does not point at the definition "
            "that requires a source line"
        )


def test_a_document_the_validator_passed_is_json(tmp_path: Path) -> None:
    """An extraction is a JSON document, so a document that passes is writable
    and reads back as itself."""
    document = an_extraction()
    validate_extraction(document)
    path = tmp_path / "extraction.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    read_back = json.loads(path.read_text(encoding="utf-8"))
    assert read_back == deepcopy(document)
    validate_extraction(read_back)
