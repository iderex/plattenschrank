# Data protection

This is the document to read before running this software on plates whose
envelopes and logbooks carry people's names. It is written for the person who
will run it rather than for a lawyer, and it does not require reading the code.

Four things it says without hedging, three things it says this software will not
do for you, and under every one of them the line that holds it up. Where a
mechanism holds a statement, that mechanism is named and you can open it. Where
nothing holds it, the statement says so in those words. A document that reads as
an assurance where the mechanism is only a habit is worse than one that admits
the habit.

`docs/personal-data-inventory.md` is the detailed companion to this: six
entries, each saying what the data is, where it enters, where it is stored, how
long it is kept, on what basis it is processed and who the controller is. This
document is the short version and the inventory is the one to work from.

## The four statements

### 1. What you put in stays on the host that runs this software

Scans, envelopes, logbooks, annotations and everything derived from them stay on
the machine you run this on. Nothing is copied off it.

What holds it up. Nothing in the shipped code can open a connection, which is a
fact about the tree rather than a promise:

    git grep -nE '^\s*(import|from)\s+(socket|ssl|http|urllib|requests|httpx|aiohttp|ftplib)\b' -- src/
    (no output)

Its one runtime dependency is a numeric array library, declared in
`pyproject.toml`, and nothing else is installed with it.

`tests/conftest.py` refuses an outbound connection attempted from the test
process, and `tests/test_offline.py` is the file that goes red when that refusal
is removed. The `build` job runs that suite on every push and every pull
request.

What that does not cover, and the sentence stays negative. The refusal is
installed in the test process, so it holds over the suite and not over the
software an operator runs. No check reads the shipped code for an outbound call.
Issue #71 is where that check is owed, and until it lands this statement is held
by the absence above being true rather than by anything refusing a change to it.
The refusal also does not reach name resolution, a raw send, or a subprocess the
suite starts, which is written out where it lives.

### 2. Nothing is sent anywhere unless you send it

There is no step in this software that transmits your data, and there is no
default endpoint for one to transmit to. Sending anything is planned to be a
command you run, against a manifest derived from your own data, with a
confirmation.

What holds it up. That command does not exist yet:

    git grep -niE 'federat' -- src/ tests/
    (no output)

So today the statement is true in a stronger form than it is written: nothing
here sends, because nothing here can. Issue #72 is where the command is designed
and issue #71 is where the check that refuses a default endpoint is owed. When
that command lands, this section is what has to be rewritten, and the thing to
check is whether the confirmation is real rather than a flag with a default.

Nothing refuses a change to any of this today.

### 3. There is no telemetry, no usage reporting and no crash reporting

None of the three exists, and none of them is a setting you have to find and
switch off. This is not an opt-out that defaults to on.

What holds it up. The three are absent from the tree:

    git grep -niE 'telemetry|analytics|sentry|crash.?report|usage.?report' -- src/
    (no output)

`docs/decisions/0014-local-first-and-no-default-egress.md` is where this was
decided, and it refuses opt-out telemetry by name, aggregate and anonymous
included, along with automatic model downloads on first run.

Nothing refuses a change to this. A decision record is a reason written down and
not a machine, and the check that would refuse a default endpoint is issue #71.

### 4. The handwriting component turns names in an image into names in a text field

Plate envelopes and observing logbooks carry the names, initials and signatures
of the people who made the observations, written next to the date and the place.
Reading them is one of this project's stated aims.

That step is not neutral, and this is the sentence to take away from this
document. A name in a scanned image is hard to search and is found by somebody
who was already looking at that plate. The same name in an indexed text field is
found by anyone who searches for it and joins to every other row that carries it.
The transcription step is where the first becomes the second, and it is your act
as the operator rather than the archive's.

What follows from that is yours to decide, not this software's: whether you
transcribe those fields at all, whether you keep the names in your catalogue,
whether you publish a catalogue that carries them, and how long you keep any of
it. Deciding it by default, by running the pipeline and seeing what comes out,
is deciding it.

What holds it up. Nothing, because the component does not exist yet:

    git ls-files src/plattenschrank/
    src/plattenschrank/__init__.py
    src/plattenschrank/__main__.py
    src/plattenschrank/cli.py
    src/plattenschrank/model.py
    src/plattenschrank/synthetic.py

This section describes what the component will do rather than what it does. It
is here before the component so that the decision is in front of you at the
point where it is still a choice. Entries 2, 3 and 6 of
`docs/personal-data-inventory.md` are the detail, and entry 3 is the one where
the answer may not be routine: per-hand adaptation holds something about how an
individual writes, and whether that amounts to processing a behavioural
characteristic to identify a person is open in the design rather than in the law.

## What this software does not do for you

### It does not decide your legal basis for processing

The basis depends on who you are, what you intend to do with the output, and
where you are. None of those is knowable from here, so this software states
none, and a statement here would be worth less than nothing because you would be
relying on it.

What it owes you instead is the material to establish one, which is the
inventory and the technical facts in it, so your assessment is made against what
the software does rather than against what it was assumed to do.

Nothing refuses a change to this, and nothing could. It is a statement about who
decides.

### It does not decide your retention period

This software sets no retention on data it did not create, and it does not
delete your holdings. What it creates, it writes where you told it to and leaves
there.

The retention answer for a scanned image is not the retention answer for a
searchable index built from it, and treating one as covering the other is the
mistake this line exists to prevent.

Nothing refuses a change to this.

### It is not a compliance product

Running this software does not make you compliant with anything, and no output
of it is evidence that you are. There is no report here that a supervisory
authority asked for, no certification behind it, and no assessment of your
processing.

What it is, is software that is honest about what it touches. The inventory
tells you what the data is and the sections above tell you where it goes. The
assessment is yours.

Nothing refuses a change to this either, and this is the one where that matters
least: no check could make a claim of compliance true or false.

## Where the rest of it is

`docs/personal-data-inventory.md` for the six entries in detail, including the
two that are easiest to miss, which are campaign metadata that singles out a
person with no name field, and names that reach a measurement row and travel
with it beyond your host.

`docs/decisions/0014-local-first-and-no-default-egress.md` for the position and
what it rejected.

`docs/decisions/0012-headless-and-cpu-by-default.md` for why the gated tests run
with no network at all, which is the same rule pointed at the suite.

`CONTRIBUTING.md` for which rules on this repository a machine refuses and which
are held by reading. Every rule there carries one line or the other, in the same
way every statement above does.
