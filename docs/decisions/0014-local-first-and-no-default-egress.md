# 0014. Nothing leaves the host by default

Decided. Issue #15.

## The decision

### The rule

The software makes no outbound network connection unless the operator has
configured an endpoint for that specific purpose. Configured for that purpose,
not configured in general: an endpoint an operator set for one thing does not
become permission for a second thing to use it.

Data an operator puts in stays on the host that runs the software until the
operator deliberately sends it somewhere. Sending is an act the operator
performs, never a default they have to discover and switch off.

### The named exclusions

Four things are named as never happening on their own:

| Excluded | What it covers |
| --- | --- |
| Telemetry | Any reporting of what the software did, including anonymous and aggregate reporting. |
| Usage reporting | Any count of runs, installs, features used or data volumes, sent anywhere. |
| Crash reporting | Any automatic submission of a traceback, a core file or a diagnostic bundle. |
| Model download | Any fetch of a weight file that happens because a run needed it rather than because an operator asked for it. |

### A discrepancy in the issue, recorded rather than resolved

The done-condition of issue #15 asks this record to state "the three named
exclusions". The decision text in the same issue names four, and they are the
four in the table above. This record enumerates the four rather than choosing
which three were meant, because dropping one to match a count would remove a
rule, and nothing in the issue says which one is not a rule.

## Why

Two reasons that happen to point the same way.

### The legal one

Plate envelopes and observing logbooks carry names, initials and signatures of
the people who made the observations. `docs/personal-data-inventory.md` holds
that as an inventory entry rather than as an assumption, and decision 0016 names
the observer field as the one that turns a name in a scanned image into a name
in an indexed text field. The annotation loop this board depends on carries
whatever a campaign chooses to record about the people who annotate, and whether
any annotator identity is stored at all is entry 6 of issue #1, which is open
and is not assumed here in either direction.

That is personal data. The safe position, and the one this board takes, is that
it does not leave the host by accident. An operator who is an archive or a
university group has an assessment to make about this software, and the
assessment is only possible if the answer to "what does it send" is nothing
rather than a list they have to audit.

### The engineering one

A default that reaches the network is a default that fails in an archive
basement, where a scanner and a workstation sit and the uplink does not. It is a
default that makes every test flaky, which decision 0012 refuses for the gate
and which this rule is the product-side half of. And it hides a dependency on
somebody else's uptime inside a number somebody publishes, which is the shape
this board is least able to afford: the number looks the same whether the
dependency answered or not.

## What was rejected

Opt-out telemetry, even anonymous and even aggregate. On this data class the
burden of an opt-out sits with the operator who did not read the release notes,
and there is no aggregate this project needs badly enough to move that burden.

Automatic model downloads on first run. Convenient, and it turns the first run
into an outbound connection at exactly the moment an operator is deciding
whether to trust the tool. Decision 0011 already keeps weights out of the
repository, so a weight file has to arrive from somewhere; this record says the
arrival is a command the operator runs, not a side effect of a run.

Crash reporting behind a prompt on first failure. A prompt at the moment
something broke is answered to make it go away.

## The condition this record does not yet satisfy

The done-condition of issue #15 asks for two things beyond this record: the unit
suite passing with outbound sockets blocked, and a test asserting that the
default configuration resolves to no endpoints, failing if any default endpoint
is added.

Neither exists at the commit that adds this record:

    git ls-files src/ tests/

returns nothing. There is no configuration to resolve and no suite to block
sockets around. So the rule above is stated in a document and nothing in this
repository refuses a default endpoint added tomorrow.

Issue #15 stays open until issue #24 lands the blocked-socket proof for the unit
suite and issue #71 lands the check that refuses a default egress, and until
that check has been shown to go red when a default endpoint is added rather than
only green while none is.

## Where that condition was met

The section above stands as it was written. What follows is what happened
afterwards, and it does not replace it.

Both halves it names are in place. The blocked-socket proof landed with issue
#24: the refusal is installed at the socket layer inside the test process by
`tests/conftest.py`, `tests/test_offline.py` is what reds when it is removed, and
every run says the block is in force before it prints a result. The check that
refuses a default egress landed with issue #71 in merge commit
`14be2ed4376e504d836894a8c45f1120728c005a`, as
`src/plattenschrank/egress.py` and `tests/test_egress.py`.

There is now a configuration to resolve. `Egress` is the registry of every
outbound endpoint this software can be configured with, one field per purpose,
each admitting absence and absent unless an operator sets it, and
`defaulted_endpoints` reads the ones that are anything else. It declares no
purpose today, because no stage in this tree fetches anything, and the module
says so rather than leaving a reader to conclude that an empty answer was a
measured one.

The rule that a connection is made for the purpose it was configured for is in
`connect`, which looks the purpose up and refuses before an address exists, and
the second way round it is refused by an import check holding every other module
in the package away from a network library.

Read against `main` at `14be2ed4376e504d836894a8c45f1120728c005a`:

    https://github.com/iderex/plattenschrank/actions/runs/31351321736
    uid=1001 user=runner DISPLAY=<unset> WAYLAND_DISPLAY=<unset>
    outbound connections are refused in this suite, except to 127.0.0.1, ::1, localhost
    284 passed, 1 warning in 3.66s

The last part of the condition is the one that separates a check from a green
result, and it is the reason this section can be written at all. The check was
shown to go red when a default endpoint is added, on a branch carrying that and
nothing else:

    https://github.com/iderex/plattenschrank/actions/runs/31350044150
    FAILED tests/test_egress.py::test_the_default_configuration_names_no_endpoint - AssertionError: assert ('archive_index',) == ()
    branch scratch/egress-reds-when-a-default-endpoint-is-added

What is still not refused anywhere is the rule's own subject rather than its
default. Nothing here reads a running process, so a build that reached the
network would be caught by the suite and by nothing else, and the block that
catches it is a test-process refusal rather than a property of the shipped
software. The bounds on that block are named in `tests/conftest.py` and stay
named: it does not reach name resolution, a raw send, or a subprocess the suite
starts.
