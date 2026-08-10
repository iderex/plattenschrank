"""What refuses a default egress, and what refuses a second way out.

``docs/decisions/0014-local-first-and-no-default-egress.md`` says nothing leaves
the host unless an operator configured an endpoint for that purpose.
``src/plattenschrank/egress.py`` is the registry and the one function that opens
a connection, and this file is what refuses the absence of both.

Two of the three checks issue #71 asks for are here. The third, that no
diagnostic carries a value read off a page, is
``tests/test_no_transcribed_value_escapes.py``, because it fails for a different
reason and a reader chasing one should not have to read the other.

## The default configuration

``Egress`` declares one purpose, ``federation``, and its default is correct, so
the enumeration below reads a field and still reports an empty answer. That is
the honest state of the tree and it is also the shape of a check that proves
nothing, because a reader that reported nothing whatever it was given would
answer identically. So it is not left standing alone. Three registries declared
in this file carry a default endpoint, a purpose that cannot be left unset, and
a purpose declared correctly, and the same enumeration is run over each. Those
three are what show it reads a default at all.

## The one way out

The import check reads what a source file names rather than what it calls. That
is a floor and the bound is worth stating: a library reached through
``importlib`` under a name assembled at run time is not named in an import
statement and is not caught here. What it does catch is the shape somebody
actually writes, which is an adapter that imports a client library at the top of
the file, in either spelling.

It is also aimed at a near miss rather than at the obvious case. A grep for the
word would match a comment and an aliased import would slip a plain string
search, so the modules are read out of the parse tree and the alias is
irrelevant to it. ``a_source_that_reaches_the_network`` is the fixture that shows
the reader catches the from-import spelling, which is the one an adapter is most
likely to be written with.
"""

from __future__ import annotations

import ast
import socket
import threading
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from plattenschrank.egress import (
    NOTHING_CONFIGURED,
    Egress,
    EgressNotConfigured,
    EndpointUnreadable,
    connect,
    declared_purposes,
    defaulted_endpoints,
    endpoint_for,
    split_endpoint,
)

pytestmark = pytest.mark.unit

PACKAGE = Path(__file__).resolve().parent.parent / "src" / "plattenschrank"

# The module that is allowed to name a network library, as the import check
# reads its name. Everything else in the package is refused one.
THE_ONE_WAY_OUT = "egress.py"

# The libraries a stage would reach an archive with, by the root name an import
# statement carries. It is a floor rather than a complete list of everything that
# can open a socket, and each entry is here because it is what somebody would
# actually write: the three standard library clients an archive service is
# reached with, the transport underneath them, the mail and file protocols that
# have no business in this package at all, and the three third-party clients that
# would arrive with an adapter.
#
# `asyncio` is deliberately absent. It reaches the network and it is also how a
# process supervises a subprocess or a timer, so refusing it here would refuse
# work that leaves nothing, and a check that refuses the innocent case is a check
# somebody switches off.
REACHES_THE_NETWORK = frozenset(
    {
        "socket",
        "ssl",
        "http",
        "urllib",
        "ftplib",
        "smtplib",
        "poplib",
        "imaplib",
        "telnetlib",
        "xmlrpc",
        "webbrowser",
        "requests",
        "httpx",
        "urllib3",
        "aiohttp",
    }
)

# The spelling the reader has to catch and a plain string search would not: the
# module is named in a `from` clause and the symbol it imports says nothing about
# where it came from.
A_SOURCE_THAT_REACHES_THE_NETWORK = (
    "from urllib.request import urlopen\n\n\ndef fetch(url):\n    return urlopen(url)\n"
)


@dataclass(frozen=True)
class ARegistryCarryingADefault(Egress):
    """A purpose whose endpoint is set for an operator who never asked."""

    archive_index: str | None = "plates.example.org:443"


@dataclass(frozen=True)
class ARegistryDemandingOne(Egress):
    """A purpose with no default at all, so there is no empty configuration.

    ``kw_only`` is here for the language rather than for the property. A field
    without a default cannot follow one that has a default, and the registry
    this inherits from now declares a purpose, so the declaration is illegal
    positionally and legal as a keyword. What the enumeration reads is still a
    field with no default, which is what this fixture is for.
    """

    archive_index: str | None = field(kw_only=True)


@dataclass(frozen=True)
class ARegistryDeclaredCorrectly(Egress):
    """A purpose declared the way the decision asks for."""

    probe: str | None = None


def network_libraries_named_by(source: str) -> set[str]:
    """The network libraries this source names, read from the parse tree."""
    named: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            named.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            named.add(node.module.split(".")[0])
    return named & REACHES_THE_NETWORK


def test_the_default_configuration_names_no_endpoint() -> None:
    assert defaulted_endpoints(Egress) == ()
    assert NOTHING_CONFIGURED == Egress()


def test_a_purpose_carrying_a_default_endpoint_is_reported() -> None:
    """What shows the enumeration reads a default rather than nothing.

    Without this the test above would pass on a registry the reader could not
    read at all, and the two results are indistinguishable while the registry is
    empty.
    """
    assert defaulted_endpoints(ARegistryCarryingADefault) == ("archive_index",)


