"""What makes federation deliberate, and what would make it accidental.

``docs/decisions/0014-local-first-and-no-default-egress.md`` reserves one act
that puts rows on a wire, and ``src/plattenschrank/federate.py`` is it. Issue
#72 asks for three properties and this file refuses the absence of each.

## The column test

A column added to the measurement schema appears in the manifest with no change
to the federation code. That is the whole reason the manifest is read off the
rows rather than off a list, and the test below adds a column by declaring a
type that carries one, so nothing in the package is edited to make it pass.

## The confirmation tests, and what they reach

A test that greps for a configuration key nobody has added passes for exactly as
long as nobody adds one, so that is not what is written here. Four tests bite
instead, and each fails on the change rather than on the name.

The command's option surface is held to the three options it declares, so a
fourth reds the suite whatever it is called. The function's parameter list is
held the same way, so a configuration argument cannot arrive quietly. The one
configuration type this package has is set to its most permissive value and the
run is still a dry run. And the module is read for an environment lookup, which
is the configuration surface the other three do not reach.

WHAT NONE OF THEM REACHES is a key read from somewhere this file does not know
about: a file the module opens by a name assembled at run time, or a value
imported from another module and used as a switch. That is a floor rather than a
guarantee, and it is the same shape of floor the import check in
``tests/test_egress.py`` states about itself.

## What is sent, and where

The send tests reach a server started on this machine. Loopback is what the
block in ``tests/conftest.py`` allows, and decision 0014 is about what leaves
the host rather than about what is opened on it. That is also what makes "sends
nothing without the confirmation" a measurement rather than a restatement: the
server says whether it was ever reached, so an unconfirmed run is checked
against a connection that did not happen and not against the absence of an
exception.
"""

from __future__ import annotations

import argparse
import inspect
import io
import json
import socket
import threading
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, fields
from pathlib import Path

import pytest

from plattenschrank import cli
from plattenschrank import federate as federate_module
from plattenschrank.egress import Egress, EndpointUnreadable
from plattenschrank.federate import (
    CONFIRMATION,
    NOT_ASSESSED,
    PERSONAL_DATA,
    NoDestination,
    NothingToFederate,
    RowsUnreadable,
    federate,
    manifest_for,
    read_rows,
)
from plattenschrank.model import Measurement

pytestmark = pytest.mark.unit

# How long a test waits to be sure a connection did NOT happen. Long enough that
# a loopback connect would have arrived many times over, short enough that the
# tests which expect nothing do not dominate the run.
NOTHING_ARRIVES_WITHIN = 0.25

# One measurement row, built through the type rather than written as a literal,
# so a column renamed in the model reaches this file without anybody editing it.
A_MEASUREMENT = Measurement(
    detection_id="d-1",
    collection_id="hamburg",
    plate_id="p-1",
    scan_id="s-1",
    quantity="magnitude",
    value=12.5,
    unit="mag",
    calibration_id="c-1",
    software_version="0.0.0",
    model_id="none",
    uncertainty_measurement=0.02,
    uncertainty_calibration=None,
    uncertainty_transformation=None,
)


@dataclass(frozen=True)
class MeasurementCarryingAnObserverName(Measurement):
    """The measurement schema with one column added and nothing else changed.

    This is how the first test the issue asks for is made real without editing
    the package: the column exists on a row, the manifest is read off the row,
    and `src/plattenschrank/federate.py` has never heard of it.
    """

    observer_name: str = "H. Kaiser"


class Recorder:
    """A server on this machine that says whether it was reached, and with what.

    ``reached`` is set the moment a connection is accepted, which is what a test
    expecting nothing waits on. Waiting on the bytes instead would confuse a
    connection that carried nothing with one that never happened.
    """

    def __init__(self) -> None:
        self.received = b""
        self.reached = threading.Event()
        self.finished = threading.Event()

    def serve(self, server: socket.socket) -> None:
        try:
            connection, _ = server.accept()
        except OSError:
            # The listening socket timed out or was closed under the thread,
            # which is what happens when a test sent nothing.
            self.finished.set()
            return
        self.reached.set()
        with connection:
            while chunk := connection.recv(4096):
                self.received += chunk
        self.finished.set()

    def what_arrived(self) -> bytes:
        assert self.finished.wait(timeout=5), "the server never finished reading"
        return self.received

    def was_never_reached(self) -> bool:
        return not self.reached.wait(timeout=NOTHING_ARRIVES_WITHIN)


