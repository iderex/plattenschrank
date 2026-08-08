# 0006. Artefacts are an output class, not a filter

Decided. Issue #7.

## The decision

### Artefacts are labelled, predicted and reported

A plate artefact is an output class of the detector, with its own label in the
annotation format, its own predictions and its own reported numbers. It is not
removed by a filter before the detector sees it, and it is not folded into one
rejected category.

### One tracked taxonomy file

The artefact classes are enumerated in a single tracked file, and that file is
the authority for the list. The code reads the class list from it rather than
carrying its own copy, so a class cannot exist in the taxonomy and be missing
from the report, or the reverse. What the classes are, and what evidence from
the four collections puts each one in the list, is issue #49.

A class list that is restated in more than one place drifts, and the direction
it drifts is always the same: the report is written once and the taxonomy grows
afterwards, so the report silently stops covering the newest class, which is the
one nobody has numbers for yet.

### Per-class numbers, never one rejection count

The evaluation report breaks results down by artefact class. A single count of
things rejected is not an acceptable substitute and is not reported alongside as
a headline, because it is the number that gets quoted.

## Why

On a plate, a dust grain, an emulsion flaw, a scratch, a plate defect, a ghost
reflection and a halo around a bright star all produce something a source
detector will find, and at the level of a cutout each of them looks like an
object. That is the property that makes this subject different from a CCD
survey, where the artefact population is smaller, better understood and mostly
instrumental.

A pipeline that filters them out is making a classification decision without
recording it. Every such decision is a place where a real detection vanishes
with no trace: not a wrong number that a later check can catch, but a row that
was never written, which no audit of the output can find. The loss is invisible
in exactly the measurements this board wants to be publishable.

Naming the classes also makes the failure legible, and legibility here is worth
more than usual. "The detector found four thousand spurious things" tells
nobody what to do. "The detector confuses emulsion flaws with faint sources
below this magnitude and does not confuse scratches with anything" says what to
fix and what to label next. On a board where labelling effort is the binding
constraint, decided in 0009, the report's job is to direct that effort, and a
single rejection count directs nothing.

There is a third reason that only appears later. Decision 0008 reports the
headline number on a collection the model has never seen, and artefact
morphology is one of the things that differs most between collections, because
it comes from the emulsion, the developer chemistry, the storage and the
scanner rather than from the sky. Per-class numbers are what make a drop on a
held-out collection attributable. One count makes it a mystery.

## What was rejected

Sigma clipping and morphology cuts as the artefact strategy. They are cheap and
they work on the easy cases, which is why this record keeps them as the
classical baseline that issue #50 measures. As the strategy they hide the
decision, and they are tuned per collection by hand, which is the definition of
something that will not transfer.

One rejected category covering every artefact kind. It is easier to label,
which is a real argument on this board, and it produces a confusion matrix whose
largest cell cannot be acted on.

Artefact removal as a preprocessing step before detection. It reads as a
separate concern and it is the same decision made earlier, where it is harder to
see and where nothing downstream can recover what it discarded.

## The condition this record does not yet satisfy

The done-condition of issue #7 asks for more than this record. It asks that the
evaluation report the pipeline produces breaks results down by artefact class,
and that a reader can see that in the report.

There is no pipeline and no report at the commit that adds this record:

    git ls-files src/ tests/

returns nothing. There is also no taxonomy file, because issue #49 is open. So
the rule above is stated and nothing produces the report it describes. Issue #7
stays open until the report exists and shows per-class numbers, and the way to
prove it bites is the harness in issue #52 rather than a reading of the code.
