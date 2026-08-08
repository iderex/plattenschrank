# 0008. Evaluation holds out whole collections

Decided. Issue #9.

## The decision

### The protocol

The headline number for every learned component on this board is
leave-one-collection-out. The model is trained on some collections and reported
on a collection it has never seen.

The rotation runs over the collections that actually carry data for the task
being evaluated, and the report names them. Which those are is a measurement
rather than an assumption, and the two tasks do not have the same list.

For the objective-prism tasks, `docs/prism-survey.md` established the list on
2026-08-08 with the commands in it: DFBS, and APPLAUSE, whose prism plates sit
in six Hamburg plate series. It also established that DASCH holds no prism
plates in its seventh data release, so DASCH is not in that rotation.

For the direct-plate tasks the established collections are DASCH and APPLAUSE.
NAROO is not in either list yet, and the reason is not that its plates were
judged unsuitable: `docs/archive-terms.md` records that neither of its two
service hosts answered that route on 2026-08-08 while the observatory's own host
did. What NAROO holds is therefore not established from here, and it joins a
rotation when it can be read rather than on an assumption about what an
astrometric reduction archive contains.

A task whose established list holds one collection cannot produce this number at
all. It reports that it cannot, and it does not substitute a random split.

Each held-out collection produces its own number and all of them are reported.
An average across the folds may be quoted only next to the per-fold numbers,
never instead of them, because the spread between folds is the quantity this
protocol exists to expose.

### A held-out collection is never used for model selection

Not for hyperparameters, not for early stopping, not for checkpoint selection,
not for a threshold, and not for deciding which of two runs to report. Model
selection uses a validation split taken from the training collections only.

A collection that has been looked at once is no longer held out. There is no
partial version of this: a threshold tuned on the held-out collection makes the
reported number a fitted number wearing the name of a generalisation number.

### Random splits are a diagnostic

Random splits over pooled plates are permitted and useful for finding a broken
training loop early. They are never the reported result, and where one appears
in a report it is labelled as a diagnostic on the same line as its value.

Where a random split is used at all, it is grouped by plate, so the same plate
cannot appear on both sides. That is a floor and not a fix, for the reason
below.

## Why

Distribution shift between collections is one of the named failure modes this
board exists for. Two collections differ in telescope, emulsion, developer
chemistry, scanner, epoch and sky coverage, so a model has an enormous amount of
collection-specific signal available to it, and no incentive not to use it.

A random split puts plates from the same collection, often from the same
observing run and sometimes from the same night, on both sides. The number that
comes out is high, it is reproducible, and it does not survive contact with a
new archive. It is not a number that was measured carelessly; it is a number
that answers a different question than the one a reader will think it answers.

Fixing this as a decision rather than a convention matters because the wrong
split is the easy default in every framework, and because of the ratchet: once a
release quotes a random-split number, the honest number looks like a regression.
The first honest measurement then has to be argued for rather than published,
and the person arguing for it is arguing against their own project's history.

Reporting per fold rather than one average follows from the same reason. One
average hides the case this board cares most about, which is the fold where a
model trained on two archives falls apart on the third. That fold is the
estimate of what happens on the fifth archive, and it is the only estimate
available.

## What was rejected

Random splits with a per-plate group constraint as the headline. Better than
nothing, and it does stop the same plate appearing on both sides, but it does
not touch the collection-level signal, which is the larger effect. It is kept
above as the shape a diagnostic split takes, not as a result.

A single pooled test set drawn across all collections. It reports one number,
which is what a reader wants, and it answers the question of how the model does
on the archives it has already seen, which nobody needs to ask.

Holding out a fraction of each collection. It is the same failure in a form that
is harder to spot, because the held-out rows genuinely were unseen and the
protocol genuinely was strict about them.

## The condition this record does not yet satisfy

The done-condition of issue #9 asks for a refusal and a test that proves it: the
evaluation code refuses to produce a headline number when a collection appears
on both sides of a split, and the test constructs such a split and asserts the
failure.

There is no evaluation code at the commit that adds this record:

    git ls-files src/ tests/

returns nothing. So the protocol above is stated in a document, and a split that
leaks a collection would be accepted by everything in this repository. Issue #9
stays open until that refusal exists in the harness of issue #52, and until the
test has been shown to go red when the refusal is removed rather than only green
while it is present.
