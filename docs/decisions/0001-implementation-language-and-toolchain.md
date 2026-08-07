# 0001. Implementation language and toolchain

Decided. Issue #2.

## The decision

The implementation language is Python, with a declared minimum version of
3.12. The toolchain is one lock-capable installer, one formatter and linter,
one type checker run in strict mode, and one test runner. No second
implementation language is added at birth.

The named tools, each with the reason it fits this repository:

| Role | Tool | Why it fits |
| --- | --- | --- |
| Language | Python, minimum 3.12 | Everything this board reads is already Python-shaped: FITS and WCS handling, the Virtual Observatory client stack, source extraction, and every framework that could do the segmentation work. |
| Installer and resolver | `uv` | It resolves, locks and installs from one tool, so the pinned graph and the installed graph come from the same file rather than from two mechanisms that can disagree. It is already the installer the workflow tree invokes, so this adds no runtime the repository does not carry. |
| Formatter and linter | `ruff` | One tool covers both roles, so formatting and lint cannot disagree about the same line, and it exits non-zero on a violation, which is what a required check needs. |
| Type checker | `mypy`, run with `--strict` | Strict mode refuses an untyped definition rather than passing it silently, so a function that loses its annotations reds the gate instead of quietly leaving the checked set. |
| Test runner | `pytest` | It exits non-zero on failure, it carries the marker scheme the gated and non-gated suites are separated by, and it is what the numeric and astronomy libraries this board depends on are themselves tested with. |

## Why

Choosing a compiled language here does not buy speed. It buys a
reimplementation of FITS, WCS, VOTable and TAP before a single plate is read,
and those are exactly the parts where a subtle bug produces a plausible wrong
number rather than a crash.

The properties this repository has to be able to refuse are all reachable in
this means. A failing check is an exit code from a runner that a required check
can name. A proof that a guard bites is a test that fails when the guard is
removed. A claim in an issue can carry the command that produced it, because
every stage of this toolchain has a command.

The cost is real and is paid knowingly. This runtime brings a dependency graph
that is large, mutable, and a supply chain surface. That is why the lock file
and hash-pinned installs are part of this decision rather than a later nicety,
and why the dependency floor is a separate gated job.

## What was rejected

A compiled language for the whole pipeline. It would have forced first-party
FITS, WCS and Virtual Observatory clients, which is a large amount of work
whose only output is parity with libraries that already exist and are already
tested against real archives.

A split, with numeric kernels in a compiled language from day one. Rejected for
now because the numeric stack already drops into compiled code underneath, and
adding a second language before a measurement shows it is needed adds a build
system, a cross-compilation matrix and a second set of gates for no measured
gain. A measurement reopens this, a preference does not.

## What is a claim rather than a measurement

The minimum version is 3.12 because the scientific stack this board depends on
is expected to ship wheels for it across the platforms an operator will use for
the life of the first release. That is a claim about an ecosystem outside this
repository and no command in this tree produces it. It becomes a measurement
when the resolved dependency graph lands and the resolution either succeeds on
3.12 or does not.

## The condition this record does not yet satisfy

The versions named here and the versions `pyproject.toml` declares have to
match, and a reader checks that by opening both files. At the commit that adds
this record, `pyproject.toml` does not exist:

    git ls-files pyproject.toml

returns nothing. So that half of the condition is unmet rather than satisfied,
and issue #2 stays open until the file exists and the two agree.
