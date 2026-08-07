# 0007. Objective-prism extraction is instance segmentation under overlap

Decided. Issue #8.

## The decision

Extraction of objective-prism spectra is posed as instance segmentation with
overlapping instances. Each spectrum is a region with an identity, regions may
share pixels, and the model assigns flux between them. It is not posed as source
detection followed by aperture extraction along a trace.

### What the model outputs for a contested pixel

A contested pixel is one claimed by more than one trace. The model does not pick
a winner and it does not drop the pixel. It outputs, for that pixel, a
distribution over the traces that claim it: a set of fractions that sum to one
across the claiming traces, plus the fraction attributed to background.

Two things follow onto every extracted spectrum. Each wavelength bin carries the
fraction of its flux that came from contested pixels, so a spectrum assembled
mostly from contested pixels says so on the row rather than in a caption. And
the identities of the traces it was contested with are recorded, so a
disagreement between two extractions can be traced to the pair that caused it.

### The baseline it is measured against

Detection followed by a fixed-width aperture along a fitted trace. That is the
classical method and it stays in the tree as the number to beat. The evaluation
for this work reports the learned method and the classical baseline side by
side, on the same fields, with the crowding of each field stated, because a
learned method that wins only on average and loses on uncrowded fields has not
shown what it claims.

## Why

This is the part of the subject nobody has automated, and the reason is in the
data. An objective prism turns every star in the field into a short
low-dispersion streak. In a crowded field those streaks cross and superimpose,
the signal to noise is poor at both ends of every trace, and the background is
itself structured by the neighbouring traces. Detect-then-extract assumes you
can decide where one object is before you decide what its light is, and on these
plates that ordering does not hold: which trace a pixel belongs to and how
bright each trace is are the same question.

Posing it as segmentation with overlap makes the ambiguity a modelled output
rather than an error. A pixel can carry a distribution over the traces that
claim it, and a spectrum extracted from contested pixels can say so.

## What was rejected

Detection followed by a fixed-width aperture along a fitted trace, as the
design. It stays as the baseline to beat, because a new method that cannot beat
the manual practice on uncrowded fields has shown nothing. It is rejected as the
design because it has no answer at all in the crowded case, and the crowded case
is where the millions of unevaluated spectra are.

## The condition this record does not yet satisfy

The evaluation harness for the objective-prism milestone has to report both the
learned method and the classical baseline. That harness does not exist:

    git ls-files src/ tests/

returns nothing. So the reporting requirement is stated and not demonstrated,
and issue #8 stays open until the harness reports both.
