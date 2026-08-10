"""What refuses a diagnostic that repeats something read off a page.

Plate envelopes and observing logbooks carry the names, initials and signatures
of the people who made the observations.
``docs/decisions/0014-local-first-and-no-default-egress.md`` is why that text
does not leave the host, and the way it leaves without anybody deciding to send
it is an error message: a refusal quotes the document it refused, the message
reaches a log, and the log is the file somebody attaches to a bug report.

So the rule is that no refusal repeats what a page said. This is the third of the
three checks issue #71 asks for; the other two are in ``tests/test_egress.py``.

## How every refusal is reached rather than the ones somebody remembered

A guard over "the messages I thought of" is worth what the author's memory was
worth on the day. The refusal sites in ``src/plattenschrank/transcription.py``
are read out of its parse tree instead, and the cases below have to reach every
one of them. A refusal added later with no case here reds this file naming the
line it is on, which is the failure this arrangement exists to prevent.

That only holds while ``_refuse`` is the whole refusal surface, so a second test
reads the module for a ``raise ExtractionRefused`` anywhere outside the one place
that has a reason to be there.

## What this covers and what it does not

It covers the text: the value a field was read as, the line reference it carries
and the reason a field was declined. Every document below carries the same
sentinel in all three places, so a message that repeats any of them is caught by
the same assertion.

It does not cover a confidence, and the omission is deliberate rather than an
oversight. A confidence is a number the component produced about a value, not
text somebody wrote on an envelope, and
``the confidence of the field 'observer' is 1.5, outside the 0 to 1 the schema
allows`` is a message that has to name the number to be worth printing.

It does not cover an annotation either, and that is an absence rather than a
decision. Issue #71 names transcriptions and annotations together; the annotation
exchange format is issue #66 and there is nothing in this tree to read yet, so
the surface this file guards is the one that exists.

There is no logging in this package. The refusal message and the traceback that
carries it are what a diagnostic is made of here, and both are read below. A
logging call added later is outside what this file reads.
"""

from __future__ import annotations

import ast
import inspect
import json
import traceback
from pathlib import Path
from typing import Any

import pytest

from plattenschrank import transcription
from plattenschrank.transcription import ExtractionRefused, validate_extraction

pytestmark = pytest.mark.unit

MODULE = Path(transcription.__file__)
SOURCE = MODULE.read_text(encoding="utf-8")

# Text standing in for what a hand wrote on an envelope. It is a token rather
# than a plausible name so that a message repeating it cannot be mistaken for a
# coincidence, and so that this file carries no invented person.
FROM_THE_PAGE = "PAGE-TEXT-QX7"

# Where this module's refusal may be raised with a `raise` rather than through
# the one function. `_refuse` is that function and its own body is the raise
# every other site goes through. `load_schema` runs at import time over a file
# that ships inside the package, so no document reaches it and no case below can
# trip it.
THE_DIRECT_RAISES_THAT_ARE_ALLOWED = frozenset({"_refuse", "load_schema"})


def a_read_field(**changed: Any) -> dict[str, Any]:
    """A field as the component writes one, carrying the sentinel in its text."""
    field: dict[str, Any] = {
        "value": FROM_THE_PAGE,
        "source_line": f"line-3-{FROM_THE_PAGE}",
        "confidence": 0.71,
    }
    field.update(changed)
    return field


def a_page(**changed: Any) -> dict[str, Any]:
    """A whole extraction, valid until a case below breaks one thing in it."""
    page: dict[str, Any] = {
        "extraction_schema_version": "1.0",
        "page_description": "envelope-0042.xml",
        "fields": {"observer": a_read_field()},
        "declined": {"date": f"the ink has faded over {FROM_THE_PAGE}"},
    }
    page.update(changed)
    return page


