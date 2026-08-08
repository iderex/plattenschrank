# 0004. Archives are reached only through adapters, and collection identity is never dropped

Decided. Issue #5.

## The decision

### The four collections

One adapter per collection, and these four first, because they are the ones that
are machine-readable today:

| Collection | What it is |
| --- | --- |
| DASCH | The Harvard plate archive. |
| APPLAUSE | The German-led archive covering the Hamburg, Bamberg, Potsdam, Tautenburg, Tartu and Vatican collections, reached over its Virtual Observatory service. |
| NAROO | The astrometric reduction archive in France. |
| DFBS | The digitised first Byurakan survey. |

`docs/archive-terms.md` holds what each of the four publishes about licence,
redistribution and citation, read from their own pages. It is the reason this
record does not restate those terms.

### The adapter surface

An adapter offers four things and nothing else is expected of it:

| Operation | What it returns |
| --- | --- |
| Search | Plate records matching a query over position, epoch and plate series, in the model of decision 0003. |
| Plate | One plate record by its identifier inside this collection, with the exposures the archive records for it. |
| Scan | The bytes of one digitisation and its FITS header, for a plate and scan identifier. |
| Capabilities | What this archive provides and what it does not, as data rather than as prose: whether a world coordinate solution is present, whether photometry is provided or has to be derived here, and which plate metadata fields the archive holds at all. |

Every row any of them returns carries a non-empty `collection_id`, and the
adapter sets it. A caller cannot pass it in and cannot override it, because a
field the caller supplies is a field the caller can get wrong.

### Where archive-specific knowledge may live

Inside an adapter, and nowhere else. Scan resolution, bit depth, how the world
coordinate solution is stored, what a plate identifier looks like in this
archive, which header keywords carry the exposure and which of them this archive
spells differently: all of that is adapter-local, and a stage downstream that
needs to know one of them is a stage that is missing a field on the model.

### The one thing downstream may do with collection identity

Split, group and report by it. Never branch on it.

The two are different and the difference is the whole rule. Decision 0008 holds
out whole collections, and a report that could not say which collection a row
came from could not do that. What is refused is a stage whose arithmetic changes
because the collection is one value rather than another: a calibration with a
per-archive constant in it, a detection threshold picked by collection, a
correction applied to one archive's rows and not another's. Those belong in the
adapter, as a property of the data it returns, or in a calibration record with
its own identifier, which is what decision 0013 requires of every measurement
row anyway.

## Why

### The adapter boundary

The four disagree about almost everything, and the disagreement is not a detail
of parsing. `docs/archive-terms.md` measured one form of it: of the four, one
publishes a licence, two ask for a citation, and one did not answer that route
at all. If the four differ that much in what they say about themselves, the
assumption that they agree about how a plate identifier is spelled is not one
worth holding.

Archive-specific knowledge that leaks out of an adapter does not stay a small
conditional. It ends up in the middle of a calibration routine, where the next
archive breaks it, and where the person adding the fifth adapter has no way to
find it, because it does not look like archive code and is not in a file named
for an archive.

### Carrying the collection identifier

It is what makes distribution shift measurable rather than theoretical. A
pipeline that averages the collection away can still produce a number, and the
number will be wrong in exactly the way this board exists to catch: high on the
data it was fitted to, and not survivable on the next archive.

The reason the field is mandatory rather than recommended is that its absence is
undetectable afterwards. A magnitude with no collection on it cannot be
attributed to one later by inspection, so a stage that drops the field destroys
information that no downstream repair recovers.

### Capabilities as data

An adapter that reports what it lacks lets a stage refuse cleanly. An adapter
that does not forces every stage to discover an absence by failing on it, and
the failure arrives as a missing key in the middle of a run rather than as a
statement before it. It also gives issue #44's offline mode something to report
that is not a guess.

## What was rejected

Normalising every archive into one format at ingest and forgetting where a row
came from. It produces cleaner-looking code and it destroys the only signal that
says a model has learned one telescope's emulsion rather than the sky.

A single configurable adapter driven by a per-archive table. It looks like the
same thing with less code, and it holds only until the first archive whose
difference is behavioural rather than a value: a service that pages its results,
one that requires a second request for the scan, one that answers with a
different identifier than the one it was asked about. At that point the table
grows a code path and the boundary is gone with nothing left to enforce it.

Making the collection identifier optional, filled in where it is known. An
optional field is absent on the rows that matter, because the rows where it went
missing are the rows a bug produced.

## The condition this record does not yet satisfy

The done-condition of issue #5 asks for a test: every row produced by any
adapter carries a non-empty collection identifier, and the test fails when the
field is removed from any one adapter.

No such test exists at the commit that adds this record, and there is nothing
for it to run against:

    git ls-files src/ tests/

returns nothing. So the mandatory field above is mandatory in a document and
nothing refuses a row without it. Issue #5 stays open until the adapters in
issues #39 to #42 exist, the test exists, and it has been shown to go red when
the field is removed from one adapter rather than from all of them.