def test_a_purpose_that_cannot_be_left_unset_is_reported() -> None:
    """The same failure by the other route.

    A purpose with no default cannot be absent, because a configuration that
    omits it cannot be built, so an operator who configured nothing has no
    configuration rather than an empty one.
    """
    assert defaulted_endpoints(ARegistryDemandingOne) == ("archive_index",)


def test_a_purpose_declared_correctly_is_not_reported() -> None:
    """The other direction, which is what a reader that reports everything fails.

    A check that flagged every declared purpose would pass both tests above and
    would make the first real endpoint impossible to declare.
    """
    assert defaulted_endpoints(ARegistryDeclaredCorrectly) == ()
    assert declared_purposes(ARegistryDeclaredCorrectly) == (
        *declared_purposes(Egress),
        "probe",
    )


def test_a_purpose_nobody_configured_is_refused() -> None:
    with pytest.raises(EgressNotConfigured, match="probe"):
        endpoint_for("probe", ARegistryDeclaredCorrectly())


def test_a_purpose_the_registry_does_not_declare_is_refused() -> None:
    """Fail closed on a name nothing declares, rather than on a missing value.

    A purpose spelled wrong at the call site would otherwise read as a purpose
    nobody configured, and the two are repaired in different places.
    """
    with pytest.raises(EgressNotConfigured, match="archive_index"):
        endpoint_for("archive_index", ARegistryDeclaredCorrectly())


@pytest.mark.parametrize("endpoint", ["", "   "], ids=["empty", "spaces"])
def test_a_blank_endpoint_is_refused_like_an_absent_one(endpoint: str) -> None:
    """The near miss, and the one a configuration file actually produces.

    A key present with nothing after it satisfies every check that asks whether
    a setting exists, and it names no host.
    """
    with pytest.raises(EgressNotConfigured):
        endpoint_for("probe", ARegistryDeclaredCorrectly(probe=endpoint))


def test_connecting_without_a_configured_endpoint_is_refused() -> None:
    """Refused before an address exists, rather than after a failed attempt."""
    with pytest.raises(EgressNotConfigured):
        connect("probe", ARegistryDeclaredCorrectly())


def test_connecting_for_a_purpose_nothing_declares_is_refused() -> None:
    """The default argument is the empty configuration, so a forgetful caller.

    A caller that omits the configuration reaches nothing rather than whatever
    the process happened to be holding.
    """
    with pytest.raises(EgressNotConfigured):
        connect("archive_index")


def test_an_endpoint_that_names_no_port_is_refused() -> None:
    """A port is stated rather than assumed, so a default cannot pick a service."""
    with pytest.raises(EndpointUnreadable):
        split_endpoint("plates.example.org")


@pytest.mark.parametrize(
    ("endpoint", "expected"),
    [
        ("plates.example.org:443", ("plates.example.org", 443)),
        ("::1:8080", ("::1", 8080)),
        (" 127.0.0.1 :80", ("127.0.0.1", 80)),
    ],
)
def test_an_endpoint_is_read_as_the_host_and_port_it_names(
    endpoint: str, expected: tuple[str, int]
) -> None:
    assert split_endpoint(endpoint) == expected


def test_a_configured_endpoint_is_reached() -> None:
    """A refusal that refused everything would pass every test above.

    It would also be wrong, and it would be wrong invisibly until the first
    operator configured something. A real connection is made here, to a server
    started on this machine, and it is expected to work. Loopback is what the
    block in `tests/conftest.py` allows, and decision 0014 is about what leaves
    the host rather than about what is opened on it.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.bind(("127.0.0.1", 0))
        server.listen(1)
        accepted: list[socket.socket] = []
        listener = threading.Thread(
            target=lambda: accepted.append(server.accept()[0]), daemon=True
        )
        listener.start()
        host, port = server.getsockname()
        configured = ARegistryDeclaredCorrectly(probe=f"{host}:{port}")
        with connect("probe", configured, timeout=5) as client:
            client.sendall(b"configured")
        listener.join(timeout=5)
    assert accepted, "the loopback server accepted nothing"
    with accepted[0] as served:
        assert served.recv(10) == b"configured"


def test_only_one_module_in_the_package_names_a_library_that_reaches_the_network() -> (
    None
):
    reaching = {
        path.name: named
        for path in sorted(PACKAGE.rglob("*.py"))
        if (named := network_libraries_named_by(path.read_text(encoding="utf-8")))
    }
    assert set(reaching) <= {THE_ONE_WAY_OUT}, (
        "the socket layer is reached through src/plattenschrank/egress.py and "
        "nowhere else, and these name a library that reaches it: "
        + ", ".join(
            f"{name} ({', '.join(sorted(named))})" for name, named in reaching.items()
        )
    )


def test_the_module_allowed_to_reach_the_network_does() -> None:
    """The test above passes on a package that reaches nothing at all.

    That is the state this tree would be in if `egress.py` stopped importing a
    socket, and there would then be no chokepoint for anything to go through
    while the check went on reporting green.
    """
    source = (PACKAGE / THE_ONE_WAY_OUT).read_text(encoding="utf-8")
    assert network_libraries_named_by(source) == {"socket"}


def test_the_import_reader_catches_the_spelling_a_grep_would_not() -> None:
    """What shows the reader reads imports rather than passing on everything."""
    assert network_libraries_named_by(A_SOURCE_THAT_REACHES_THE_NETWORK) == {"urllib"}
    assert network_libraries_named_by("import numpy as np\n") == set()
