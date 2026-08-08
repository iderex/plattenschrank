# Contributing

Every rule below is followed by one of two lines. Either the name of the check
that refuses a violation, or a sentence saying no check does. There is no third
kind, and a rule with nothing under it is a defect in this document.

Read the second kind carefully. Most of the rules here are of that kind today,
and a reader who assumes a machine is watching them will be wrong.

One section states no rule and therefore carries no such line: the table of what
the checks that exist actually do.

## The gate

There is no gate command yet.

The toolchain is decided in `docs/decisions/0001-implementation-language-and-toolchain.md`:
`uv` to resolve and install, `ruff` to format and lint, `mypy --strict` to type
check, `pytest` to run the suite. None of them is wired to anything in this
repository, because there is no package for them to run against:

    git ls-files src/ tests/
    (no output)

The job whose name a ruleset could require is issue #19, the formatting and lint
gate is #20, the type checking is #21, and the harness the suite runs under is
#22. Until those land, running a formatter or a type checker here checks nothing,
and a green result from one of them is a statement about an empty set.

**No check refuses this.** There is no gate command for a check to run, and the
ruleset requires no status check at all:

    gh api repos/iderex/plattenschrank/rulesets/20519975 \
      --jq '[.rules[].type]'
    ["deletion","non_fast_forward","pull_request"]

`required_status_checks` is absent from that list. The five workflows on this
repository run and report, and none of them can stop a merge.

## What the checks that exist actually do

Five workflows run. Each one reports a result and none of them gates:

| Check name | What it does |
| --- | --- |
| `DCO sign-off` | Reads the commits on a pull request for a `Signed-off-by` line. |
| `Reject Trojan Source Unicode` | Greps the tracked tree for bidirectional and invisible Unicode control characters. |
| `Audit workflows (zizmor)` | Audits the workflow files themselves. |
| `dependency-review` | Compares the dependency diff of a pull request against the advisory database. |
| `Scorecard analysis` | Scores the repository's supply chain posture. It is the one that does not run on a pull request: its triggers are a weekly schedule, a push to `main`, and a change to the branch protection rule. |

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

**No check refuses this.** There is no suite yet, and no mechanism is planned
that could judge whether a proof of this kind was run.

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

A fixture is synthetic. The generator every gated test draws from is issue #25,
and it exists so that a test that needs a plate does not need an archive.

No archival image is added to this repository. That is not a decision about
whether archival images may be redistributed as test fixtures, which is entry 3
of issue #1 and is the maintainer's. It is the only position available while that
entry is open, because adding one would answer it.

A test that needs a real plate belongs to a harness named for what it needs, and
never to the gated set. That naming rule is
`docs/decisions/0012-headless-and-cpu-by-default.md` and the harnesses are issue
#29.

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

**No check refuses this.** The marker scheme that would separate the gated set
from the named harnesses is issue #22 and does not exist, so today there is no
selection to enforce and nothing to enforce it with.

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
