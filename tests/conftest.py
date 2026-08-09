"""The collection hook that refuses a test whose requirements nobody stated.

The marker scheme is in ``pyproject.toml`` under ``[tool.pytest.ini_options]``:
four markers, one line of meaning each, and ``-m unit`` as the default
selection. This file is the half of the scheme that refuses rather than
describes.

The rule is one sentence. Every collected test carries at least one of the
markers the scheme names, and collection fails naming the ones that do not.

It also carries the disclosure that goes with the selection. Every run prints,
before it reports a result, which of the four sets it reached and which it left
out with what running those would need. A green run of the gated set says
nothing about the network-bound or hardware-bound halves, and that line is what
stops it being read as though it did.

That single rule covers both shapes of the mistake. A test with no marker at all
is the obvious one. The one worth aiming at is a test whose marker is
misspelled, because ``@pytest.mark.unti`` reads as ``unit`` in review and is not
one, so the test states no requirement and, without this hook, quietly leaves
the default selection while looking like it is inside it.

``--strict-markers`` would also refuse the misspelling, and it is deliberately
not set. Two mechanisms answering for one property make a red fixture unable to
say which of them refused, and the proof this board asks for is that deleting
the guard reds the suite. There is one guard here, and
``tests/test_marker_scheme.py`` runs the source of this file against fixtures
that trip it.

The scheme is read from its own ``requirement_markers`` setting rather than from
pytest's ``markers`` list, because that list also carries pytest's own built-in
markers and there would then be no way to say which four the scheme is. Two of
those built-ins, ``tryfirst`` and ``trylast``, are bare names that survive the
parse intact, so a guard reading the scheme out of that list accepts a test
carrying one of them and nothing else. The rest arrive with their argument
lists attached and are refused for the accidental reason that their names do
not parse to a bare word, which is not a property to rely on.

The hook runs ``tryfirst`` because pytest's own ``-m`` filtering deselects in
this same hook. Running after it would mean an unmarked test had already been
deselected by the default selection and there would be nothing left to refuse,
which is the failure this ordering exists to prevent and which
``test_the_hook_sees_a_test_the_default_selection_would_have_deselected``
demonstrates.
"""

from __future__ import annotations

import os
import socket
from typing import Any, NoReturn

import pytest

pytest_plugins = ["pytester"]

SCHEME = "requirement_markers"

# The non-interactive plotting backend, selected here and not in an environment
# variable a contributor sets on their own machine. A guard that depends on
# somebody remembering is not a guard, and the failure it prevents is a plotting
# call selecting a window toolkit on the first machine that has one, which turns
# a green suite into one that hangs waiting for a window nobody will close.
#
# This line is the forcing and `tests/test_headless.py` is what refuses its
# absence. The bound on both is stated there: no plotting library is in the
# locked graph yet, so what is proved is the selection this suite makes and not
# a backend observed in force.
NON_INTERACTIVE_BACKEND = "Agg"
os.environ["MPLBACKEND"] = NON_INTERACTIVE_BACKEND

# The refusal of anything that would leave this host, installed in this process
# at import time rather than around it.
#
# `docs/decisions/0014-local-first-and-no-default-egress.md` is the position and
# this is what refuses a departure from it. It is here rather than in a firewall
# rule on the runner for one reason: a block that lives in the runner
# configuration is a block a contributor does not get, so it would hold in the
# one place nothing needs it and be absent in the place the software is meant to
# run. Patching the standard library travels with the repository.
#
# It also separates two failures that otherwise look the same. An archive that
# is down and a test that reached for an archive it should not have reached for
# both appear as a red suite, and after this only the second one can happen in
# the gated set.

REFUSAL = "outbound connections are refused in this suite"

# The address families that can carry a packet off this machine. A unix domain
# socket cannot, and neither can the families the operating system uses to talk
# to itself, so the block reads the family rather than guessing from the address.
ROUTABLE_FAMILIES = frozenset({socket.AF_INET, socket.AF_INET6})

