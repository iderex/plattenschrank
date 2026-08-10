"""The annotation exchange format, and the validator that decides a batch.

``docs/decisions/0009-label-scarcity-is-the-binding-constraint.md`` fixes the
name ``plateanno`` and fixes the schema location as
``docs/schemas/plateanno/``, one versioned file per released version, with the
version written inside the file. That directory is the published location and
the authority. This module decides a batch against it, and it is the only
coupling between this repository and any annotation platform, which is the whole
point of the format being a file.

## Why the schema is in two places

``docs/`` is not shipped. The wheel carries ``src/plattenschrank`` and an
editable install resolves a package resource against the source package
directory, so a validator that read only the published copy would have no rules
at all once installed. The package therefore carries the same bytes under
``schemas/plateanno/``.

That is a copy, and a copy drifts. ``tests/test_plateanno.py`` compares the two
files byte for byte and reds where they differ, so the drift is refused rather
than disclosed. The published file is the one to edit; the other is the one that
travels.

## Everything here is derived from the schema

The key lists, the bounds, the pattern an annotator reference has to match and
the version this code speaks are all read out of the schema document at import
time. Nothing below is a second copy that could drift. What is NOT derived is
which rules exist: a keyword added to the schema tomorrow is not decided by
anything here until somebody writes the code that decides it, which is the same
bound ``transcription.py`` states about its own validator and for the same
reason.

## What the format has to be able to say

Disagreement. Two people labelling one subject differently is information, and a
format that keeps a majority throws it away. Annotations are a sequence and
never a mapping keyed by subject, so two answers about one subject are two rows.
``Batch`` round-trips through the types here, and the test that both survive is
what would red if anybody keyed them.

Abstention. A person saying they cannot tell is the most useful label a hard
example can get. It is ``abstained`` with no class and no confidence, rather
than a row that is missing, because a missing row and an unlabelled subject read
the same and mean opposite things.

## The class identifier, and what this cannot check

A batch names the taxonomy it was labelled against, and ``validate_batch`` is
handed the classes that taxonomy holds. A class outside them is refused. The
artefact taxonomy this board will use is issue #49 and does not exist, so
nothing here names a class, and the classes are an argument rather than a
constant for exactly that reason.

WHAT IS NOT CHECKED is that ``taxonomy_id`` names the taxonomy whose classes
were passed. Nothing in this tree holds taxonomies, so the two are supplied by
the same caller and this module cannot tell a mismatched pair from a matched
one. That is stated rather than closed.

## Personal data, and the narrower claim this module actually makes

No property in the schema is a direct identifier: there is no name, no address,
no account and no signature, and ``tests/test_plateanno.py`` refuses one being
added under any of those names.

THAT IS NOT THE SAME AS SAYING A BATCH CARRIES NO PERSONAL DATA, and the wider
claim would be false. ``docs/personal-data-inventory.md`` entry 5 is about this
format: timing and order separate two annotators, and anyone who knows which of
them worked when has a name to attach. ``THE_RESIDUAL`` below names the fields
that carry it. The format is shaped to keep the direct identifier out and it
does not make a batch anonymous, and no test here says otherwise.
"""

from __future__ import annotations

import json
import re
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass
from importlib.resources import files
from typing import Any, Final, Self

SCHEMA_RESOURCE: Final = "schemas/plateanno/1.0.json"

# The fields that carry entry 5 of docs/personal-data-inventory.md, which is the
# residual this format keeps rather than removes. Named here so that the claim
# made above is checkable, and so that a reader who takes "no direct identifier"
# away from this module meets the sentence that narrows it.
THE_RESIDUAL: Final[frozenset[str]] = frozenset({"seconds_taken", "annotator_ref"})


class BatchRefused(ValueError):
    """Raised where a batch may not be read or written.

    Its own type rather than a bare ``ValueError``, so a caller that means to
    handle a malformed batch cannot swallow an unrelated one by accident.
    """


