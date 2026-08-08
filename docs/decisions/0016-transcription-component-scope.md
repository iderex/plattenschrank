# 0016. The scope and the two output formats of the transcription component

Decided. Issue #54.

## The decision

The transcription component reads photographs of plate envelopes and of
observing logbook pages. It writes two things, and they are separate artefacts
rather than two views of one.

### What it reads

Scans of plate envelopes and of ruled logbook pages, as images. It does not read
the plate itself. Everything it produces is a claim about what a person wrote on
paper, never a measurement of the sky.

### The first output: the page description

The page description is a PAGE XML document, in the schema published by PRImA at
`https://www.primaresearch.org/schema/PAGE/gts/pagecontent/2019-07-15/`. It
carries the regions found on the page, the text lines inside them, a
transcription per line, and a confidence per line.

The confidence is not an extension this board invents. The schema carries it:

    curl -sS https://www.primaresearch.org/schema/PAGE/gts/pagecontent/2019-07-15/pagecontent.xsd \
      | grep -n 'name="conf"'
    343:		<attribute name="conf" type="pc:ConfSimpleType">
    483:		<attribute name="conf" type="pc:ConfSimpleType">
    758:		<attribute name="conf" type="pc:ConfSimpleType">
    1333:		<attribute name="conf" type="pc:ConfSimpleType">
    2093:		<attribute name="conf" type="pc:ConfSimpleType">
    2358:		<attribute name="conf" type="pc:ConfSimpleType">

and the one on `TextEquivType`, at line 758, is documented in the schema itself
as "OCR confidence value (between 0 and 1)".

This is the output an archive wants and the output a correction interface edits.
It is written whether or not any field was extracted from it, because a page
that yielded no usable metadata is still a transcribed page and the archive
still wants it.

### The second output: the structured extraction

The structured extraction is a JSON document validated against a JSON Schema
carried in this repository. One document per page.

Its fields are the ones the pipeline needs from an envelope or a logbook page:
plate identifier, date, exposure time, plate centre, emulsion, filter, telescope
and observer.

Every field carries three things and not one:

- the value,
- a reference to the line in the page description it was read from,
- a confidence.

A field that could not be read is absent, with the reason recorded, rather than
present and empty. An absent field and a field read as empty are different
statements and a consumer cannot tell them apart if they are written the same
way.

### The rule the validator enforces

An extraction whose field carries a value and no source-line reference is
refused. There is no configuration under which it is accepted, because a value
with no line behind it is exactly the thing this component exists not to
produce.

### What these fields are, and what they are not

The field list here overlaps the plate and exposure fields defined in
`docs/decisions/0003-data-model.md`, and the two lists are not the same thing.
This output is what a person appears to have written. The model's fields are
what the pipeline holds to be true about a plate. Nothing here populates a plate
record directly; a separate, deliberate step does that, and it is the step where
a confidence becomes a decision.

That separation is why the structured extraction is its own document with its
own schema rather than a partially filled plate record. A partially filled plate
record is indistinguishable from a plate record, and the first consumer to
receive one will treat it as one.

### The means

Two formats rather than one, and neither is this repository's invention.

PAGE XML for the page description, because it is what the tools an archive
already uses read and write, and because adopting an existing layout schema is
what stops the correction loop needing software from this board. Its cost is an
XML dependency in a tree that is otherwise columnar and tabular, and that cost is
paid knowingly, once, at the boundary where somebody else's tool has to read the
file.

JSON with a JSON Schema for the structured extraction, because the artefact is
one small nested document per page rather than a bulk table, and because the
refusal this record requires is a schema validation rather than a column
constraint. The columnar format named in `docs/decisions/0003-data-model.md` is
for bulk measurement output and would carry a per-page nested document badly.

## Why

Two outputs rather than one, because they have two audiences that want different
things and would each be worse served by a compromise. An archive wants the page,
with its layout, so a person can check and correct it. The pipeline wants eight
fields and does not care where on the page they were.

The source-line reference is the join between them, and it is what makes a
correction cheap. A wrong exposure time is traced to the line that produced it,
corrected once in the page description, and the extraction is regenerated.
Without it the same error is corrected in two places, or in one place and not the
other.

Confidence per line and per field is required rather than optional because
handwriting from this period will not be read reliably. A metadata field the
pipeline trusts blindly becomes a systematic error in every measurement derived
from that plate, and the error is invisible: a plate dated 1923 instead of 1928
produces numbers that are wrong and plausible.

Declining to answer is a first-class outcome for the same reason. A component
that says it cannot read a field costs a person half a minute. A component that
guesses costs a wrong measurement nobody finds.

## What personal data this creates

`docs/personal-data-inventory.md` holds entry 2 for exactly this component: the
same observer names that are already in the scanned image, turned into an
indexed text field. That entry states that the conversion is this project's own
act rather than the archive's, because a name in an image is found by somebody
already looking at that plate and a name in an index is found by anybody who
searches for it.

The observer field decided above is the field that performs that conversion. It
is kept in the list because the pipeline needs to know who observed, and it is
named here so that the operator's assessment is made against a field that
declares itself rather than against one discovered later.

## What was rejected

One combined output carrying both the layout and the extracted fields. It makes
the archive's artefact depend on the pipeline's field list, so every field the
pipeline adds changes the file an archive is asked to store, and it makes the
correction interface responsible for a schema it has no interest in.

Extraction without a source reference, with the fields written straight from the
recogniser. It is smaller and it removes the only route by which a wrong value
can be corrected once instead of every time it is used.

A confidence on the page description alone, with the extracted fields carrying
none. A field can be assembled from more than one line, and a field can be
rejected by a rule even where every line behind it was read confidently, so the
two confidences are different numbers and collapsing them loses the one the
pipeline needs.

## The condition this record does not yet satisfy

The done-condition of issue #54 asks for more than this record. It asks that a
schema for each output exists, and that a validator refuses an extraction whose
field has no source reference, proved by a test.

Neither exists at the commit that adds this record:

    git ls-files src/ tests/

returns nothing. So the refusal above is stated in a document and nothing refuses
it. Issue #54 stays open until the schemas and the validator exist and the test
has been shown to go red when the refusal is removed.
