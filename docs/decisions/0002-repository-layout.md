# 0002. Repository and package layout

Decided. Issue #3.

## The decision

Four locations, and each one is named here so that a checkout can be compared
against this record rather than against anybody's memory.

| Location | What lives there |
| --- | --- |
| `src/` | One importable package. Nothing else is importable from this repository. |
| `src/<package>/__main__.py` and the console entry point declared beside it | One command line entry point, with subcommands. |
| `tests/` | The test suite, outside the package and never inside it. |
| `docs/`, and `docs/decisions/` inside it | Documentation, and the numbered decision records. |

Decision records are numbered, and a record is superseded by a later record
rather than rewritten in place. A superseding record names the record it
replaces and the superseded record stays where it is.

The distribution name of the package, and whether it is published anywhere at
all, is entry 7 of issue #1. It is the maintainer's and this record does not
assume an answer to it. What is fixed here is that the importable code sits
under `src/`, not what the thing is called on an index.

## Why

### The `src/` directory

Without it, a test suite imports the working tree. The working tree contains
files that are not in the package: files that were never added to git, files
excluded by the packaging configuration, and files that exist only because
somebody generated them once. A suite that imports the working tree passes on
all of them, and the package that ships is missing whichever of them nobody
noticed. The failure is silent, it is not visible in a green run, and the place
it surfaces is an operator's machine.

With the package under `src/`, the import that the suite performs is the import
of an installed package, so the thing under test and the thing that ships are
the same set of files.

### One entry point with subcommands

The stages of this pipeline compose. Reading a plate, estimating the
characteristic curve, detecting, calibrating and writing measurement rows are
steps that run in sequence and hand each other files. Several separate scripts
make that sequence a thing an operator has to assemble, and the assembly is
where a stage gets skipped without anybody noticing which one.

One verb with subcommands also gives every stage a single place to print what it
did and, more importantly, what it did not do. Decision 0012 requires a harness
that is named for what it needs; the same requirement applies to a run, and a
run that covered less than it was asked for has to be able to say so in one
place rather than in as many places as there are scripts.

### Tests outside the package

Tests inside the package ship to the operator, which means the package's
dependency set has to carry whatever the tests import, or the shipped package
contains modules that fail to import. Both are worse than putting the suite in a
directory that is not packaged.

### Records are append-only

The reason a choice was made is the part that goes missing first. A record
edited to match a later choice destroys the evidence that the earlier choice was
ever held, and with it the ability to tell a decision that was revisited from
one that was quietly abandoned. The two look identical in the tree once the
earlier text is gone, and they are opposite statements about how carefully this
board works.

Numbering is what makes superseding possible without editing. A later record can
name an earlier number; an unnumbered document can only be replaced.

## What was rejected

A flat layout with the package at the repository root. It is one directory
fewer and it is the layout the silent-shipping failure above comes from.

Tests inside the package, discovered from the installed location. It makes the
suite runnable against an installed artefact, which is a real property, and it
buys that by shipping the suite. The same property is available by installing
the package and pointing the runner at `tests/`.

Rewriting a decision record when the decision changes. Cheaper to read, because
there is only ever one text. What it costs is the entire reason the records
exist.

## What this record does not settle

Whether the transcription component is a second distributable, a second package
from this repository, or a separate repository is entry 4 of issue #1, and it is
open. Decision 0010 is the record that will hold the module boundary once that
entry is answered.

This matters to the layout above, because one of the three answers puts a second
package next to the first one under `src/` and another puts it in a different
repository. The layout recorded here holds one importable package, which is what
the tree holds today. Where entry 4 is answered in a way that changes that, this
record is superseded by a later one rather than edited, which is the rule it
just set for itself.

## The condition this record does not yet satisfy

The done-condition of issue #3 asks for more than this record. It asks that a
checkout match it: the package under `src/`, tests outside it, and
`docs/decisions/` holding at least this record and the language record.

Half of that holds at the commit that adds this record. Both records are
present:

    git ls-files docs/decisions/0001-implementation-language-and-toolchain.md docs/decisions/0002-repository-layout.md
    docs/decisions/0001-implementation-language-and-toolchain.md
    docs/decisions/0002-repository-layout.md

The other half does not. There is no package and no suite:

    git ls-files src/ tests/

returns nothing. So the four locations are named and two of them are empty
directories that do not exist. Issue #3 stays open until the skeleton in issue
#17 lands and a checkout can be compared against the table above.