def load_schema() -> dict[str, Any]:
    """The plateanno schema, read from the file that ships with this package."""
    resource = files(__package__ or "plattenschrank").joinpath(SCHEMA_RESOURCE)
    loaded: object = json.loads(resource.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise BatchRefused(
            f"{SCHEMA_RESOURCE} does not hold an object, so nothing here has a "
            "rule to decide"
        )
    return loaded


SCHEMA: Final = load_schema()

_ANNOTATION: Final = SCHEMA["$defs"]["annotation"]
_REGION: Final = SCHEMA["$defs"]["region"]
_CONFIDENCE: Final = _ANNOTATION["properties"]["confidence"]

# Derived from the schema above. None of it is a list written twice.
SCHEMA_ID: Final[str] = SCHEMA["$id"]
FORMAT_VERSION: Final[str] = SCHEMA["properties"]["plateanno_version"]["const"]
BATCH_KEYS: Final[frozenset[str]] = frozenset(SCHEMA["properties"])
REQUIRED_BATCH_KEYS: Final[frozenset[str]] = frozenset(SCHEMA["required"])
ANNOTATION_KEYS: Final[frozenset[str]] = frozenset(_ANNOTATION["properties"])
REQUIRED_ANNOTATION_KEYS: Final[frozenset[str]] = frozenset(_ANNOTATION["required"])
REGION_KEYS: Final[frozenset[str]] = frozenset(_REGION["properties"])
REQUIRED_REGION_KEYS: Final[frozenset[str]] = frozenset(_REGION["required"])
CONFIDENCE_BOUNDS: Final[tuple[float, float]] = (
    _CONFIDENCE["minimum"],
    _CONFIDENCE["maximum"],
)
BATCH_ID_PATTERN: Final = re.compile(SCHEMA["properties"]["batch_id"]["pattern"])
ANNOTATOR_REF_PATTERN: Final = re.compile(
    _ANNOTATION["properties"]["annotator_ref"]["pattern"]
)


@dataclass(frozen=True)
class Region:
    """A pixel region on a scan, in the scan's own frame."""

    x: float
    y: float
    width: float
    height: float

    @classmethod
    def from_document(cls, region: Mapping[str, object]) -> Self:
        return cls(
            x=_as_number("x", region["x"]),
            y=_as_number("y", region["y"]),
            width=_as_number("width", region["width"]),
            height=_as_number("height", region["height"]),
        )

    def to_document(self) -> dict[str, object]:
        return {"x": self.x, "y": self.y, "width": self.width, "height": self.height}


@dataclass(frozen=True)
class Annotation:
    """One person's answer about one subject, including a refusal to answer."""

    subject_id: str
    collection_id: str
    plate_id: str
    scan_id: str
    region: Region
    class_id: str | None
    abstained: bool
    confidence: float | None
    seconds_taken: float
    annotator_ref: str

    @classmethod
    def from_document(cls, annotation: Mapping[str, object]) -> Self:
        confidence = annotation["confidence"]
        class_id = annotation["class_id"]
        return cls(
            subject_id=_as_text("subject_id", annotation["subject_id"]),
            collection_id=_as_text("collection_id", annotation["collection_id"]),
            plate_id=_as_text("plate_id", annotation["plate_id"]),
            scan_id=_as_text("scan_id", annotation["scan_id"]),
            region=Region.from_document(_as_object("region", annotation["region"])),
            class_id=None if class_id is None else _as_text("class_id", class_id),
            abstained=bool(annotation["abstained"]),
            confidence=(
                None if confidence is None else _as_number("confidence", confidence)
            ),
            seconds_taken=_as_number("seconds_taken", annotation["seconds_taken"]),
            annotator_ref=_as_text("annotator_ref", annotation["annotator_ref"]),
        )

    def to_document(self) -> dict[str, object]:
        return {
            "subject_id": self.subject_id,
            "collection_id": self.collection_id,
            "plate_id": self.plate_id,
            "scan_id": self.scan_id,
            "region": self.region.to_document(),
            "class_id": self.class_id,
            "abstained": self.abstained,
            "confidence": self.confidence,
            "seconds_taken": self.seconds_taken,
            "annotator_ref": self.annotator_ref,
        }


@dataclass(frozen=True)
class Batch:
    """One batch of annotations, in the order the file carried them.

    ``annotations`` is a sequence rather than a mapping keyed by subject, and
    that is the format's decision rather than a detail of this type. Keying by
    subject would keep one answer per subject, which is the majority-collapsing
    this format exists to refuse.
    """

    plateanno_version: str
    batch_id: str
    taxonomy_id: str
    annotations: tuple[Annotation, ...]

    @classmethod
    def from_document(cls, document: Mapping[str, object]) -> Self:
        annotations = _as_sequence("annotations", document["annotations"])
        return cls(
            plateanno_version=_as_text(
                "plateanno_version", document["plateanno_version"]
            ),
            batch_id=_as_text("batch_id", document["batch_id"]),
            taxonomy_id=_as_text("taxonomy_id", document["taxonomy_id"]),
            annotations=tuple(
                Annotation.from_document(_as_object("annotation", annotation))
                for annotation in annotations
            ),
        )

    def to_document(self) -> dict[str, object]:
        return {
            "plateanno_version": self.plateanno_version,
            "batch_id": self.batch_id,
            "taxonomy_id": self.taxonomy_id,
            "annotations": [
                annotation.to_document() for annotation in self.annotations
            ],
        }

    def disagreements(self) -> tuple[str, ...]:
        """The subjects more than one annotator answered about differently.

        Here rather than in a consumer because the format exists to carry this,
        and a format that carries something nobody can read out of it carries it
        in name only.
        """
        answers: dict[str, set[str | None]] = {}
        for annotation in self.annotations:
            answers.setdefault(annotation.subject_id, set()).add(annotation.class_id)
        return tuple(
            sorted(subject for subject, given in answers.items() if len(given) > 1)
        )


def validate_batch(document: object, classes: Collection[str]) -> None:
    """Refuse a batch that may not be read or written, or return nothing.

    ``classes`` is what the taxonomy named by the batch holds. It is an argument
    because no taxonomy exists in this tree yet, and a constant here would be
    this module inventing one.

    It raises rather than returning a verdict, for the reason
    ``transcription.py`` gives: a caller who forgets to read a returned boolean
    writes the file anyway.
    """
    if not isinstance(document, Mapping):
        _refuse("a batch is an object")
        return
    missing = sorted(REQUIRED_BATCH_KEYS - set(document))
    if missing:
        _refuse(f"the batch carries no {', '.join(missing)}")
    unknown = sorted(set(document) - BATCH_KEYS)
    if unknown:
        _refuse(f"the batch carries {', '.join(unknown)}, which is not a key")
    version = document["plateanno_version"]
    if version != FORMAT_VERSION:
        _refuse(
            f"the batch says it was written against plateanno {version!r} and "
            f"this reads {FORMAT_VERSION!r}. A batch is read by the version it "
            "names or it is not read."
        )
    if not BATCH_ID_PATTERN.fullmatch(_text_or_blank(document["batch_id"])):
        _refuse(
            "the batch_id is not the shape the schema allows. It is an opaque "
            "token this repository never interprets, and a sentence describing "
            "who worked on the batch is not one."
        )
    if _blank(document["taxonomy_id"]):
        _refuse("the batch names no taxonomy, so no class_id in it names anything")
    annotations = document["annotations"]
    if not isinstance(annotations, Sequence) or isinstance(annotations, str | bytes):
        _refuse("annotations is a list of annotations")
        return
    if not annotations:
        _refuse(
            "the batch carries no annotation. An empty batch and a batch whose "
            "annotations were dropped on the way here look the same, and the "
            "second is the one worth refusing."
        )
    for position, annotation in enumerate(annotations):
        _check_annotation(position, annotation, classes)


def read_batch(text: str, classes: Collection[str]) -> Batch:
    """Read one batch from the text of a plateanno file, or refuse it."""
    try:
        document: object = json.loads(text)
    except json.JSONDecodeError as failure:
        raise BatchRefused(f"this is not a plateanno file: {failure}") from failure
    validate_batch(document, classes)
    return Batch.from_document(_as_object("the batch", document))


def write_batch(batch: Batch, classes: Collection[str]) -> str:
    """Write a batch back out, having refused it if it may not be written.

    Validated on the way out as well as on the way in, because a batch this
    software assembled is as capable of naming a class nobody declared as one it
    read, and the file is what somebody else will trust.
    """
    document = batch.to_document()
    validate_batch(document, classes)
    return json.dumps(document, indent=2, sort_keys=False) + "\n"


def _refuse(detail: str) -> None:
    raise BatchRefused(detail)


def _blank(value: object) -> bool:
    """Whether a value fails to be a string carrying something."""
    return not isinstance(value, str) or not value.strip()


def _text_or_blank(value: object) -> str:
    return value if isinstance(value, str) else ""


def _as_text(name: str, value: object) -> str:
    if not isinstance(value, str):
        raise BatchRefused(f"{name} is not text")
    return value


def _as_number(name: str, value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise BatchRefused(f"{name} is not a number")
    return float(value)


def _as_object(name: str, value: object) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise BatchRefused(f"{name} is not an object")
    return value


def _as_sequence(name: str, value: object) -> Sequence[object]:
    if not isinstance(value, Sequence) or isinstance(value, str | bytes):
        raise BatchRefused(f"{name} is not a list")
    return value


def _check_annotation(
    position: int, annotation: object, classes: Collection[str]
) -> None:
    """Refuse one annotation, naming its position rather than its content.

    The position is what a person fixing the file needs. Quoting the content
    would put whatever the batch carried into a diagnostic, and a diagnostic is
    a place data escapes to.
    """
    where = f"annotation {position}"
    if not isinstance(annotation, Mapping):
        _refuse(f"{where} is not an object")
        return
    missing = sorted(REQUIRED_ANNOTATION_KEYS - set(annotation))
    if missing:
        _refuse(f"{where} carries no {', '.join(missing)}")
    unknown = sorted(set(annotation) - ANNOTATION_KEYS)
    if unknown:
        _refuse(f"{where} carries {', '.join(unknown)}, which is not a part")
    for part in ("subject_id", "collection_id", "plate_id", "scan_id"):
        if _blank(annotation[part]):
            _refuse(
                f"the {part} of {where} is blank. A blank reads as a value to "
                "every consumer and states nothing."
            )
    if not ANNOTATOR_REF_PATTERN.fullmatch(_text_or_blank(annotation["annotator_ref"])):
        _refuse(
            f"the annotator_ref of {where} is not the shape the schema allows. "
            "It is a token that means something inside this batch and nothing "
            "outside it, and an account name or an address does not fit it."
        )
    _check_region(where, annotation["region"])
    _check_verdict(where, annotation, classes)
    seconds = annotation["seconds_taken"]
    if isinstance(seconds, bool) or not isinstance(seconds, int | float):
        _refuse(f"the seconds_taken of {where} is not a number")
    elif seconds < 0:
        _refuse(f"the seconds_taken of {where} is negative")


def _check_region(where: str, region: object) -> None:
    if not isinstance(region, Mapping):
        _refuse(f"the region of {where} is not an object")
        return
    missing = sorted(REQUIRED_REGION_KEYS - set(region))
    if missing:
        _refuse(
            f"the region of {where} carries no {', '.join(missing)}. A region "
            "that does not say where it is cannot be shown to a second "
            "annotator, so agreement on it cannot be computed."
        )
    unknown = sorted(set(region) - REGION_KEYS)
    if unknown:
        _refuse(f"the region of {where} carries {', '.join(unknown)}")
    for side in ("width", "height"):
        extent = region[side]
        if isinstance(extent, bool) or not isinstance(extent, int | float):
            _refuse(f"the {side} of the region of {where} is not a number")
        elif extent <= 0:
            _refuse(
                f"the {side} of the region of {where} is {extent}, and a region "
                "with no extent covers no pixel"
            )
    for corner in ("x", "y"):
        if isinstance(region[corner], bool) or not isinstance(
            region[corner], int | float
        ):
            _refuse(f"the {corner} of the region of {where} is not a number")


def _check_verdict(
    where: str, annotation: Mapping[str, object], classes: Collection[str]
) -> None:
    """Refuse an annotation that answers twice or not at all.

    An abstention and a class are the two answers. A row carrying both says
    neither, and a row carrying neither is the missing row this format refuses
    to let an abstention become.
    """
    abstained = annotation["abstained"]
    if not isinstance(abstained, bool):
        _refuse(f"the abstained of {where} is not true or false")
        return
    class_id = annotation["class_id"]
    confidence = annotation["confidence"]
    if abstained:
        if class_id is not None:
            _refuse(
                f"{where} abstained and also names a class. Abstaining is an "
                "outcome of its own and not a class with a note attached."
            )
        if confidence is not None:
            _refuse(
                f"{where} abstained and also carries a confidence. There is "
                "nothing for it to be a confidence in."
            )
        return
    if _blank(class_id):
        _refuse(
            f"{where} names no class and did not abstain, so it says nothing. "
            "An annotator who could not tell abstains, which is recorded rather "
            "than left out."
        )
    elif isinstance(class_id, str) and class_id not in classes:
        _refuse(
            f"{where} names the class {class_id!r}, which the taxonomy this "
            "batch was labelled against does not hold. A class nobody declared "
            "is a label nothing can be trained against."
        )
    if isinstance(confidence, bool) or not isinstance(confidence, int | float):
        _refuse(f"the confidence of {where} is not a number")
        return
    low, high = CONFIDENCE_BOUNDS
    if confidence < low or confidence > high:
        _refuse(
            f"the confidence of {where} is {confidence}, outside the {low} to "
            f"{high} the schema allows"
        )
