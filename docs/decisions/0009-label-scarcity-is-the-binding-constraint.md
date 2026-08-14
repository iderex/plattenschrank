# 0009. Label scarcity is the binding constraint

Decided. Issue #10.

## The decision

Label scarcity is the constraint that decides what this board can build, and
every learned component is designed around it from the start rather than
adjusted for it later.

The annotation loop is an exchange format on disk, not a module inside the
pipeline. Any annotation platform can write it and no platform is a dependency
of this repository.

### The format

The annotation exchange format is called `plateanno`. Its schema location is
the directory `docs/schemas/plateanno/`, holding one versioned schema file per
released version of the format, and the version a file was written against
appears inside the file. The schema is the authority for the field list, and
this record does not restate it, because a list here drifts against the file
that decides it. That directory is empty at the commit adding this record; the
schema is written under issue #66.

What the format has to carry follows from the constraint rather than from
convenience. It carries more than one annotation of the same object, because
agreement between annotators is a number this board has to be able to compute.
It carries the provenance of each annotation, meaning which pass and which
campaign produced it, so a bad batch can be found and removed without discarding
the good ones. It carries an explicit uncertain marker, because an annotator who
cannot tell an artefact from a source is information rather than noise. It
carries no field that identifies a person by default.

### The reporting rule

Every metric this board reports carries the number of labels that produced it.
A result that needed ten thousand labels and a result that needed two hundred
are different results even when the metric matches, and a report that omits the
count cannot be compared with either.

## Why

There are more than five hundred thousand machine-readable plates. Nothing
labelled exists at a size that trains anything: not for plate artefacts, not for
overlapping prism traces, not for German handwritten plate envelopes. Compute is
not the constraint here and neither is data volume. The number of hours a person
with the right expertise will spend drawing boxes is the constraint, and it is
small.

Writing that into the plan changes what gets built, and finding it out halfway
through does not. Active learning becomes a first-class part of the design.
Agreement between annotators becomes something the format has to carry. Weak
supervision and simulation become load-bearing.

Keeping the loop as a file format is what stops one annotation platform
becoming a hard dependency of the science. The public
repository `iderex/lesesaal` is building a self-hostable annotation platform,
and this format is what connects the two. If that platform is never used here,
the format still works with anything else, and if it is used, nothing in this
repository has to know.

## What was rejected

Building an annotation user interface inside this repository. It doubles the
surface, it is a different discipline, and it makes the pipeline depend on a web
stack that has nothing to do with plates.

Treating labels as a fixed input that arrives from somewhere. That assumption
is what leaves the shortage to be discovered halfway through the build, and
this record is written before that can happen.

## What this record leaves open

Whether an annotator identity is stored at all is not decided here. It is
entry 6 of issue #1 and it belongs to the maintainer. The format is built so
that the answer is a configuration setting and no schema version moves with it.

## The condition this record does not yet satisfy

The rule that every reported metric carries its label count has to be checkable
on a published evaluation report. No such report exists:

    git ls-files docs/ | grep -i eval

returns nothing. An absent report is not a report that passes. That half of the
condition is unmet, and issue #10 stays open until the first evaluation report
carries the count.