# Loopback is not outbound, and refusing it would be a different rule than the
# one decision 0014 states. `socket.socketpair` is built on a loopback
# connection on Windows, so a block that refused this would refuse a piece of
# the standard library on one of the two platforms this suite runs on.
LOOPBACK_HOSTS = frozenset({"127.0.0.1", "::1", "localhost"})


class OutboundConnectionRefused(RuntimeError):
    """Raised where a gated test reached for something off this machine.

    Its own type rather than `OSError`, because a test that catches `OSError`
    around a connection would swallow this and report that the host was
    unreachable. The two are opposite statements about the suite and must not be
    catchable by the same handler.
    """


def leaves_this_host(family: int, address: object) -> bool:
    """Whether connecting to this address would put a packet on a wire."""
    if family not in ROUTABLE_FAMILIES:
        return False
    if not isinstance(address, tuple) or not address:
        # A routable family with an address shape nothing here can read. Refused
        # rather than allowed, because the alternative fails open on exactly the
        # case nobody anticipated.
        return True
    host = address[0]
    return not (isinstance(host, str) and host in LOOPBACK_HOSTS)


def _refuse(wanted: object) -> NoReturn:
    raise OutboundConnectionRefused(
        f"{REFUSAL}, and this one wanted {wanted!r}. A test that needs an "
        "archive carries the integration_network marker and runs in the harness "
        "named for it, never in the gated set."
    )


# The mark an installed wrapper carries, and the reason it has to.
#
# `tests/test_marker_scheme.py` and `tests/test_offline.py` run this file's own
# source under `pytester`, which imports it a second time as a different module
# in this same process. Without this mark that second import wraps the first
# wrapper, and the exception the outer one raises belongs to the copy rather than
# to the module a test imported `OutboundConnectionRefused` from, so
# `pytest.raises` stops matching and the guard tests red for a reason that has
# nothing to do with the guard. Measured rather than reasoned about: the two
# tests in `tests/test_offline.py` that expect the refusal passed alone and
# failed in the full suite before this existed.
INSTALLED = "refuses_outbound_connections"


def _install_outbound_block() -> None:
    """Refuse at the socket layer, which is the layer nothing gets under.

    `socket.create_connection` is patched as well as the two methods, and not
    because it could get past them. It is patched because it is called with the
    host as somebody wrote it, and the methods are called with whatever name
    resolution returned, so the message a reader sees names `example.org` rather
    than an address they then have to look up.

    Installing twice is a no-op rather than a second wrapper, for the reason
    written above the mark.
    """
    if getattr(socket.socket.connect, INSTALLED, False):
        return

    connect = socket.socket.connect
    connect_ex = socket.socket.connect_ex
    create_connection = socket.create_connection

    def guarded_connect(self: socket.socket, address: Any) -> None:
        if leaves_this_host(self.family, address):
            _refuse(address)
        connect(self, address)

    def guarded_connect_ex(self: socket.socket, address: Any) -> int:
        if leaves_this_host(self.family, address):
            _refuse(address)
        return connect_ex(self, address)

    def guarded_create_connection(address: Any, *args: Any, **kwargs: Any) -> Any:
        if leaves_this_host(socket.AF_INET, address):
            _refuse(address)
        return create_connection(address, *args, **kwargs)

    for wrapper in (guarded_connect, guarded_connect_ex, guarded_create_connection):
        setattr(wrapper, INSTALLED, True)

    socket.socket.connect = guarded_connect  # type: ignore[method-assign]
    socket.socket.connect_ex = guarded_connect_ex  # type: ignore[method-assign]
    socket.create_connection = guarded_create_connection  # type: ignore[assignment]


_install_outbound_block()