@pytest.fixture
def recorder() -> Iterator[tuple[str, Recorder]]:
    """A loopback endpoint and the recorder listening on it."""
    listening = Recorder()
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.bind(("127.0.0.1", 0))
        server.listen(1)
        server.settimeout(5)
        host, port = server.getsockname()
        thread = threading.Thread(target=listening.serve, args=(server,), daemon=True)
        thread.start()
        try:
            yield f"{host}:{port}", listening
        finally:
            release(host, port)
            thread.join(timeout=5)


def release(host: str, port: int) -> None:
    """Let the accepting thread return where a test connected to nothing."""
    try:
        with socket.create_connection((host, port), timeout=1):
            pass
    except OSError:
        pass


def run(
    destination: str,
    rows: tuple[Mapping[str, object], ...],
    confirmation: str | None = None,
) -> tuple[str, int]:
    """Federate, and return what was printed and how many rows were sent."""
    out = io.StringIO()
    outcome = federate(destination, rows, confirmation=confirmation, out=out)
    return out.getvalue(), outcome.rows_sent


def test_a_run_with_no_destination_is_refused() -> None:
    with pytest.raises(NoDestination):
        manifest_for("", (A_MEASUREMENT.to_row(),))


@pytest.mark.parametrize("destination", ["   ", "\t"], ids=["spaces", "tab"])
def test_a_blank_destination_is_refused_like_an_absent_one(destination: str) -> None:
    """The near miss, and the one a shell actually produces.

    An empty argument satisfies every check that asks whether a destination was
    given, and it names no host.
    """
    with pytest.raises(NoDestination):
        manifest_for(destination, (A_MEASUREMENT.to_row(),))


def test_a_destination_that_names_no_port_is_refused_before_the_manifest() -> None:
    """Refused while reading is still cheap, rather than after a confirmation.

    An operator who read a manifest and confirmed it has done the deliberate
    act. Finding out afterwards that the address could not be read leaves them
    unable to say whether anything went.
    """
    with pytest.raises(EndpointUnreadable):
        manifest_for("plates.example.org", (A_MEASUREMENT.to_row(),))


def test_a_run_with_no_rows_is_refused_rather_than_described() -> None:
    """An empty manifest reads exactly like a manifest over harmless columns."""
    with pytest.raises(NothingToFederate):
        manifest_for("127.0.0.1:9", ())


def test_the_manifest_names_every_column_the_rows_carry() -> None:
    row = A_MEASUREMENT.to_row()
    manifest = manifest_for("127.0.0.1:9", (row,))
    assert [column.name for column in manifest.columns] == list(row)
    assert manifest.rows == 1


def test_a_column_added_to_the_measurement_schema_appears_in_the_manifest() -> None:
    """The load-bearing test of this issue, and it edits no package file.

    The manifest is derived from the row rather than from a list, so a column
    the schema gained is a column the operator is shown. A list in
    `src/plattenschrank/federate.py` would pass every other test here and fail
    this one on the day it mattered.
    """
    row = MeasurementCarryingAnObserverName(
        detection_id="d-1",
        collection_id="hamburg",
        plate_id="p-1",
        scan_id="s-1",
        quantity="magnitude",
        value=12.5,
        unit="mag",
        calibration_id="c-1",
        software_version="0.0.0",
        model_id="none",
        uncertainty_measurement=None,
        uncertainty_calibration=None,
        uncertainty_transformation=None,
    ).to_row()
    manifest = manifest_for("127.0.0.1:9", (row,))
    named = {column.name: column for column in manifest.columns}
    assert "observer_name" in named
    assert named["observer_name"].personal_data == NOT_ASSESSED
    assert "observer_name" in manifest.render()


def test_a_column_nobody_assessed_is_not_reported_as_a_column_nobody_need_worry() -> (
    None
):
    """The direction that fails safely, which is the opposite of the cheap one.

    Reporting an unlisted column as carrying nothing would be a positive
    assurance derived from an absence, and the operator would have no way to see
    the difference on the page in front of them.
    """
    manifest = manifest_for("127.0.0.1:9", ({"a_column_nobody_listed": "text"},))
    assert manifest.columns[0].personal_data == NOT_ASSESSED
    assert "Not assessed" in manifest.render()


def test_every_measurement_column_carries_a_personal_data_entry() -> None:
    """The drift check the list needs, in the direction that hides a column."""
    declared = {field.name for field in fields(Measurement)}
    assert declared - set(PERSONAL_DATA) == set()


