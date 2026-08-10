"""The one place in this package that may put a packet on a wire.

``docs/decisions/0014-local-first-and-no-default-egress.md`` states the position:
nothing leaves the host unless the operator configured an endpoint for that
purpose. This module is what refuses a departure from it, rather than a second
sentence asserting it.

Two properties, and they fail separately.

The default configuration names no endpoint. ``Egress`` is the registry of every
outbound endpoint this software can be configured with, one field per purpose,
and every field admits absence and is absent unless somebody sets it. A default
endpoint added later is a field whose default is no longer ``None``, which is
what ``defaulted_endpoints`` reads and what ``tests/test_egress.py`` refuses.

The socket layer is reached from here and from nowhere else. ``connect`` is the
only function in this package that opens a connection, and it cannot be called
without an endpoint: the purpose is looked up in the registry and an unset one is
refused before an address exists. Everything else in the package is held to that
by an import check in ``tests/test_egress.py``, because the useful moment to
catch a stage that builds its own socket is the pull request that adds it.

## What the registry holds today, and why that is not a defect

Nothing. No stage in this tree fetches anything yet, so there is no purpose to
declare, and a purpose invented here would be a decision about an adapter taken
in the wrong file. The consequence is stated rather than left to be discovered:
the enumeration below ranges over an empty set today, so the test that reads it
passes without reading a field. What shows that it reads a default at all is a
declaration in the suite that carries one, and what shows it bites on this
registry is the branch under ``scratch/`` that adds a default endpoint here.

## What this does not refuse

Name resolution. ``connect`` resolves a host, and a caller that resolves one
itself and never connects puts a query on the wire and is not stopped here. The
same bound is on the block in ``tests/conftest.py`` and is written there too.

A subprocess. Nothing here reaches into a program this package starts, so a stage
that shells out to a downloader is outside every check in this module.

An import the tree does not make yet. The import check reads the modules a source
file names, so a library reached through ``importlib`` under a name assembled at
run time passes it. That is a floor rather than a guarantee, and the set it reads
is written in the test beside the reason for each entry.
"""

from __future__ import annotations

import socket
from dataclasses import MISSING, dataclass, fields
from typing import Final

# How long ``connect`` waits before it gives up. A connection with no timeout
# hangs a run against an archive that accepts a socket and never answers, which
# on a batch over a collection is indistinguishable from a stage that is slow.
DEFAULT_TIMEOUT_SECONDS: Final = 30.0


class EgressRefused(RuntimeError):
    """Raised where this package declined to reach off the host.

    Its own type rather than ``OSError``, for the reason ``tests/conftest.py``
    gives for the same choice: a caller that catches ``OSError`` around a
    connection would swallow this and report that the archive was unreachable.
    A refusal by this software and a failure of somebody else's machine are
    opposite statements and must not be catchable by the same handler.
    """


class EgressNotConfigured(EgressRefused):
    """Raised where a purpose was reached for and no operator configured it."""


class EndpointUnreadable(EgressRefused):
    """Raised where a configured endpoint does not name a host and a port.

    Apart from ``EgressNotConfigured`` because the two say opposite things about
    the operator. One says nobody configured this and the run should stop; the
    other says somebody did and typed something this cannot use.
    """


@dataclass(frozen=True)
class Egress:
    """Every outbound endpoint this software can be configured with.

    One field per purpose, each written ``str | None`` and each defaulting to
    ``None``. A purpose that is added later is unset until an operator sets it,
    which is the default this decision is about, and the annotation is where that
    is declared rather than in a list somewhere else.

    Frozen for the reason ``model.py`` gives: a configuration that can be changed
    after it has been read is a configuration two stages can disagree about.
    """


# The configuration in force where the operator has configured nothing, which is
# every run until one of them does. It is a value rather than a function so that
# a caller cannot be handed a different empty configuration than the one the
# suite enumerates.
NOTHING_CONFIGURED: Final = Egress()


def declared_purposes(registry: type[Egress]) -> tuple[str, ...]:
    """The purposes this registry declares, in the order it declares them."""
    return tuple(field.name for field in fields(registry))


def defaulted_endpoints(registry: type[Egress]) -> tuple[str, ...]:
    """The purposes whose endpoint is anything other than absent by default.

    A field with no default at all is reported too. It cannot be given one by an
    operator who has not been asked, so a registry carrying one has no default
    configuration to be empty, which is the same failure by another route.
    """
    return tuple(
        field.name
        for field in fields(registry)
        if field.default is MISSING or field.default is not None
    )


def endpoint_for(purpose: str, configuration: Egress) -> str:
    """The endpoint configured for this purpose, or a refusal.

    A blank is refused alongside an absence, for the reason ``model.py`` gives:
    a blank is what a configuration file with an empty key produces, it satisfies
    every check that asks whether a setting is present, and it says nothing.
    """
    declared = declared_purposes(type(configuration))
    if purpose not in declared:
        raise EgressNotConfigured(
            f"{purpose!r} is not a purpose this software can be configured with. "
            f"It declares {', '.join(declared) or 'no purpose at all'}, and a "
            "connection is made for a declared purpose or it is not made."
        )
    endpoint = getattr(configuration, purpose)
    if not isinstance(endpoint, str) or not endpoint.strip():
        raise EgressNotConfigured(
            f"no endpoint is configured for {purpose!r}, so nothing is reached "
            "for it. docs/decisions/0014-local-first-and-no-default-egress.md is "
            "why this is a refusal rather than a default somebody has to find and "
            "switch off."
        )
    return endpoint


def split_endpoint(endpoint: str) -> tuple[str, int]:
    """An endpoint as the host and port it names, or a refusal.

    The port is required rather than defaulted. A default port is a second place
    a destination is decided, and the operator who typed a host without one has
    not said which service they meant.
    """
    host, separator, port = endpoint.rpartition(":")
    if not separator or not host.strip() or not port.isdigit():
        raise EndpointUnreadable(
            f"{endpoint!r} does not name a host and a port. An endpoint is "
            "written host:port, and the port is stated rather than assumed."
        )
    return host.strip(), int(port)


def connect(
    purpose: str,
    configuration: Egress = NOTHING_CONFIGURED,
    *,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> socket.socket:
    """Open a connection for a configured purpose, and refuse without one.

    The configuration defaults to the empty one, so a caller that forgot to pass
    one is refused rather than reaching whatever the process had lying around.
    """
    host, port = split_endpoint(endpoint_for(purpose, configuration))
    return socket.create_connection((host, port), timeout=timeout)
