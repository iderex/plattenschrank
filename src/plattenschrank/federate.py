"""Federation, which is the one act that puts measurement rows on a wire.

``docs/decisions/0014-local-first-and-no-default-egress.md`` says nothing leaves
this host unless an operator asked for it. Sharing results is the point of the
work, so the position is not that data never leaves. It is that leaving is
something an operator does knowingly, and this module exists to make the knowing
part unavoidable rather than merely documented.

Three refusals, and each fails on its own.

A run with no destination is refused before anything is read. A blank one is
refused with it, for the reason ``model.py`` gives about blanks: a key present
with nothing after it satisfies every check that asks whether a setting exists
and names no host.

A run with no rows is refused rather than described. A manifest over an empty
set lists no column and reads exactly like a manifest over a schema that carries
nothing personal, and those are opposite statements.

Nothing is sent without the confirmation, and the confirmation is an argument
rather than a setting. This module holds no configuration object and reads none,
so there is no key to turn the confirmation off. What keeps that true is not
this sentence: ``tests/test_federate.py`` holds the command's whole option
surface to the set it declares today, so an option added later reds that test
and has to argue for itself in the pull request that adds it.

## The manifest is read off the rows

Its columns are the keys the rows actually carry, in the order they carry them,
and its counts are what sits under each key. A column added to the measurement
schema therefore appears in the manifest without a line changing here. A list of
columns written into this file would drift against the schema, and the drift
would stay invisible until the run that sent a column nobody had looked at.

## The one part that is a list, and what keeps it honest

Whether a column can carry personal data is a judgement about meaning, and no
reading of the rows makes it. ``PERSONAL_DATA`` is that judgement, one entry per
column, each of them sourced from ``docs/personal-data-inventory.md``. It is a
list and it will drift, so two things hold it.

A column with no entry is reported as not assessed rather than as carrying
nothing. That is the direction that fails safely for the operator reading the
manifest, because a silent column and a column somebody cleared are otherwise
the same line.

And ``tests/test_federate.py`` refuses a measurement column that has no entry
here, and an entry here that names no measurement column, so the drift is caught
in the suite rather than in a manifest somebody skims at the end of a long day.

## What this does not decide

The carrier. ``docs/decisions/0003-data-model.md`` names Parquet as the bulk
output and no library in the locked graph reads or writes it, so there is no
catalogue file for this to federate yet. What it reads and what it sends is one
JSON object per line, which is the smallest thing that carries exactly the rows
the manifest describes and lets the command be exercised end to end today. No
record on this board decides a federation protocol, and this module does not
become that record by having to send something.

## What this does not refuse

A destination the operator typed wrongly. An endpoint is a host and a port, and
nothing here knows which host was meant, so an operator who reads a manifest and
confirms it against the wrong address has sent it.

Anything that leaves by another route. The manifest describes the rows this
function was handed and says nothing about a stage that opens its own
connection. What holds that is the import check in ``tests/test_egress.py``,
which refuses a second module naming a library that reaches the network, rather
than anything written here.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final, TextIO

from plattenschrank.egress import Egress, connect, split_endpoint

# The purpose ``egress.py`` declares for this, and the only one this module
# reaches for. It is a name rather than an endpoint: the endpoint is what the
# operator types, and it is absent until they do.
FEDERATION: Final = "federation"

# The word that turns a dry run into a send. Compared exactly, and deliberately
# not parsed for intent. An operator who typed something else has not confirmed,
# and guessing at what they meant is the failure this constant is against.
CONFIRMATION: Final = "send"

NOT_ASSESSED: Final = (
    "Not assessed. No entry in docs/personal-data-inventory.md names this "
    "column, so nothing here says it is free of personal data."
)

_AN_ARCHIVE_IDENTIFIER: Final = (
    "An identifier rather than a name, and also the join key that takes this "
    "row back to a plate whose envelope carries names, which is entry 1 of "
    "docs/personal-data-inventory.md."
)

_A_PROVENANCE_FIELD: Final = (
    "A provenance field, and entry 6 of docs/personal-data-inventory.md names "
    "a provenance field as a place a name reaches."
)

_A_MEASURED_NUMBER: Final = (
    "A number this software computed. No entry in "
    "docs/personal-data-inventory.md puts personal data here, and that is a "
    "statement about this column rather than about the row it sits in."
)

_WHAT_WAS_MEASURED: Final = (
    "Text this software wrote, naming what was measured and in what unit, "
    "rather than anything read off a plate."
)

# One entry per column of ``model.Measurement``, and no entry for anything else.
# Both directions are held by the suite, because an entry for a column that no
# longer exists reads as cover for a column that does.
PERSONAL_DATA: Final[Mapping[str, str]] = {
    "detection_id": _AN_ARCHIVE_IDENTIFIER,
    "collection_id": _AN_ARCHIVE_IDENTIFIER,
    "plate_id": _AN_ARCHIVE_IDENTIFIER,
    "scan_id": _AN_ARCHIVE_IDENTIFIER,
    "quantity": _WHAT_WAS_MEASURED,
    "unit": _WHAT_WAS_MEASURED,
    "value": _A_MEASURED_NUMBER,
    "uncertainty_measurement": _A_MEASURED_NUMBER,
    "uncertainty_calibration": _A_MEASURED_NUMBER,
    "uncertainty_transformation": _A_MEASURED_NUMBER,
    "calibration_id": _A_PROVENANCE_FIELD,
    "software_version": _A_PROVENANCE_FIELD,
    "model_id": _A_PROVENANCE_FIELD,
    "schema_version": _A_PROVENANCE_FIELD,
}


class FederationRefused(RuntimeError):
    """Raised where this software declined to federate.

    Its own type rather than a bare ``RuntimeError``, for the reason
    ``egress.py`` gives: a refusal by this software and a failure of somebody
    else's machine are opposite statements and must not be catchable by one
    handler.
    """


class NoDestination(FederationRefused):
    """Raised where nothing said where the rows were to go."""


class NothingToFederate(FederationRefused):
    """Raised where there are no rows, so there is nothing to describe."""


class RowsUnreadable(FederationRefused):
    """Raised where the rows could not be read, apart from there being none.

    Apart from ``NothingToFederate`` because the two say opposite things about
    the operator's file. One says it held nothing; the other says it held
    something this could not read, and reading the second as the first would
    federate a shorter set than the operator believes they confirmed.
    """


@dataclass(frozen=True)
class Column:
    """One column of the manifest: what the rows hold, and what it may be.

    The four counts are measured off the rows. ``personal_data`` is not: it is
    the judgement from ``docs/personal-data-inventory.md``, and it sits beside
    the counts rather than instead of them because the two catch different
    mistakes.
    """

    name: str
    text_values: int
    numeric_values: int
    absent_values: int
    other_values: int
    personal_data: str


@dataclass(frozen=True)
class Manifest:
    """Every field that would be sent, how many rows, and what each may carry."""

    destination: str
    rows: int
    columns: tuple[Column, ...]

    def render(self) -> str:
        """The manifest as the text an operator reads before confirming."""
        lines = [
            f"federating to {self.destination}",
            f"{self.rows} row(s) across {len(self.columns)} column(s).",
            "",
        ]
        for column in self.columns:
            counted = (
                f"{column.text_values} text, "
                f"{column.numeric_values} numeric, "
                f"{column.absent_values} absent"
            )
            if column.other_values:
                counted += f", {column.other_values} of some other type"
            lines.append(f"  {column.name}: {counted}")
            lines.append(f"      {column.personal_data}")
        lines.append("")
        lines.append(
            "The counts above are read off these rows. The sentence under each "
            "column is a judgement taken from docs/personal-data-inventory.md "
            "and is not a reading of the data."
        )
        return "\n".join(lines)


@dataclass(frozen=True)
class Outcome:
    """What a federation run did, so a caller does not infer it from output."""

    manifest: Manifest
    rows_sent: int


def manifest_for(destination: str, rows: Sequence[Mapping[str, object]]) -> Manifest:
    """The manifest for these rows, or a refusal.

    The destination is checked here rather than at the moment of sending, so an
    operator does not read a manifest and confirm it before finding out that the
    address it names cannot be read.
    """
    if not destination.strip():
        raise NoDestination(
            "no destination was given, so there is nowhere for these rows to "
            "go. Federation names its destination every time, because a "
            "destination that can be omitted is one a run can acquire by "
            "default. docs/decisions/0014-local-first-and-no-default-egress.md "
            "is where that is decided."
        )
    if not rows:
        raise NothingToFederate(
            "there are no rows here, so there is nothing to describe and "
            "nothing to send. A manifest over an empty set lists no column and "
            "reads exactly like a manifest over a schema that carries nothing "
            "personal, which is the misreading this refusal is against."
        )
    endpoint = _readable_endpoint(destination.strip())
    names: list[str] = []
    for row in rows:
        for name in row:
            if name not in names:
                names.append(name)
    return Manifest(
        destination=endpoint,
        rows=len(rows),
        columns=tuple(_column(name, rows) for name in names),
    )


def federate(
    destination: str,
    rows: Sequence[Mapping[str, object]],
    *,
    confirmation: str | None,
    out: TextIO,
) -> Outcome:
    """Print the manifest, and send only where the confirmation is exact.

    The dry run is not a mode that has to be selected. It is what happens, and
    the send is the departure from it.
    """
    manifest = manifest_for(destination, rows)
    print(manifest.render(), file=out)
    if confirmation != CONFIRMATION:
        print("", file=out)
        print(
            f"Nothing was sent. Sending is the departure from this, and it "
            f"needs the confirmation {CONFIRMATION!r} exactly, which no "
            f"setting supplies and no setting suppresses.",
            file=out,
        )
        return Outcome(manifest=manifest, rows_sent=0)
    sent = _send(manifest.destination, rows)
    print("", file=out)
    print(f"Sent {sent} row(s) to {manifest.destination}.", file=out)
    return Outcome(manifest=manifest, rows_sent=sent)


def read_rows(path: Path) -> tuple[Mapping[str, object], ...]:
    """Read rows from a file holding one JSON object per line.

    Blank lines are skipped and anything else that is not an object is refused,
    because a file half of which parsed is not a shorter catalogue.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as failure:
        raise RowsUnreadable(
            f"{path} could not be read, so there is nothing to federate: {failure}"
        ) from failure
    rows: list[Mapping[str, object]] = []
    for number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError as failure:
            raise RowsUnreadable(
                f"{path} line {number} is not one JSON object: {failure}. The "
                "whole file is refused rather than the rows before it sent, "
                "because a partial send is not what the manifest described."
            ) from failure
        if not isinstance(parsed, dict) or not all(
            isinstance(key, str) for key in parsed
        ):
            raise RowsUnreadable(
                f"{path} line {number} parsed to something that is not an "
                "object with string keys, and a row is an object with string "
                "keys."
            )
        rows.append({str(key): value for key, value in parsed.items()})
    return tuple(rows)


