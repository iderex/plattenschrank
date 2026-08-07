# 0013. Determinism and provenance on every measurement row

Decided. Issue #14.

## The decision

### The five mandatory fields

Every measurement row carries all five. A row missing any of them is refused
rather than written with a blank.

| Field | What it names |
| --- | --- |
| `plate_id` | The plate the measurement came from, unique inside its collection. |
| `collection_id` | The archive the plate belongs to. |
| `software_version` | The version of this software that produced the row. |
| `calibration_id` | The identifier of the calibration used, as decision 0005 requires. |
| `model_id` | The identifier of any model used, or an explicit none where the path was classical rather than learned. |

### The determinism rule

Running the same input through the same version produces byte-identical output.
Sources of nondeterminism are pinned deliberately: random seeds, thread counts
wherever a reduction is order-sensitive, and any hash-ordered iteration that
reaches an output.

## Why

A number from this pipeline is meant to be usable in a result somebody
publishes. A number that cannot say which calibration and which model produced
it cannot be checked, cannot be reproduced after either of those moves, and
cannot be withdrawn cleanly when one of them turns out to be wrong. That last
case is not hypothetical on a board whose whole subject is failure modes that
resemble signal.

Byte-identical output is the cheap version of the same property. Once it holds,
a rerun that differs is a signal rather than a shrug, and a change that was
meant to be a refactor can be proved to be one by comparing outputs rather than
by reading the diff.

The cost is that the sources of nondeterminism have to be pinned deliberately.
That cost is paid once, at birth, and it is much larger later.

## What was rejected

Provenance kept in a side log rather than on the row. Side logs get separated
from the data they describe on the first copy, and the copy is the normal case
here because these outputs are meant to be shared.

## The conditions this record does not yet satisfy

Two tests are owed. One runs a fixture through the pipeline twice and asserts
the outputs are byte-identical. The other asserts that a row missing any of the
five fields is refused, one case per field, so that losing a single field reds
the suite.

Neither exists at the commit that adds this record:

    git ls-files src/ tests/

returns nothing. So both rules above are stated and neither is enforced, and
issue #14 stays open until the two tests exist and are proved to bite.
