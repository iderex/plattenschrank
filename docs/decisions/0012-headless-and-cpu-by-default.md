# 0012. Gated tests are headless, unprivileged, offline and processor-only

Decided. Issue #13.

## The decision

### The four conditions

Every test that gates a merge runs under all four of these, and a test that
cannot is not in the gated set:

| Condition | What it means |
| --- | --- |
| Headless | No display. The test runs with no display variable set and opens no window. |
| Unprivileged | No elevation. The test runs as an ordinary user and never asks the operating system for consent, a service registration, a certificate store write or a driver. |
| Offline | No network. The test passes with outbound sockets blocked, and does not reach a name server, an archive or a package index. |
| Processor-only | No graphics processor. The test passes on a machine where none is present. |

### The naming rule for everything else

Work that genuinely needs a network or particular hardware is covered by a
separate harness, and the harness is named for what it needs. The name carries
the requirement in it, in the form `integration (needs network)`, so that a
reader of a run summary cannot mistake what ran for what did not.

A harness that is not run says that it was not run, and a gate that does not
include one says which one it left out. A summary that is silent about a harness
is read as covering it.

### Where the graphics processor question stops

The condition above is about the gate, and it is decided here. Whether any
shipped path may require a graphics processor is entry 5 of issue #1, it belongs
to the maintainer and it is open. This record does not assume an answer to it.

The gate condition survives every answer entry 5 could take, which is why the
two can be separated. A path that requires a graphics processor cannot be
covered by a test that runs where none is present, so under any answer that
admits such a path, that path is covered by a named hardware harness and not by
the gate. What entry 5 decides is whether such a path may be shipped at all, not
whether the gate can test it.

## Why

This is a birth requirement rather than a later hardening, because each of the
four is unfixable afterwards.

A suite that grew up assuming a display grows plotting calls into assertions,
and they are not marked as such; they are ordinary lines in ordinary tests. A
suite that grew up assuming a graphics processor grows kernels into unit tests
that then only run where one exists. A suite that grew up assuming a network
turns an archive outage into a red build that nobody can tell from a real
regression, which trains everybody to re-run a red build before reading it.
Undoing any of these means rewriting the tests rather than adding a flag,
because the assumption is spread across the assertions rather than held in one
place.

The unprivileged condition has a second reason that is about the machine rather
than the suite. A test that asks for elevation interrupts whoever is sitting in
front of the machine, and a prompt that appears while somebody is doing
something else is answered by reflex. A suite that can produce that prompt is a
suite that trains people to approve prompts.

There is a reason specific to this subject as well. The people who hold the
plates are archives and observatory groups, and the machine in front of them is
a workstation. A tool whose only tested path needs a data centre is a tool they
cannot check, and this board's users are exactly the people who have to be able
to check it.

The honest naming of the separate harness is the part that matters most. A green
gate has to mean what a reader thinks it means. A harness called
`integration (needs network)` cannot be misread as covering the offline case,
and a gate that does not run it says so.

## What was rejected

One suite with skip markers for the hardware-bound and network-bound tests. A
skipped test and a passing test look the same in a summary line, and the count
of skips is exactly the number nobody reads. It also makes the gated set a
property of the machine the run happened on rather than a property of the
repository, so two green runs can have covered different things.

A gate that is allowed to reach the network for fixtures only. It sounds narrow
and it makes every gated run depend on somebody else's uptime, which is the
dependency decision 0014 exists to keep out of the product. The synthetic plate
generator in issue #25 is what removes the need.

## The condition this record does not yet satisfy

The done-condition of issue #13 asks for a demonstration and for the command
that produced it: the default test command passing with no display variable set,
as an unprivileged user, with no graphics processor present, and with outbound
sockets blocked.

That demonstration is not in this record, and it cannot be, because there is no
suite and no default test command:

    git ls-files src/ tests/

returns nothing. Running a command that reports a pass over an empty suite would
be a green result standing where a measurement should be, which is worse than
this absence.

So all four conditions above are stated and none of them is proved. Issue #13
stays open until the harness in issue #22 exists and until issues #23 and #24
land the two proofs that are separately gated, at which point the commands they
record are what this record's condition is discharged by.