# One document per refusal the module can make, each breaking exactly one thing
# and each carrying page text somewhere a message could pick it up. The names are
# what a failure reports, so they say which refusal the case is aimed at rather
# than numbering them.
DOCUMENTS: dict[str, Any] = {
    "not an extraction at all": [FROM_THE_PAGE],
    "a required key is absent": {
        key: value for key, value in a_page().items() if key != "declined"
    },
    "a key the schema does not have": a_page(scan_notes=FROM_THE_PAGE),
    "no page description": a_page(page_description="   "),
    "no schema version": a_page(extraction_schema_version=""),
    "fields is not an object": a_page(fields=FROM_THE_PAGE),
    "fields names something that is not a field": a_page(
        fields={"plate_condition": a_read_field()}
    ),
    "a field is not an object": a_page(fields={"observer": FROM_THE_PAGE}),
    "a field is missing a part": a_page(fields={"observer": {"value": FROM_THE_PAGE}}),
    "a field carries a part that is not one": a_page(
        fields={"observer": a_read_field(hand="a second one")}
    ),
    "a field's value is blank": a_page(fields={"observer": a_read_field(value="  ")}),
    "a confidence that is not a number": a_page(
        fields={"observer": a_read_field(confidence="high")}
    ),
    "a confidence outside its bounds": a_page(
        fields={"observer": a_read_field(confidence=1.5)}
    ),
    "declined is not an object": a_page(declined=FROM_THE_PAGE),
    "declined names something that is not a field": a_page(
        declined={"plate_condition": "unreadable"}
    ),
    "declined with a blank reason": a_page(declined={"date": "   "}),
    "read and declined at once": a_page(
        fields={"observer": a_read_field()},
        declined={"observer": f"two hands wrote {FROM_THE_PAGE}"},
    ),
}


def refusal_sites(source: str) -> set[int]:
    """The line of every call to the module's one refusal, from its parse tree."""
    return {
        node.lineno
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "_refuse"
    }


def refused(document: Any, monkeypatch: pytest.MonkeyPatch) -> tuple[int, str, str]:
    """Refuse this document, and say which site did it and what it printed."""
    site: list[int] = []
    original = transcription._refuse

    def recording_refuse(detail: str) -> None:
        site.append(inspect.stack()[1].lineno)
        original(detail)

    monkeypatch.setattr(transcription, "_refuse", recording_refuse)
    try:
        validate_extraction(document)
    except ExtractionRefused as refusal:
        printed = "".join(traceback.format_exception(refusal))
        return site[0], str(refusal), printed
    raise AssertionError("this document was accepted, so no message was produced")


@pytest.mark.parametrize("case", sorted(DOCUMENTS))
def test_a_refusal_does_not_repeat_what_the_page_said(
    case: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, message, printed = refused(DOCUMENTS[case], monkeypatch)
    assert FROM_THE_PAGE not in message, (
        f"the refusal for {case!r} repeats text read off the page: {message}"
    )
    assert FROM_THE_PAGE not in printed, (
        f"the traceback for {case!r} carries text read off the page"
    )


@pytest.mark.parametrize("case", sorted(DOCUMENTS))
def test_every_case_here_carries_page_text_for_a_message_to_pick_up(case: str) -> None:
    """The assertion above passes on a document with nothing in it to leak.

    A case that lost its sentinel would go on passing and would prove nothing,
    and nothing about the failure would say which case had stopped testing.
    """
    assert FROM_THE_PAGE in json.dumps(DOCUMENTS[case], default=str)


def test_every_refusal_the_module_can_make_is_exercised_here(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The guard is worth the refusals it reaches, so it reaches all of them.

    The set on the right is read out of the module rather than written here, so
    a refusal added later with no case above reds this test naming its line.
    """
    reached = {refused(document, monkeypatch)[0] for document in DOCUMENTS.values()}
    declared = refusal_sites(SOURCE)
    assert reached == declared, (
        "these lines of src/plattenschrank/transcription.py refuse a document "
        "and no case in this file reaches them, so nothing here says whether "
        f"their message repeats a page: {sorted(declared - reached)}"
    )


def test_the_one_refusal_is_the_whole_refusal_surface() -> None:
    """What the test above assumes, held rather than assumed.

    It counts calls to one function. A refusal raised directly would be absent
    from both sides of that comparison, so it would be uncovered and invisible
    at the same time. Two direct raises are allowed and both are named above.
    """
    tree = ast.parse(SOURCE)
    direct = {
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Raise)
        and isinstance(node.exc, ast.Call)
        and isinstance(node.exc.func, ast.Name)
        and node.exc.func.id == ExtractionRefused.__name__
    }
    allowed = {
        raised.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
        and node.name in THE_DIRECT_RAISES_THAT_ARE_ALLOWED
        for raised in ast.walk(node)
        if isinstance(raised, ast.Raise)
    }
    assert direct <= allowed, (
        "these lines raise the refusal without going through the one function, "
        "so the coverage test above cannot see them: " + str(sorted(direct - allowed))
    )


def test_the_site_reader_reads_the_module_it_is_pointed_at() -> None:
    """A rename or a rewrite would leave the comparison reading an empty set."""
    assert refusal_sites(SOURCE), (
        f"{MODULE.name} names no refusal site, so the comparison above holds "
        "an empty set against an empty set"
    )
