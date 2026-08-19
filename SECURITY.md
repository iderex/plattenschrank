# Security policy

## What this repository is, so that a report can be about it

This is a Python package for machine learning on digitised astronomical
photographic plates, and most of the pipeline is not built: the subcommands
`ingest`, `calibrate`, `detect`, `extract` and `evaluate` report what they did
not examine and exit 3.

What runs today is a command line entry point, two validators for file formats
this project did not produce (`plateanno.py` for annotation batches,
`transcription.py` for structured extractions of transcribed pages), a
photometric response fit (`response.py`), a synthetic plate generator the tests
draw fixtures from (`synthetic.py`), a registry of outbound endpoints
(`egress.py`) and one command that puts data on a wire (`federate.py`). numpy is
the only runtime dependency. There is no release and no tag here and the version
in `pyproject.toml` is `0.0.0`, so anyone running this cloned it.

That shape decides the rest of this file. There is no server, no account, no
session and no privilege boundary inside the program; an operator runs it on
their own host over their own archive holdings. A policy listing account
takeover and privilege escalation would look thorough and would be describing
some other program.

## Reporting

Report privately through the GitHub advisory form for this repository:

https://github.com/iderex/plattenschrank/security/advisories/new

Private reporting is enabled here, measured rather than assumed:

    gh api repos/iderex/plattenschrank/private-vulnerability-reporting
    {"enabled":true}

So that door opens today. Tell me what you fed the program, what it did, and
what you expected instead. A file that reproduces it is worth more than a
description of one. If your reproducer carries anything read off a real plate
envelope or logbook, redact it or describe its shape instead, because I do not
want somebody's name sitting in an advisory thread.

## No response time is promised

I state no deadline for acknowledgement and none for a fix. A deadline this
project cannot keep is worse than no deadline at all: a reporter told to expect
an answer within some number of days who does not get one is left guessing
whether the report arrived, and the guessing is the harm. I would rather you
know that before you write than find it out by waiting.

## What counts as a vulnerability here

**Data leaving the host when nobody knowingly sent it.** This is the one that
matters most here. `docs/decisions/0014-local-first-and-no-default-egress.md` is
the position and `egress.py` enforces it: it is the only module that opens a
socket, every endpoint field defaults to absent, and `federate.py` sends nothing
unless the operator passes `--confirm send` exactly. Anything defeating that is
in scope: a default endpoint in the `Egress` registry, a second module reaching
the network directly, or rows sent without the confirmation or with one supplied
by something other than the person typing the command. The import check in
`tests/test_egress.py` is a floor rather than a proof, and says so: a library
reached through `importlib` under a name assembled at run time walks past it.

**A manifest that describes less than what gets sent.** The federation manifest
is what an operator reads before confirming, so a wrong manifest is consent
given against a false description. A column that would be sent and does not
appear in it, a count that does not match the rows, or a `PERSONAL_DATA`
sentence calling a column clear when that column can carry a name, is a
vulnerability here even though nothing crashes.

**A validator accepting what it must refuse.** `plateanno.validate_batch` and
`transcription.validate_extraction` stand between a file some annotation or
transcription platform produced and everything downstream of it. The extraction
rule with no exception is that a field carrying a value carries the source line
it was read from. A crafted document that passes either validator and then means
something other than what it validated as is worth reporting.

**Content escaping into a place it was never meant to reach.** Plate envelopes
and observing logbooks carry people's names. `plateanno._check_annotation`
refuses by position rather than by quoting content, because a diagnostic is a
place data escapes to. A refusal message, an exception, a log line or a manifest
that carries content read off a plate, an envelope or a logbook somewhere the
operator did not put it is in scope.

**A path from a file to code execution.** Nothing in `src/` imports `pickle`,
`subprocess`, `yaml` or `eval`, and the parsing is `json` plus two anchored,
length-bounded regular expressions read out of the schema document. If you have
found a route from a file this program reads to code that runs, that is exactly
what I want to see.

**A hole in the workflows.** Every action is pinned to a commit SHA, every
workflow declares its permissions, and none uses `pull_request_target`. A token
wider than its step needs, an injection through a pull request title or branch
name, or a mutable reference that slipped in, goes through the same channel.

## What is not a vulnerability here

**Federation is not encrypted and does not authenticate its destination.**
`federate._send` writes JSON lines into a plain TCP connection opened by
`egress.connect`, and there is no TLS anywhere in this tree. That is the current
state rather than a finding, and this file is where you learn it. Until it
changes, federate only over a channel you already trust. A protected transport
is public design work and belongs in an issue rather than a private advisory.

**`docs/data-protection.md` lags the tree.** It still says nothing in the
shipped code can open a connection and that the federation command does not
exist. Both were true when it was written and neither is now, because
`egress.py` and `federate.py` landed after it. That staleness is a real problem
and I want it reported publicly as an issue: handling a documentation defect
privately only keeps the inaccurate version in front of readers for longer.

**A stage that does nothing.** Five subcommands are unbuilt and exit 3. That a
stage which does not exist fails to validate its input is not a finding about
this repository.

**The absence of authentication, roles or sandboxing.** There is nothing to
authenticate to, and whoever can run the command can already read the files it
would read.

**A generic dependency advisory.** The `build` job audits the installed graph
with `pip-audit --strict` on every push and pull request, and
`dependency-review` checks each pull request's dependency diff against the same
database. If an advisory is reachable through this program's own inputs, show me
the path and that is a report; a scanner number with no path through this code
is an issue.

**Resource exhaustion from a file you handed it yourself.** `read_rows` reads
the whole file and `read_batch` takes the whole text, so a large enough input
exhausts memory. That input is a local file the operator chose. It is a limit
worth fixing and it is not somebody reaching you.

**Trained model weights.** None are tracked, by
`docs/decisions/0011-model-weights-are-not-tracked.md`, and no release exists,
so there is no published artefact to tamper with. When weights are published
they are to be fetched by checksum or not at all, and a break in that is in
scope on the day it exists.

## Which versions this covers

`main`, and nothing else. There is no tag and no release to backport to, so a
fix is a commit on `main` and that is the whole answer.

## After a report

I say what I could reproduce and what I could not, fix it on `main`, and publish
through the same advisory. I will credit you by whatever name you give me, or
leave you out if you would rather. There is no bounty and there never has been
one.
