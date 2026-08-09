# Contributing

Every rule below is followed by one of two lines. Either the name of the check
that refuses a violation, or a sentence saying no check does. There is no third
kind, and a rule with nothing under it is a defect in this document.

Read the second kind carefully. Most of the rules here are of that kind today,
and a reader who assumes a machine is watching them will be wrong.

One section states no rule and therefore carries no such line: the table of what
the checks that exist actually do.

## The gate

The gate is the `build` job. Before pushing, run the legs of it that judge this
tree:

    uv sync --locked --extra test --extra typecheck --extra lint
    uv run --no-sync ruff format --check --diff .
    uv run --no-sync ruff check --no-fix .
    uv run --no-sync mypy
    uv run --no-sync pytest

That is not the whole job. One leg is left out of the list above and it is the
one that audits the installed graph against the advisory database: it needs a
network, so a contributor working offline cannot run it, and it is the leg that
can red a push which changed nothing. A second job in the same file resolves
every direct dependency down to the bound it declares and runs the suite against
that graph rather than against the lock file, so a green run above says nothing
about the floor.

Which legs exist is printed by the job rather than listed here, because a list in
this document drifts against the file that decides it:

    grep -n '^      - name:' .github/workflows/build.yml

The toolchain is decided in `docs/decisions/0001-implementation-language-and-toolchain.md`:
`uv` to resolve and install, `ruff` to format and lint, `mypy --strict` to type
check, `pytest` to run the suite. All four are wired up, and each reads its
settings out of `pyproject.toml` rather than out of a flag in the workflow, which
is what makes the answer here and the answer on a contributor's machine the same
answer.

The legs run in order and the job stops at the first one that fails, so a red is
attributable to one leg rather than to the job.

**No check refuses this.** The `build` job runs and reports, and the ruleset
requires no status check at all:

    gh api repos/iderex/plattenschrank/rulesets/20519975 \
      --jq '[.rules[].type]'
    ["deletion","non_fast_forward","pull_request"]

`required_status_checks` is absent from that list, so a red `build` reports and
does not stop a merge. Proposing the list a ruleset would require is issue #36,
and `docs/gate-parity.md` holds what it would say.

## What the checks that exist actually do

Every workflow here reports a result and none of them gates. Which ones exist is
read off the tree rather than counted in this sentence, because a count written
down is the thing that goes stale first:

    git ls-files .github/workflows/

| Check name | What it does |
| --- | --- |
| `build` | Installs the locked graph, refuses a formatting or lint failure, type checks in strict mode, runs the default suite with no display and as an unprivileged user, and audits the whole installed graph against the advisory database. |
| `dependency floor` | Resolves every direct dependency down to the lower bound it declares, installs that graph, and runs the default suite against it. It refuses to pass where the floor resolution turns out to be the locked one, because the two runs would then be the same run. |
| `DCO sign-off` | Reads the commits on a pull request for a `Signed-off-by` line. |
| `Reject Trojan Source Unicode` | Greps the tracked tree for bidirectional and invisible Unicode control characters. |
| `Audit workflows (zizmor)` | Audits the workflow files themselves. |
| `dependency-review` | Compares the dependency diff of a pull request against the advisory database. |
| `Scorecard analysis` | Scores the repository's supply chain posture. One of the three that never run on a pull request: its triggers are a weekly schedule, a push to `main`, and a change to the branch protection rule. |
| `integration (needs network)` and `integration (needs GPU)` | The harnesses for what the gate cannot cover. Manual and weekly, never on a pull request, each named for what it needs. Both are red today, because no test carries either marker and no runner here has a graphics processor, and each says that rather than passing on a selection that collected nothing. |

`docs/gate-parity.md` is where the list this board is working towards is held,
one row per check, with what is owed and by which issue.

## No work without an issue

Every change starts as an issue and lands as a pull request.

An issue says what is wrong, what the evidence is, and what "done" means. Where
the evidence is a number, it carries the command that produced it. Where a
planning issue declares a `Scope:` line, the change stays inside it.

**Refused by the ruleset for half of this, and by no check for the other half.**
A direct push to `main` is refused, because the `pull_request` rule in the output
above requires one. Nothing anywhere reads an issue body, so an issue with no
evidence and no done-condition passes everything here, and nothing connects a
pull request to an issue or compares a change against a `Scope:` line.

## Every asserted fact carries the command that produced it

A number in an issue, in a pull request body, in a commit message or in a
document is written with the command that produced it, run against the reference
the reader will have rather than against a working tree. Where a claim cannot be
backed by a command, it is written as a claim, in those words.

This board's subject makes the rule sharper than usual. A plate measurement that
is wrong is usually not absurd, it is plausible, so a number nobody can re-derive
is a number nobody can catch.

**No check refuses this.** Nothing here reads prose.

## No guard ships without proof that it bites

A test that passes proves the code did not crash. What has to be shown is that
the test goes red when the thing it guards is removed. Where a rule is added with
a test, the pull request says what was deleted to make the suite fail, and what
failed.

