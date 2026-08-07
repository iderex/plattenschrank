# 0011. Model weights are not tracked in this repository

Decided. Issue #12.

## The decision

No trained model weights are committed to this repository. The rule holds
whatever the answer to the publication question turns out to be, because it is
about what git carries and not about what may be released.

Where weights are published, they are published as release assets carrying a
checksum, and the code fetches them by checksum or refuses to run. A fetch that
produces bytes whose checksum does not match the one the code holds is an error
and never a warning.

Every published weight file is accompanied by a model card stating what it was
trained on, what it was evaluated on, and what it should not be used for.

Whether weights may be published at all, and under what terms, is entry 2 of
issue #1 and is not decided here.

## Why

Weights are large binaries that change often, and git keeps every version
forever. A repository that carries them becomes slow to clone, impossible to
prune without rewriting history, and hostile to exactly the archive staff who
have the most to contribute and the least tolerance for a multi-gigabyte
checkout.

Fetching by checksum rather than by name is what makes the artefact auditable. A
weight file identified only by a URL can be replaced silently, and a pipeline
that produced a published number cannot then say which weights it used.

The model card is not decoration. Weights here are trained on a small number of
collections and they will fail on a collection they have never seen, which
follows directly from the evaluation decision on this board. Shipping them
without saying so invites exactly the misuse the plan is built to avoid.

## What was rejected

Large file storage attached to git. It moves the size problem rather than
solving it, it adds a service dependency to every clone, and it still leaves a
name where a checksum is wanted.

## The condition this record does not yet satisfy

The rule above is a sentence in a document. What makes it a rule is a
repository check that refuses a tracked file over a stated size threshold under
the weights directory pattern, together with a test that proves the refusal by
tripping it with a fixture.

Neither exists at the commit that adds this record:

    git ls-files tests/ scripts/

returns nothing, and no workflow in `.github/workflows/` reads a file size.
So this record states an intention that nothing refuses, and issue #12 stays
open until the check exists and a fixture proves it bites.
