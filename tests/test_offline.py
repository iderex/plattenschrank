"""What the gated suite owes a machine that is not allowed to talk to anything.

`docs/decisions/0014-local-first-and-no-default-egress.md` says nothing leaves
the host by default. `tests/conftest.py` is the refusal that makes it more than
a sentence, and this file is what refuses the absence of that refusal.

Four properties, proved separately, because they fail separately.

The block is installed. Deleting the call in `tests/conftest.py` reds the first
test here, and it reds by the exception type rather than by a comparison.

The block is what refused, rather than a network that was not there. This is the
near miss the whole file is aimed at. A suite run on a machine with no route out
refuses a connection whether or not anything here is installed, and the two
results look identical from a distance. `OutboundConnectionRefused` is its own
type and no operating system raises it, so a test asserting on that type is
asserting on this repository rather than on the runner it happened to run on.

The block is not refusing everything. A guard that refuses every connection
passes the two tests above and would also break a loopback server somebody adds
later, and it would be indistinguishable from a correct one until they did. A
real loopback connection is made here and is expected to succeed.

The line that says so is printed. A run that is offline and does not say it is
offline gets read as a run that happened to have no network.

WHAT IS NOT PROVED HERE, and the sentence is negative and stays negative. That
the block would have stopped a connection which would otherwise have succeeded
cannot be shown from inside a suite that is forbidden to make one. It is shown
by two branches instead, one where a gated test reaches a real host and the job
reds, and one where the same test runs with the block deleted and the job
greens. Neither is merged and both are linked from the pull request for #24.
"""

from __future__ import annotations

import ipaddress
import socket
import threading
from pathlib import Path

import pytest

from conftest import (
    LOOPBACK_HOSTS,
    REFUSAL,
    OutboundConnectionRefused,
    leaves_this_host,
)

pytestmark = pytest.mark.unit

# The file the block lives in, read rather than re-created, so a run under
# `pytester` is a run of the guard this repository ships and not of a copy that
# drifted from it.
GUARD = Path(__file__).resolve().parent / "conftest.py"

# A host that is not this machine. It is never connected to: every test below
# expects the attempt to be refused before a packet exists, so the name is a
# string this suite reads and not an address it reaches.
SOMEWHERE_ELSE = ("example.org", 443)


def test_a_connection_off_this_host_is_refused() -> None:
    """The guard. Deleting the install call in `tests/conftest.py` reds this."""
    with pytest.raises(OutboundConnectionRefused) as refused:
        socket.create_connection(SOMEWHERE_ELSE, timeout=1)
    assert "example.org" in str(refused.value)


def test_the_socket_method_underneath_is_refused_as_well() -> None:
    """`create_connection` is a convenience, and the method is the layer.

    A client library that builds its own socket and calls `connect` never
    touches `create_connection`, so a block on the convenience alone would let
    through most of the libraries anybody would actually reach an archive with.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        with pytest.raises(OutboundConnectionRefused):
            sock.connect(("192.0.2.1", 443))
        with pytest.raises(OutboundConnectionRefused):
            sock.connect_ex(("192.0.2.1", 443))


def test_the_refusal_is_not_something_an_operating_system_can_raise() -> None:
    """The near miss, and the reason this file exists rather than a bare assert.

    A machine with no route out raises `OSError` from the same call. If this
    suite asserted that connecting fails, it would pass identically on a runner
    with no network and with every line of the block deleted, and the guard
    would be absent and invisible. `OutboundConnectionRefused` is declared in
    `tests/conftest.py` and nothing else raises it.
    """
    assert issubclass(OutboundConnectionRefused, RuntimeError)
    assert not issubclass(OutboundConnectionRefused, OSError)


def test_loopback_is_not_refused() -> None:
    """A block that refused everything would pass every test above.

    It would also be wrong. Decision 0014 is about what leaves the host, and a
    connection to this machine leaves nothing. This makes a real one, to a
    server started here, and expects it to work.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.bind(("127.0.0.1", 0))
        server.listen(1)
        accepted: list[socket.socket] = []
        listener = threading.Thread(
            target=lambda: accepted.append(server.accept()[0]), daemon=True
        )
        listener.start()
        with socket.create_connection(server.getsockname(), timeout=5) as client:
            client.sendall(b"loopback")
        listener.join(timeout=5)
    assert accepted, "the loopback server accepted nothing"
    with accepted[0] as served:
        assert served.recv(8) == b"loopback"