**No check refuses this.** The suite exists and `build` runs it, but nothing
reads whether a pull request deleted a guard and recorded the red, and no
mechanism is planned that could. What stands in its place is a branch under
`scratch/` per guard, carrying the deletion and the run it produced, linked from
the body that claims the red:

    git branch -r --list 'origin/scratch/*'

A branch there is evidence and never a proposal. None of them is merged and none
of them is meant to be.

## Sign-off

Every commit carries a `Signed-off-by` line matching its author:

    git commit -s

The certificate that line refers to is `DCO` at the root of this repository. It
is the Developer Certificate of Origin 1.1, unmodified.

**Reported by `DCO sign-off` and refused by nothing.** The check runs on every
pull request and reports a failure for a commit without the line, and because the
ruleset requires no status check, a red result does not stop the merge.

Whether a certificate is the right instrument for this repository at all, and
whether outside contributions are accepted on any terms, is entry 8 of issue #1.
It is the maintainer's and it is open.

## Commit messages and pull request bodies

A commit message says what changed and what failure the change prevents. Where it
is a correction, it says what was wrong and how it was found. One topic per
commit and one topic per pull request.

Everything about a change goes in its body. Where the body is wrong or out of
date, the body is edited rather than corrected underneath.

**No check refuses any of this.** Nothing reads a message or a body.

## Fixtures

A fixture is synthetic. The generator every gated test draws from is
`src/plattenschrank/synthetic.py`, and it exists so that a test that needs a
plate does not need an archive. Everything it produces is a function of a seed,
so a fixture is a number in a test rather than a file committed here, and a
plate that broke something can be named in an issue in four characters.

What it produces carries the failures somebody enumerated and nothing else. Its
first sentence says so, and a recovery number read off it is a statement about
arithmetic on that enumerated set rather than about plate photometry.

No archival image is added to this repository. That is not a decision about
whether archival images may be redistributed as test fixtures, which is entry 3
of issue #1 and is the maintainer's. It is the only position available while that
entry is open, because adding one would answer it.

A test that needs a real plate belongs to a harness named for what it needs, and
never to the gated set. That naming rule is
`docs/decisions/0012-headless-and-cpu-by-default.md` and the harnesses are in
`.github/workflows/integration.yml`.

**No check refuses this.** Nothing here inspects what a fixture is made of, and
`dependency-review` reads dependencies rather than files.

## The four conditions on a gated test

Headless, unprivileged, offline, processor-only. A test that needs a display, an
elevation prompt, a network or a graphics processor is not in the gated set,
and the harness that covers it carries the requirement in its name, in the form
`integration (needs network)`.

The reasoning is in `docs/decisions/0012-headless-and-cpu-by-default.md`. The
unprivileged condition is the one most often broken by accident: a test that
raises an operating system consent prompt interrupts whoever is at the machine,
and a prompt that arrives mid-task gets answered by reflex.

**Partly refused by `tests/conftest.py`, and by no check for the rest.** Every
collected test carries one of the four markers `pyproject.toml` registers, and
collection fails naming the ones that do not, which is what stops a test with a
misspelled marker leaving the gated set while it still reads as being inside it.
The default selection is `-m unit`, so a test that states another requirement is
not in the gate. The same file refuses an outbound connection attempted from the
test process, so a gated test that reaches for an archive fails here rather than
on the day the archive is down.

Two of the four conditions are established by the leg rather than assumed of the
runner. It removes both display variables for the duration of the run and exits
non-zero if it is running as root, and it prints what each was before it runs
anything, because a runner that happens to have no display today is not the same
property as a suite that cannot use one.

The fourth condition has nothing behind it. Nothing here reads a test for a
graphics processor it needs, and a test that wanted one and marked itself `unit`
would reach the gated set and pass wherever one happens to be present. The
offline half is refused in part rather than whole: the block does not reach name
resolution, a raw send, or a subprocess the suite starts, and `tests/conftest.py`
names those three in a paragraph that stays negative.

Every run prints, before its first result, which of the four sets it reached and
which it left out with what running those would need. A green `build` is a
statement about one set, and that line is what stops it being read as a statement
about the software.

## Decision records

Architecture decisions live in `docs/decisions/`, numbered, one per file, and a
record is superseded by a later record rather than rewritten in place. An edited
record destroys the evidence that the earlier choice was ever held, which makes a
decision that was revisited indistinguishable from one that was quietly
abandoned.

A record that does not satisfy the whole done-condition of its issue says so in a
closing section, and its issue stays open.

**No check refuses this.** Nothing reads the records or compares one against the
tree.

## Decisions this board does not take for itself

Issue #1 collects the questions that belong to the maintainer: the licence,
whether trained weights may be published, whether archival images may be
redistributed, whether the handwriting component is a separate distributable,
whether any shipped path may require a graphics processor, whether an annotator
identity is ever stored, the published package name, and whether outside
contributions are accepted.

No issue and no record assumes an answer to one of them. Work that needs an
answer names the entry and stops there.

**No check refuses this.** It is caught by reading, or it is not caught.

## Style

English in artefacts.

No attribution of work to a tool, and no generated-by markers, in anything
tracked.

**No check refuses either.** `Reject Trojan Source Unicode` reads the tracked
tree for control characters and nothing else about its content.