def test_no_personal_data_entry_names_a_column_the_schema_dropped() -> None:
    """The other direction, which is cover for a column nobody looked at.

    An entry for a column that no longer exists makes the list look complete
    while a real column goes unassessed, and the test above alone would pass.
    """
    declared = {field.name for field in fields(Measurement)}
    assert set(PERSONAL_DATA) - declared == set()


def test_the_counts_under_a_column_are_read_off_the_rows() -> None:
    """The measured half of the manifest, which is what the judgement is not."""
    rows: tuple[Mapping[str, object], ...] = (
        {"value": 1.0, "unit": "mag"},
        {"value": None, "unit": "mag"},
        {"value": 3.0},
    )
    counted = {
        column.name: column for column in manifest_for("127.0.0.1:9", rows).columns
    }
    assert counted["value"].numeric_values == 2
    assert counted["value"].absent_values == 1
    assert counted["unit"].text_values == 2
    assert counted["unit"].absent_values == 1


def test_a_boolean_is_not_counted_as_a_measured_number() -> None:
    """The one-character mistake, which is that a boolean is an integer here."""
    manifest = manifest_for("127.0.0.1:9", ({"value": True},))
    assert manifest.columns[0].numeric_values == 0
    assert manifest.columns[0].other_values == 1


def test_without_the_confirmation_the_destination_is_never_reached(
    recorder: tuple[str, Recorder],
) -> None:
    """Measured against a connection that did not happen."""
    destination, listening = recorder
    printed, sent = run(destination, (A_MEASUREMENT.to_row(),))
    assert sent == 0
    assert "Nothing was sent." in printed
    assert listening.was_never_reached()


@pytest.mark.parametrize(
    "confirmation",
    ["", "yes", "true", "1", "SEND", " send", "sending"],
    ids=["empty", "yes", "true", "one", "shouted", "padded", "longer"],
)
def test_a_confirmation_that_is_not_the_word_sends_nothing(
    confirmation: str, recorder: tuple[str, Recorder]
) -> None:
    """Compared exactly, because guessing at intent is how a default returns."""
    destination, listening = recorder
    _, sent = run(destination, (A_MEASUREMENT.to_row(),), confirmation)
    assert sent == 0
    assert listening.was_never_reached()


def test_with_the_confirmation_the_rows_arrive(
    recorder: tuple[str, Recorder],
) -> None:
    """A refusal that refused everything would pass every test above.

    It would also be wrong, and wrong invisibly until the first operator
    confirmed something.
    """
    destination, listening = recorder
    row = A_MEASUREMENT.to_row()
    printed, sent = run(destination, (row,), CONFIRMATION)
    assert sent == 1
    assert f"Sent 1 row(s) to {destination}." in printed
    arrived = [json.loads(line) for line in listening.what_arrived().decode().split()]
    assert arrived == [row]


def test_the_only_configuration_type_at_its_most_permissive_changes_nothing(
    recorder: tuple[str, Recorder],
) -> None:
    """Every purpose this package can be configured with, set and ignored.

    `Egress` is the whole configuration surface this package has, and this holds
    every field of it at the most permissive value it can take. A surface that
    grows is covered without this test being edited, because it enumerates the
    fields rather than naming them.
    """
    destination, listening = recorder
    permissive = Egress(**{field.name: destination for field in fields(Egress)})
    assert fields(Egress), "there is no configuration surface to be permissive on"
    assert all(getattr(permissive, field.name) for field in fields(Egress))
    _, sent = run(destination, (A_MEASUREMENT.to_row(),))
    assert sent == 0
    assert listening.was_never_reached()


def test_the_command_declares_no_option_beyond_the_three_it_needs() -> None:
    """What reds on the day somebody adds the option this issue is against.

    Naming a key that does not exist proves nothing. Holding the option set to
    what it is proves the next one has to be argued for, whatever it is called.
    """
    parser = cli.build_parser()
    groups = [
        action
        for action in parser._actions
        if isinstance(action, argparse._SubParsersAction)
    ]
    assert len(groups) == 1
    federating = groups[0].choices[cli.FEDERATE]
    declared = {
        option for action in federating._actions for option in action.option_strings
    }
    assert declared == {"-h", "--help", "--to", "--rows", "--confirm"}


def test_the_function_takes_no_configuration_argument() -> None:
    """The same property one level down, where a keyword could arrive quietly."""
    taken = list(inspect.signature(federate).parameters)
    assert taken == ["destination", "rows", "confirmation", "out"]