# WHAT THIS DOES NOT REFUSE, and the sentence is negative and stays negative.
# Name resolution is not blocked, so a test that calls `socket.getaddrinfo` and
# never connects puts a query on the wire and passes. Nor is a raw socket sending
# with `sendto`, and nor is a subprocess: `tests/test_cli.py` starts interpreters
# of its own and this block does not reach into them. What is refused is a
# connection attempted from this process, which is the shape every client library
# in the locked graph uses.


def pytest_report_header() -> str:
    """Say the block is in force before the first result, not after the last."""
    return f"{REFUSAL}, except to {', '.join(sorted(LOOPBACK_HOSTS))}"


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addini(
        SCHEME,
        "the markers a test states its requirements with, one of which every "
        "test carries",
        type="args",
        default=[],
    )


def requirement_markers(config: pytest.Config) -> frozenset[str]:
    """The marker names the scheme declares, read from the configuration."""
    return frozenset(config.getini(SCHEME))


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    declared = requirement_markers(config)
    if not declared:
        # Fail closed. An empty scheme would make the loop below accept every
        # test, so the guard would report nothing and read exactly like a guard
        # that found nothing wrong.
        raise pytest.UsageError(
            f"the {SCHEME} setting names no marker, so nothing here states a "
            "requirement and this hook would accept every test. It belongs in "
            "pyproject.toml under [tool.pytest.ini_options]."
        )
    unstated = [
        item.nodeid
        for item in items
        if not declared & {mark.name for mark in item.iter_markers()}
    ]
    if not unstated:
        return
    raise pytest.UsageError(
        "every test states its requirements with one of the markers "
        f"{', '.join(sorted(declared))}. These state none, either by carrying no "
        "marker or by carrying one the scheme does not name: " + ", ".join(unstated)
    )


DISCLOSURE = "requirement markers:"


def marker_meanings(config: pytest.Config) -> dict[str, str]:
    """What each registered marker says it needs, read from its registration.

    The sentence after the colon in the ``markers`` list is the cost of running
    that set. It is read here rather than restated, because a second copy in a
    workflow file or in this function would drift against the registration and
    the drift would be invisible until somebody compared them by hand.
    """
    meanings = {}
    for line in config.getini("markers"):
        name, _, meaning = str(line).partition(":")
        meanings[name.strip()] = meaning.strip()
    return meanings


def disclosure(config: pytest.Config, covered: frozenset[str]) -> str:
    """The one line that says what this selection reached and what it left."""
    declared = requirement_markers(config)
    meanings = marker_meanings(config)
    left = sorted(declared - covered)
    reached = ", ".join(sorted(covered)) or "no marker set"
    if not left:
        return f"{DISCLOSURE} this run covered {reached} and left no set out."
    costs = ", ".join(
        f"{name} ({meanings.get(name, 'no meaning registered')})" for name in left
    )
    return f"{DISCLOSURE} this run covered {reached}. It did not run {costs}."


def pytest_collection_finish(session: pytest.Session) -> None:
    """Say what the selection left out, before any test result is printed.

    A green run of the gated set is a statement about one of four marker sets,
    and a reader who does not know that reads it as a statement about the
    software. The network-bound and hardware-bound halves have their own harness
    in ``.github/workflows/integration.yml``, named for what each one needs, and
    this line is what stops a green ``build`` from standing in for them.

    What it measures is which of the scheme's markers the tests that survived
    selection actually carry, rather than what the marker expression asked for.
    Those differ where the expression names a set no test carries yet, and the
    honest report of that case is that the run covered nothing of it, which is
    what this produces.
    """
    reporter = session.config.pluginmanager.get_plugin("terminalreporter")
    if reporter is None:
        # Nothing to print to, under `-p no:terminal`. The suite still runs and
        # this line is a disclosure rather than a guard, so its absence here
        # removes a statement rather than a refusal.
        return
    declared = requirement_markers(session.config)
    covered = (
        frozenset(mark.name for item in session.items for mark in item.iter_markers())
        & declared
    )
    reporter.write_line(disclosure(session.config, covered))
