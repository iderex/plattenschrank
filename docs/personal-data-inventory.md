# Personal data inventory

What personal data this software can come into contact with, written before any
of it is processed.

Each entry answers six fields: what it is, where it enters, where it is stored,
how long it is kept, on what legal basis it is processed, and who the
controller is. Where this project does not decide the answer because the
operator does, the entry says so and says what the operator has to decide.

This is the inventory. The document an operator reads is separate and is issue
#73.

## Who the controller is, once for all entries

This project ships software. It runs on the operator's machine, against
collections the operator obtained, and by decision nothing leaves that host by
default. So for every entry below the controller is the operator, meaning the
archive, institute or individual running the pipeline. This project is not a
controller and is not a processor for anyone, because it receives no data.

That answer is the same in all six entries and is stated once here rather than
repeated. Where an entry adds something to it, the entry says so.

## The legal basis, and why this project cannot state one

The legal basis is the operator's to establish, for the same reason the
controller is. A basis depends on who the operator is, what they intend to do
with the output and where they are, and none of those is knowable from here.

What this project owes instead is the material an operator needs to establish
one: the list below, so nothing is missed, and the technical facts in it, so the
assessment is made against what the software does rather than against what it
was assumed to do.

Where an entry says the basis is the operator's decision, that is a statement
about who decides and never a statement that no basis is needed.

## The entries

### 1. Names, initials and signatures on plate envelopes and logbooks, as image

What it is. Observers, plate measurers and archive staff wrote their names,
initials and signatures on plate envelopes and in observing logbooks. Some of
these people have living relatives and a few may be living. The date and place
of an observation sit next to the name, which means the record says where a
named person was on a given night.

Where it enters. With the scan. It is already in the image the archive holds and
this software does not create it.

Where it is stored. In the scanned image, wherever the operator keeps their
scans. This software does not copy it anywhere else at this stage.

How long it is kept. For as long as the operator keeps the scans. This project
sets no retention on data it did not create, and deleting an archive's holdings
is not a thing this software does.

Legal basis. The operator's decision. It is the same decision the operator
already made when they digitised or obtained the plates, and this software does
not change it, because reading an image changes nothing about it.

Controller. The operator, as above.

Not a special category.

### 2. The same names as machine-readable text

What it is. The output of the transcription component: the same names, initials
and dates, in an indexed text field.

Where it enters. It is created here. The transcription component reads the image
and writes text.

This is the entry to read carefully, and it is the reason this document exists
before the component is built. A name in a scanned image and a name in an
indexed text field are not the same processing. The first is hard to search and
is found by someone who was already looking at that plate. The second is found
by anyone who searches the catalogue for the name, and joins to every other row
carrying it. The transcription step is where this project turns the first into
the second, so it is this project's act and not the archive's.

Where it is stored. In the transcription output and in any catalogue built from
it, on the operator's host.

How long it is kept. The operator's decision, and one they have to make
deliberately rather than by default, because the answer for the image is not the
answer for the index.

Legal basis. The operator's decision, and a distinct one from entry 1. Whatever
basis covers holding the scans does not automatically cover creating a
searchable index of the people named in them.

Controller. The operator.

Not a special category by itself.

### 3. Handwriting shape, where a model adapts per hand

What it is. The characteristics of an individual's handwriting, held as whatever
a per-hand adapted model holds: a cluster identity, an adaptation state, or a
set of parameters fitted to one writer.

Where it enters. It is created here, by per-hand adaptation in the transcription
component, which is issue #56.

Where it is stored. In model state on the operator's host, and in the
per-hand breakdown of any error report, which is issue #58.

How long it is kept. The operator's decision.

Legal basis. The operator's decision, and this is the entry where the assessment
is not routine.

This is the entry that could be a special category, and it is named here rather
than left to be discovered. Handwriting is a behavioural characteristic of a
person. Where it is processed for the purpose of uniquely identifying that
person, that processing falls under the special categories in data protection
law, and the consequences for the operator are substantial. Whether per-hand
adaptation as built here amounts to that depends on what it is for and how it
works: adapting to improve recognition accuracy and uniquely identifying a
writer are different purposes that can share an implementation.

