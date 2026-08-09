"""The structured extraction a transcribed page produces, and what refuses one.

``docs/decisions/0016-transcription-component-scope.md`` fixes two outputs for
the transcription component and this module answers for the second of them. The
first, the page description, is a PAGE XML document in a schema published by
somebody else; ``PAGE_DESCRIPTION_SCHEMA`` below names it and nothing here
validates it, because the schema for that output is not this repository's to
carry.

The rule the record states in one sentence is the rule this module refuses in
one function: an extraction whose field carries a value and no source-line
reference is refused, and there is no argument under which it is accepted. A
value with no line behind it cannot be corrected once, so it has to be corrected
everywhere it was used, which is the failure the whole two-output arrangement
exists to prevent.

## Where the rules come from

The schema file beside this module is the authority for what an extraction may
contain, and this module is the code that decides each rule. The field names,
which parts of a read field are required, and the bounds on a confidence are all
read out of that file at import time rather than written here a second time. A
list in this module would be the copy that goes stale, and the drift would be
invisible: both would be the same eight strings until one of them moved.

``tests/test_transcription.py`` is what holds the schema against the record's own
table, so a field added to one and not the other reds the suite rather than
being discovered by a consumer.

## Where this validator is stricter than the schema, and where it is narrower

Stricter in one place, and deliberately. The schema gives its strings
``minLength: 1``, which a general JSON Schema validator satisfies with a single
space. This refuses a string that is blank as well as one that is empty, for the
reason ``model.py`` gives for the same choice: a blank is what a mapping from an
absent source produces, it passes every check that asks whether a field is
present, and it says nothing while looking exactly like a value.

Narrower in that this is not a JSON Schema engine and does not claim to be. It
reads five things out of the schema document: the top-level required keys, the
top-level property names, the field names, the required parts of a read field,
and the bounds on a confidence. It does not read ``pattern``, it does not follow
a ``$ref`` it was not told about, and it would not notice a keyword somebody
added to the schema tomorrow. Adding a rule to the schema therefore means adding
the code that decides it, and the schema is not a place where a rule can be
declared into force.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from importlib.resources import files
from typing import Any, Final

# The published schema of the first output, named rather than validated. The
# record fixes this exact URL and ``tests/test_transcription.py`` reads it back
# out of the record, so the two cannot drift apart in silence.
PAGE_DESCRIPTION_SCHEMA: Final = (
    "https://www.primaresearch.org/schema/PAGE/gts/pagecontent/2019-07-15/"
)

SCHEMA_RESOURCE: Final = "schemas/transcription_extraction.schema.json"


class ExtractionRefused(ValueError):
    """Raised where an extraction document may not be written or read.

    Its own type rather than a bare ``ValueError``, so a caller that means to
    handle a malformed document cannot swallow an unrelated one by accident.
    """


def load_schema() -> dict[str, Any]:
    """The extraction schema, read from the file that ships with this package."""
    resource = files(__package__ or "plattenschrank").joinpath(SCHEMA_RESOURCE)
    loaded: object = json.loads(resource.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ExtractionRefused(
            f"{SCHEMA_RESOURCE} does not hold an object, so nothing here has a "
            "rule to decide"
        )
    return loaded


SCHEMA: Final = load_schema()

_READ_FIELD: Final = SCHEMA["$defs"]["read_field"]
_CONFIDENCE: Final = _READ_FIELD["properties"]["confidence"]

# Everything below is derived from the schema above. None of it is a list.
EXTRACTION_SCHEMA_ID: Final[str] = SCHEMA["$id"]
DOCUMENT_KEYS: Final[frozenset[str]] = frozenset(SCHEMA["properties"])
REQUIRED_DOCUMENT_KEYS: Final[frozenset[str]] = frozenset(SCHEMA["required"])
FIELD_NAMES: Final[frozenset[str]] = frozenset(
    SCHEMA["properties"]["fields"]["properties"]
)
READ_FIELD_PARTS: Final[frozenset[str]] = frozenset(_READ_FIELD["properties"])
REQUIRED_READ_FIELD_PARTS: Final[frozenset[str]] = frozenset(_READ_FIELD["required"])
CONFIDENCE_BOUNDS: Final[tuple[float, float]] = (
    _CONFIDENCE["minimum"],
    _CONFIDENCE["maximum"],
)


def _refuse(detail: str) -> None:
    raise ExtractionRefused(detail)


def _blank(value: object) -> bool:
    """Whether a value fails to be a string carrying something."""
    return not isinstance(value, str) or not value.strip()


def _check_read_field(name: str, field: object) -> None:
    """Refuse a field of ``fields`` that is not a whole read field."""
    if not isinstance(field, Mapping):
        _refuse(f"the field {name!r} is not an object")
        return
    missing = sorted(REQUIRED_READ_FIELD_PARTS - set(field))
    if missing:
        _refuse(
            f"the field {name!r} carries no {', '.join(missing)}. Every field "
            "that was read carries a value, the line it was read from and a "
            "confidence, and a value with no line behind it is the one this "
            "component exists not to produce."
        )
    unknown = sorted(set(field) - READ_FIELD_PARTS)
    if unknown:
        _refuse(f"the field {name!r} carries {', '.join(unknown)}, which is not a part")
    for part in sorted(REQUIRED_READ_FIELD_PARTS & set(field) - {"confidence"}):
        if _blank(field[part]):
            _refuse(
                f"the {part} of the field {name!r} is blank. A blank reads as a "
                "value to every consumer and states nothing."
            )
    if "confidence" in field:
        _check_confidence(name, field["confidence"])


def _check_confidence(name: str, confidence: object) -> None:
    low, high = CONFIDENCE_BOUNDS
    if isinstance(confidence, bool) or not isinstance(confidence, int | float):
        _refuse(f"the confidence of the field {name!r} is not a number")
        return
    if confidence < low or confidence > high:
        _refuse(
            f"the confidence of the field {name!r} is {confidence}, outside "
            f"the {low} to {high} the schema allows"
        )


def _check_named_fields(key: str, entries: object) -> frozenset[str]:
    """Refuse a mapping under ``key`` that names something not a field."""
    if not isinstance(entries, Mapping):
        _refuse(f"{key} is not an object")
        return frozenset()
    unknown = sorted(set(entries) - FIELD_NAMES)
    if unknown:
        _refuse(
            f"{key} names {', '.join(unknown)}, which "
            f"{'are' if len(unknown) > 1 else 'is'} not a field of an extraction"
        )
    return frozenset(entries)


def validate_extraction(document: object) -> None:
    """Refuse an extraction document that may not be written or read.

    Returns nothing on a document that passes. It raises rather than returning a
    verdict because a caller that forgets to read a returned boolean writes the
    document anyway, and this is the one refusal the record says has no way
    around it.
    """
    if not isinstance(document, Mapping):
        _refuse("an extraction is an object")
        return
    missing = sorted(REQUIRED_DOCUMENT_KEYS - set(document))
    if missing:
        _refuse(f"the extraction carries no {', '.join(missing)}")
    unknown = sorted(set(document) - DOCUMENT_KEYS)
    if unknown:
        _refuse(f"the extraction carries {', '.join(unknown)}, which is not a key")
    if _blank(document.get("page_description")):
        _refuse(
            "the extraction names no page description, so no source_line in it "
            "names a line in anything"
        )
    if _blank(document.get("extraction_schema_version")):
        _refuse("the extraction states no schema version")

    read = _check_named_fields("fields", document["fields"])
    for name in sorted(read):
        _check_read_field(name, document["fields"][name])

    declined = _check_named_fields("declined", document["declined"])
    for name in sorted(declined):
        if _blank(document["declined"][name]):
            _refuse(
                f"the field {name!r} was declined with a blank reason. Declining "
                "is an outcome somebody acts on and a blank is not one."
            )

    both = sorted(read & declined)
    if both:
        _refuse(
            f"{', '.join(both)} appears under both fields and declined. A field "
            "was read or it was declined, and a document saying both says "
            "neither."
        )
