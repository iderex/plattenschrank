# Gate parity

The target for this board's gate is the gate on `iderex/jellyfin-plugin-sso`,
a public repository. This document holds one row per check that gate requires,
resolved either to the check on this board that answers it or to a deviation
with its reason, and then the additions this subject needs that the target does
not have.

## What each gate requires today

Read on 2026-08-07.

    gh api repos/iderex/jellyfin-plugin-sso/rulesets/18802863 --jq '[.rules[] | select(.type=="required_status_checks") | .parameters.required_status_checks[].context]'
    ["build","ABI floor build","Package (JPRM) / Build package","Package (JPRM) / Generate SBOM","CodeQL","Analyze (csharp)","DCO sign-off","Deterministic PR-hygiene checks","Enforce greppable invariants","Reject Trojan Source Unicode","Audit workflows (zizmor)","prettier","dependency-review"]

    gh api repos/iderex/plattenschrank/rulesets/20519975 --jq '[.rules[].type]'
    ["deletion","non_fast_forward","pull_request"]

Both gates move, so re-run the two commands rather than trusting the output
pasted here.

## The state this table opens with

Four of the thirteen contexts already have a check of the same name running in
this tree, and no check on this repository is required by anything. The second
command above is the whole reason: this repository's ruleset carries deletion,
non-fast-forward and pull-request rules, and no required status checks. The same
jq that produced the thirteen contexts returns an empty list here.

    gh api repos/iderex/plattenschrank/rulesets/20519975 --jq '[.rules[] | select(.type=="required_status_checks") | .parameters.required_status_checks[].context]'
    []

A check that runs and gates nothing is the case a reader most often misreads, so
it is stated here first rather than left to be inferred from the table. Every
row below that says a check exists here means the check runs on a pull request
and blocks no merge.

## The thirteen rows

| Target context | Answer on this board | Reasoning |
| --- | --- | --- |
| `build` | Not yet. Owed by #19. | The one check every other row leans on. Nothing compiles or runs here yet, so there is no job to name. |
| `ABI floor build` | Deviation. Becomes a dependency floor check, owed by #26. | The target is a plugin inside a host and has to keep working against the oldest host it claims. There is no plugin host here. The equivalent risk is a dependency resolved higher than the floor the manifest declares, so the floor being tested is the dependency floor. |
| `Package (JPRM) / Build package` | Deviation. Becomes the checksummed artefact build, owed by #76 with its check owed by #34. | JPRM packages a plugin for a host that installs plugins. This board ships an artefact an operator installs directly, so the packaging step exists and the tool does not. |
| `Package (JPRM) / Generate SBOM` | Becomes a bill-of-materials check, owed by #34. | The property is the same on both boards: a released artefact declares what is inside it. Only the packaging tool that emits it differs. |
| `CodeQL` | A single analysis job, owed by #33. | The property is static analysis published to the code scanning tab. |
| `Analyze (csharp)` | Folded into the same single analysis job, owed by #33. | The target carries two analysis contexts because it has two languages under analysis. This board has one implementation language by decision 0001, so one job covers it and a second context would name nothing. |
| `DCO sign-off` | Exists here under the same name. | Runs on every pull request and gates nothing. The certificate it points at is absent, which is #30, and whether a certificate is the right instrument here at all is entry 8 of #1. |
| `Deterministic PR-hygiene checks` | Not yet. Owed by #33. | Nothing here checks that a pull request body is non-empty, names an issue, or carries no merge commit from the default branch. |
| `Enforce greppable invariants` | Not yet. Owed by #33. | The invariants this board can state today are a hard-coded absolute path from a developer machine, a credential-shaped literal, and a test asserting against a network host. |
| `Reject Trojan Source Unicode` | Exists here under the same name. | Runs on every branch and every pull request, and gates nothing. |
| `Audit workflows (zizmor)` | Exists here under the same name. | Runs on every pull request, and gates nothing. |
| `prettier` | Deviation. Becomes formatting of the implementation language, owed by #20. | `prettier` formats the target's web assets. There are no web assets here, so the formatting check covers the implementation language instead, which on this board is `ruff format` under decision 0001. |
| `dependency-review` | Exists here under the same name. | Runs on every pull request, and gates nothing. |

## Additions this subject needs

The target gate does not carry these, and it has no reason to. They come from
what this board is doing rather than from parity.

| Addition | Reason | Owed by |
| --- | --- | --- |
| A determinism check | Decision 0013 says the same input through the same version produces byte-identical output. That promise is worth nothing until a check runs a fixture twice and compares. | #14 |
| A headless check | The default suite has to run with no display, so an operator with a scanner and a workstation is not blocked by a test that wanted a window. | #23 |
| An offline check | Nothing is to leave the host by default, which is the decision #15 records. A suite that quietly reaches the network passes on a runner that has one and fails in the place this software is meant to run. | #24 |
| A coverage bar on the arithmetic that reaches a published number | A number this pipeline publishes can be wrong without anything crashing, which is the whole subject of this board. The bar is aimed at the arithmetic behind published numbers rather than at the repository as a whole, because a repository-wide percentage is met by testing the parts that are easy to test. | #28 |

## The list proposed for the ruleset

Changing a repository setting is not this board's act. What follows is the exact
list, ready to apply, and it is derived from check runs observed green on a
merged pull request rather than from the workflow files. A check that has never
run green cannot be required, because requiring it blocks every merge including
the one that would fix it.

| Check-run name | Observed green on |
| --- | --- |
| `DCO sign-off` | [run](https://github.com/iderex/plattenschrank/actions/runs/31216128525/job/92989964796) on the head of merged pull request #81 |
| `Reject Trojan Source Unicode` | [run](https://github.com/iderex/plattenschrank/actions/runs/31216128544/job/92989965763) on the head of merged pull request #81 |
| `Audit workflows (zizmor)` | [run](https://github.com/iderex/plattenschrank/actions/runs/31216128510/job/92989964699) on the head of merged pull request #81 |
| `dependency-review` | [run](https://github.com/iderex/plattenschrank/actions/runs/31216129759/job/92989968010) on the head of merged pull request #81 |

Two notes for whoever applies it.

`Reject Trojan Source Unicode` is produced twice on the same commit, once by the
push trigger and once by the pull-request trigger, because the guard declares
both:

    gh api repos/iderex/plattenschrank/commits/6735f48/check-runs --jq '[.check_runs[] | select(.name=="Reject Trojan Source Unicode") | .conclusion]'
    ["success","success"]

Which of the two a required context binds to, or whether it binds to both, is
not measured here and no command in this repository answers it. Check it before
applying the list, because the answer decides whether one green run is enough.

There is also a check run named `zizmor` on these commits. It is the
code-scanning analysis produced by the SARIF upload, not a workflow job, and its
upload step is deliberately allowed to fail without failing the gate. It is not
in the list above for that reason: requiring it would make a merge depend on a
step that is permitted to fail.

Every other check-run name in the two tables above is absent from this list,
because none of them has ever run.

## No check is required by the ruleset

As of the commands at the top of this document, no check run is required before
a merge on this repository. Every check named above runs and refuses nothing.
The protection this repository was born with is that pull requests are required,
deletion and non-fast-forward are refused, and there is no bypass actor.

That sentence stays here until the ruleset carries a required list, which is
tracked in #36 and is a maintainer act.