This document does not settle which one #56 will be, because #56 is not built.
What it does is put the question in front of whoever builds it, at the point
where the answer is still a design choice rather than a finding. If the
component ends up holding a per-writer identity that persists across documents,
the operator's assessment changes and this entry has to say so.

Controller. The operator.

### 4. Annotator identity in the annotation loop

What it is. Whatever a labelling campaign records about the people who label:
possibly nothing, possibly an opaque per-campaign identifier, possibly an
account identity.

Where it enters. With the annotation files, written by whatever platform the
operator uses. Decision 0009 keeps the loop a file format rather than an
integration, so this software reads what the format carries and never reaches
into a platform to get more.

Where it is stored. In the annotation files on the operator's host, and in any
agreement statistic computed from them.

How long it is kept. The operator's decision.

Legal basis. The operator's decision.

Controller. The operator, who is also whoever ran the labelling campaign, and
those may not be the same body. Where they differ, the operator has a
relationship to sort out with the campaign that this software knows nothing
about.

Not a special category.

Whether an annotator identity is stored at all is entry 6 of issue #1 and is a
maintainer decision that is open. This inventory does not assume an answer. The
format is built so that the answer is a configuration rather than a schema
change, which is what keeps this entry honest either way: if the answer is that
nothing is stored, this entry describes a category that turns out to be empty,
and an empty category correctly described is not a problem.

### 5. Campaign metadata that identifies without a name

What it is. Timing and volume attached to labelling work: when annotations were
made, in what order, how many, and at what pace.

Where it enters. With the annotation files, as the format's own metadata.

This entry exists because it is the one that gets missed. A campaign with no
name field can still single out a person. If two people labelled a batch and one
worked through the night, the timestamps separate them, and anyone who knows
which of the two that was has a name to attach. Removing the name field does not
make the data anonymous, and treating it as though it did is the mistake this
entry is written to prevent.

Where it is stored. In the annotation files and in anything derived from them.

How long it is kept. The operator's decision.

Legal basis. The operator's decision, and it does not disappear because no name
is present.

Controller. The operator.

Not a special category.

### 6. Names of people in the outputs and the provenance fields

What it is. Names that reach the pipeline's own outputs: an observer name copied
from a transcription onto a measurement row, or a name that ends up in a
provenance field.

Where it enters. From entry 2, by the pipeline carrying a transcribed field
forward.

Where it is stored. In the catalogue output, which by decision 0003 is a
columnar file a reader can open without this software, and which is meant to be
shared and joined against other catalogues.

How long it is kept. Beyond the operator's control once shared, which is the
point of this entry. Decision 0013 exists because these outputs are meant to
travel. Anything personal that reaches a measurement row travels with it, and no
retention decision made on the host reaches a copy somebody else holds.

Legal basis. The operator's decision, and the one with the widest consequences,
because it is the only entry where the data is expected to leave the host.

Controller. The operator, up to the point of sharing.

Not a special category.

## What is special and what is not

Under data protection law the special categories are a closed list, and it is
about what the data reveals rather than about how sensitive it feels. Nothing in
entries 1, 2, 4, 5 and 6 is in that list: a name, a date, a place of observation,
a labelling timestamp and an observer credit are ordinary personal data.

Entry 3 is the one that can be. Handwriting is a behavioural characteristic, and
processing it specifically to identify a person uniquely puts it in the special
list. Whether the per-hand adaptation this board plans does that is open, and it
is open in the design rather than in the law.

Two things this section does not say. It does not say the ordinary entries are
low risk, because entry 6 leaves the host and entry 2 turns an image into an
index, and both matter regardless of which list they are on. And it does not say
that entry 3 is settled either way.

## What is not covered here

This inventory covers what the software can touch. It does not cover what an
operator's own institution holds about its staff, what an archive holds about
its depositors, or anything an operator adds by joining these outputs to a
source this software never sees.

## The reference this document is owed

The done-condition of issue #70 asks that this inventory be referenced from the
operator documentation rather than living only in the repository. That
documentation is issue #77 and does not exist yet:

    git ls-files docs/ | grep -i operator
    (no output)

So that half is unmet rather than satisfied. It is unmet by an absent file and
not by a decision to leave it out.
