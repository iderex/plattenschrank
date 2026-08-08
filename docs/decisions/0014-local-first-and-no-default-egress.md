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