def test_the_module_reads_no_environment_variable() -> None:
    """The configuration surface the three tests above do not reach.

    An environment variable is a setting nobody has to write down, and it is the
    cheapest way for a confirmation to acquire a way around itself.
    """
    source = Path(federate_module.__file__).read_text(encoding="utf-8")
    assert "environ" not in source
    assert "getenv" not in source


def test_rows_are_read_from_a_file_of_one_object_per_line(tmp_path: Path) -> None:
    path = tmp_path / "rows.jsonl"
    row = A_MEASUREMENT.to_row()
    path.write_text(json.dumps(row) + "\n\n", encoding="utf-8")
    assert read_rows(path) == (row,)


def test_a_line_that_is_not_json_refuses_the_whole_file(tmp_path: Path) -> None:
    """A partial send is not what the manifest described."""
    path = tmp_path / "rows.jsonl"
    path.write_text('{"a": 1}\nnot json\n', encoding="utf-8")
    with pytest.raises(RowsUnreadable):
        read_rows(path)


def test_a_line_that_parses_to_something_other_than_an_object_is_refused(
    tmp_path: Path,
) -> None:
    path = tmp_path / "rows.jsonl"
    path.write_text('{"a": 1}\n[1, 2]\n', encoding="utf-8")
    with pytest.raises(RowsUnreadable):
        read_rows(path)


def test_a_file_that_is_not_there_is_a_refusal_rather_than_a_traceback(
    tmp_path: Path,
) -> None:
    with pytest.raises(RowsUnreadable):
        read_rows(tmp_path / "no-such-file.jsonl")


def test_the_command_refuses_without_a_destination(tmp_path: Path) -> None:
    """The command refuses this one before it reads anything."""
    path = tmp_path / "rows.jsonl"
    path.write_text(json.dumps(A_MEASUREMENT.to_row()) + "\n", encoding="utf-8")
    with pytest.raises(SystemExit) as exit_info:
        cli.main([cli.FEDERATE, "--rows", str(path)])
    assert exit_info.value.code == 2


def test_the_command_reports_a_refusal_as_a_refusal(tmp_path: Path) -> None:
    """Distinct from the code a stage that does not exist reports.

    A caller that could not tell them apart would read a refusal to federate as
    a feature nobody had written yet.
    """
    path = tmp_path / "rows.jsonl"
    path.write_text("", encoding="utf-8")
    exit_code = cli.main([cli.FEDERATE, "--to", "127.0.0.1:9", "--rows", str(path)])
    assert exit_code == cli.EXIT_REFUSED
    assert exit_code != cli.EXIT_NOT_IMPLEMENTED


def test_the_command_describes_and_sends_nothing_by_default(
    tmp_path: Path, recorder: tuple[str, Recorder], capsys: pytest.CaptureFixture[str]
) -> None:
    """The dry run is what happens, rather than a mode that has to be chosen."""
    destination, listening = recorder
    path = tmp_path / "rows.jsonl"
    path.write_text(json.dumps(A_MEASUREMENT.to_row()) + "\n", encoding="utf-8")
    assert cli.main([cli.FEDERATE, "--to", destination, "--rows", str(path)]) == 0
    assert "Nothing was sent." in capsys.readouterr().out
    assert listening.was_never_reached()


def test_the_command_sends_where_the_operator_confirmed(
    tmp_path: Path, recorder: tuple[str, Recorder], capsys: pytest.CaptureFixture[str]
) -> None:
    destination, listening = recorder
    row = A_MEASUREMENT.to_row()
    path = tmp_path / "rows.jsonl"
    path.write_text(json.dumps(row) + "\n", encoding="utf-8")
    argv = [
        cli.FEDERATE,
        "--to",
        destination,
        "--rows",
        str(path),
        "--confirm",
        CONFIRMATION,
    ]
    assert cli.main(argv) == 0
    assert "Sent 1 row(s)" in capsys.readouterr().out
    assert json.loads(listening.what_arrived().decode().strip()) == row


def test_the_manifest_says_which_half_of_it_is_a_judgement() -> None:
    """The sentence that stops the list being read as a measurement."""
    rendered = manifest_for("127.0.0.1:9", (A_MEASUREMENT.to_row(),)).render()
    assert "read off these rows" in rendered
    assert "docs/personal-data-inventory.md" in rendered