def test_a_routable_family_is_what_the_block_reads() -> None:
    """The bound is read off the family rather than guessed from the address."""
    assert leaves_this_host(socket.AF_INET, SOMEWHERE_ELSE)
    assert leaves_this_host(socket.AF_INET6, ("2001:db8::1", 443, 0, 0))


def test_a_unix_domain_socket_is_not_treated_as_routable() -> None:
    """A socket that carries a path and no host cannot leave the machine.

    `AF_UNIX` is absent from the standard library on Windows, so this is one of
    the two platforms this suite runs on rather than both, and the skip says so
    rather than the test quietly proving nothing there.
    """
    unix = getattr(socket, "AF_UNIX", None)
    if unix is None:
        pytest.skip("AF_UNIX is not a family on this platform")
    assert not leaves_this_host(unix, "/tmp/somewhere.sock")


def test_an_address_shape_nothing_can_read_is_refused_rather_than_allowed() -> None:
    """Fail closed on the case nobody anticipated, which is the whole class."""
    assert leaves_this_host(socket.AF_INET, None)
    assert leaves_this_host(socket.AF_INET, ())


def test_every_loopback_host_the_block_names_is_one() -> None:
    """The allowance is a list, and a list is where a wrong entry hides.

    Each name here is resolved and every address it resolves to has to be a
    loopback address. An entry that resolved to something routable would be a
    hole in the block that reads as a documented exception.
    """
    for host in LOOPBACK_HOSTS:
        resolved = socket.getaddrinfo(host, None)
        assert resolved, f"{host} resolved to nothing"
        for family, _, _, _, address in resolved:
            assert ipaddress.ip_address(address[0]).is_loopback, (
                f"{host} resolves to {address[0]}, which is not loopback"
            )
            assert family in {socket.AF_INET, socket.AF_INET6}


def test_the_run_says_it_is_offline_before_it_says_anything_else(
    pytester: pytest.Pytester,
) -> None:
    """The disclosure, proved by reading a run rather than by reading the source.

    A green suite that reached no archive and a green suite that was forbidden
    to are different results, and only one of them is evidence about the
    software. The line is what tells them apart in a log somebody reads months
    later.
    """
    pytester.makeconftest(GUARD.read_text(encoding="utf-8"))
    pytester.makeini(
        "[pytest]\nrequirement_markers = unit\nmarkers =\n    unit: runs anywhere\n"
    )
    pytester.makepyfile(
        "import pytest\n\n@pytest.mark.unit\ndef test_nothing():\n    pass\n"
    )
    result = pytester.runpytest_subprocess()
    result.assert_outcomes(passed=1)
    result.stdout.fnmatch_lines([f"*{REFUSAL}*"])


def test_installing_the_block_twice_leaves_one_wrapper(
    pytester: pytest.Pytester,
) -> None:
    """The failure this found, kept so it cannot come back quietly.

    This file's own source runs under `pytester` in this same process, which
    imports `conftest` a second time as a different module. A second install
    would wrap the first, and the exception the outer wrapper raises would
    belong to that second module rather than to the one this file imported
    `OutboundConnectionRefused` from, so the two tests at the top would red
    while passing when run alone. Running a copy and then asking the original
    for a refusal is what catches it.
    """
    pytester.makeconftest(GUARD.read_text(encoding="utf-8"))
    pytester.makeini(
        "[pytest]\nrequirement_markers = unit\nmarkers =\n    unit: runs anywhere\n"
    )
    pytester.makepyfile(
        "import pytest\n\n@pytest.mark.unit\ndef test_nothing():\n    pass\n"
    )
    pytester.runpytest().assert_outcomes(passed=1)

    with pytest.raises(OutboundConnectionRefused):
        socket.create_connection(SOMEWHERE_ELSE, timeout=1)