def _readable_endpoint(destination: str) -> str:
    """The destination, having been read as a host and a port by ``egress``.

    The reading is delegated rather than repeated, so a destination this accepts
    and a destination the connection accepts cannot come apart.
    """
    split_endpoint(destination)
    return destination


def _column(name: str, rows: Sequence[Mapping[str, object]]) -> Column:
    """One column, counted over every row rather than over the first one."""
    text = numeric = absent = other = 0
    for row in rows:
        value = row.get(name)
        if name not in row or value is None:
            absent += 1
        elif isinstance(value, str):
            text += 1
        elif isinstance(value, bool):
            # Before the numeric case, because a boolean is an integer to
            # ``isinstance`` and is not a measured number.
            other += 1
        elif isinstance(value, int | float):
            numeric += 1
        else:
            other += 1
    return Column(
        name=name,
        text_values=text,
        numeric_values=numeric,
        absent_values=absent,
        other_values=other,
        personal_data=PERSONAL_DATA.get(name, NOT_ASSESSED),
    )


def _send(destination: str, rows: Sequence[Mapping[str, object]]) -> int:
    """Write the rows to the destination, one JSON object per line."""
    payload = b"".join(
        (json.dumps(dict(row), separators=(",", ":")) + "\n").encode("utf-8")
        for row in rows
    )
    with connect(FEDERATION, Egress(federation=destination)) as connection:
        connection.sendall(payload)
    return len(rows)
