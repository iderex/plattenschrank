# 0003. The canonical data model

Decided. Issue #4.

## The decision

Four entities at the core and no more.

### Plate

The physical object. Required fields:

| Field | Meaning |
| --- | --- |
| `collection_id` | The archive the plate belongs to, never dropped and never folded into another identifier. |
| `plate_id` | Unique inside its collection, and only inside it. |
| `scan_id` | The digitisation this model is describing, because one plate can be scanned more than once. |

### Exposure

One shutter opening on a plate. A plate may carry several. Required fields:

| Field | Meaning |
| --- | --- |
| `exposure_id` | Unique inside its plate. |
| `collection_id`, `plate_id` | The plate this exposure sits on. |
| `start_time`, `duration` | When the shutter opened and for how long, where the archive records it. Absent is recorded as absent and never as zero. |

### Detection

Something found on the scan at a pixel position. Required fields:

| Field | Meaning |
| --- | --- |
| `detection_id` | Unique inside its scan. |
| `collection_id`, `plate_id`, `scan_id` | Where it was found. |
| `exposure_id` | The exposure it is attributed to, or an explicit unattributed marker where the pipeline cannot say. |
| `x`, `y` | Pixel position on the scan. |
| `detector_id` | The identifier of the detection stage that produced it. |

### Measurement

A calibrated number attached to a detection. Required fields:

| Field | Meaning |
| --- | --- |
| `detection_id` and its plate keys | The detection this number is about. |
| `quantity` | What is being measured. |
| `value`, `unit` | The number and its unit, with the unit on the row rather than in a document. |
| `uncertainty` | Carried per component rather than as one figure. |
| `calibration_id` | The calibration that produced the number. |

Every row of every entity carries `collection_id`. A row that cannot say which
collection it came from is refused rather than defaulted.

## Formats

Input is FITS with a world coordinate system.

Bulk output is Parquet, a columnar format a reader can open without this
software.

Interchange with the Virtual Observatory is a separate export step, not the
internal representation.

## Why

Plate archives break the one-image-one-exposure assumption that modern detector
tooling is built on. Several exposures on one plate, offset by design, are
common in the collections this board targets, and a model that cannot express
them either loses exposures or invents plates.

Separating detection from measurement matters for the same kind of reason. The
same detection can be measured differently by two calibrations, and if the model
cannot hold both, comparing calibrations means rerunning everything and trusting
that nothing else moved.

Output that needs this software to read it is output that dies with this
software. A columnar format any standard tool can open keeps the science
recoverable if the project stops.

The Virtual Observatory format is an export and not the internal model because
it is a wire format with its own constraints, and building the pipeline around
it would put those constraints in front of every internal decision.

## What was rejected

A single flat table of measurements. It cannot express the plate that carries
three exposures, and it pushes the collection identity into a string column that
later work then has to parse back out.

## The condition this record does not yet satisfy

The schema file the code loads has to match this record field for field, and a
reader checks that by opening both. At the commit that adds this record there is
no code and no schema file:

    git ls-files src/

returns nothing. So that half of the condition is unmet rather than satisfied,
and issue #4 stays open until the schema exists and the two agree.
