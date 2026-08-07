# 0015. How the measurement schema is versioned

Decided. Issue #16.

## The decision

The measurement schema carries a version, and the rules for changing it are
written down before anything is published against it.

### The version field

The field is named `schema_version`. It appears on every measurement row and in
the file-level metadata of every bulk output, so a row separated from its file
still says what it was written against. Its value is `MAJOR.MINOR`, and the
version this record names as current is `1.0`. Nothing has been published
against it yet, so `1.0` is the first version rather than a version with
consumers.

### What is a minor change

A change that leaves every existing reader correct.

- Adding an optional column.
- Adding a new permitted value to a field whose consumers are documented as
  ignoring values they do not know.
- Widening a numeric range within the same unit.

Example: adding an optional `sky_background` column to the measurement rows.
A reader that never looks at it keeps producing the same answer, so the version
moves from `1.2` to `1.3`.

### What is a major change

A change that can make an existing reader silently wrong.

- Removing a column.
- Renaming a column.
- Changing a unit.
- Changing the meaning of an existing value, including tightening or loosening
  what a flag asserts.

Example: changing `uncertainty` from a standard deviation to a 95 per cent
interval. Every existing reader keeps working and every number it derives is
wrong by a factor, so the version moves from `1.3` to `2.0`.

The classification is decided by the effect on a reader, not by the size of the
change. A one-character unit change is major and a whole new optional column is
minor.

## Why

The output of this pipeline is meant to be joined against other catalogues and
kept for years. A unit that changes silently is the failure mode that survives
longest and is found latest, because every consumer keeps working and every
number is quietly wrong by a factor.

Writing the rule down before the first publication is the only moment it is
free. Afterwards, every change carries an argument about whether the old
behaviour was a promise.

## What was rejected

A single version tied to the software release number. It ties a schema promise
to an unrelated cadence, so a patch release either cannot fix a schema mistake
or has to pretend it did not.

## The condition this record does not yet satisfy

A test has to assert that the schema version the code holds matches the one this
record names, and it has to fail when either moves without the other. That is
the part that stops the record and the code drifting apart, which is the whole
reason for writing the version down.

It does not exist at the commit that adds this record:

    git ls-files src/ tests/

returns nothing. So the record names a version that no route compares against
anything, and issue #16 stays open until the test exists and is proved to bite.
