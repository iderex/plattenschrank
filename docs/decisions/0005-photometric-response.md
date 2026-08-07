# 0005. The non-linear photometric response is its own stage

Decided. Issue #6.

## The decision

The relation between recorded density and incident intensity is estimated per
plate as an explicit stage with its own output, its own uncertainty and its own
identifier. No stage anywhere in the pipeline may assume that a pixel value is
proportional to flux.

### The stage boundary

The stage takes a scan and the detections on it, and nothing downstream of
photometry. It ends before any magnitude is written. Detection runs on the
uncalibrated scan and is not permitted to consume the curve, so a change to the
curve never moves what was detected.

### What the stage outputs

| Output | Meaning |
| --- | --- |
| `calibration_id` | The identifier of this curve, unique across the repository's outputs. |
| The curve itself | The estimated density-to-intensity relation for this plate, in a form a person can plot and dispute. |
| The supported range | The density interval over which the curve is claimed to hold. Outside it the curve is not extrapolated; a measurement there is flagged rather than produced. |
| The uncertainty of the curve | Carried as its own component and never merged into a single error bar at this stage. |
| The inputs it was estimated from | Enough to re-estimate the same curve from the same scan. |

Every measurement derived from a curve carries that curve's `calibration_id`.
A measurement row without one is refused.

## Why

A photographic emulsion responds to light along a curve with a toe, a roughly
straight section and a shoulder, and it saturates. That is the first thing plate
work has to deal with and the first thing a pipeline written for modern
detectors gets wrong, because such a pipeline was built where counts really are
proportional to photons over most of the range.

Making it a stage rather than a correction buried inside photometry has three
consequences worth the extra structure. The curve becomes something a person can
look at and dispute. Two calibrations of the same plate can be compared without
rerunning detection. And the uncertainty the curve introduces is carried forward
instead of being absorbed into a single error bar whose composition nobody can
recover.

## What was rejected

A global linearisation applied once per collection. Plates differ inside a
collection by emulsion batch, development, exposure time and age, and one curve
per collection is an average that fits no individual plate at the ends, which is
exactly where the faint and the bright objects are.

## The condition this record does not yet satisfy

The refusal of a measurement row without a `calibration_id` has to be proved by
a test, and the proof is the test failing when the refusal is removed. At the
commit that adds this record there is no test suite:

    git ls-files tests/

returns nothing. So the refusal above is stated and not enforced, and issue #6
stays open until a test proves it bites.
