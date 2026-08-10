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

Eight of the thirteen contexts already have a check of the same name running in
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
| `build` | Exists here under the same name. | The one check every other row leans on. It installs the locked graph, formats and lints, type checks in strict mode, runs the gated suite, and audits the installed graph. It gates nothing, like every other check here. |
| `ABI floor build` | Deviation. Becomes the `dependency floor` check run, which exists here. | The target is a plugin inside a host and has to keep working against the oldest host it claims. There is no plugin host here. The equivalent risk is a dependency resolved higher than the floor the manifest declares, so the floor being tested is the dependency floor. |
| `Package (JPRM) / Build package` | Deviation. Becomes the `package` check run, which exists here. The artefact an operator downloads is still owed by #76. | JPRM packages a plugin for a host that installs plugins. This board ships an artefact an operator installs directly, so the packaging step exists and the tool does not. What runs here builds both distributions on every pull request, installs the wheel into an environment holding nothing else, and runs the entry point out of it. |
| `Package (JPRM) / Generate SBOM` | Becomes the `bill of materials` check run, which exists here. | The property is the same on both boards: a released artefact declares what is inside it. Only the packaging tool that emits it differs. The document is CycloneDX, generated from the environment the wheel was installed into rather than from `pyproject.toml`, because the manifest carries ranges and only a resolved version can be matched against an advisory. |
| `CodeQL` | Exists here under the same name, and it is not a workflow job. | It is the code-scanning result of the analysis job in the row below, arriving under the category that job declares. It appeared on the pull request that added the job and did not appear on a push to a branch with no pull request open, which is where a reader looking for it on a scratch branch will not find it. |
| `Analyze (csharp)` | Deviation. Becomes the `Analyze (python)` check run, which exists here. | The target carries two analysis contexts because it has two languages under analysis. This board has one implementation language by decision 0001, so one job covers it and a second context would name nothing. The job reports whether or not it finds anything: it reds when the analysis cannot run, and a finding travels to `CodeQL` above instead. Whether a finding blocks anything is a repository setting rather than a workflow, which puts it beside #36. |
| `DCO sign-off` | Exists here under the same name. | Runs on every pull request and gates nothing. The certificate it points at is absent, which is #30, and whether a certificate is the right instrument here at all is entry 8 of #1. |
| `Deterministic PR-hygiene checks` | Exists here under the same name. | Four properties decided from the pull request's own metadata: the body is not empty, the body names an issue, the head branch is not the default branch, and the commit set carries no merge commit. Each runs against a case that must trip it and a near miss that must not before it runs against the pull request. Nothing here reads a commit message or compares a change against a `Scope:` line, and that set is as unenforced as it was. |
| `Enforce greppable invariants` | Exists here under the same name. | Three invariants: an absolute path out of a developer's home directory, a credential-shaped literal, and a test naming a network host outside loopback and the names reserved for documentation. `git grep -P` is the matcher, as in `Reject Trojan Source Unicode`, rather than the scanner binary the target fetches at run time. What each pattern does not reach is written at the pattern. |
| `Reject Trojan Source Unicode` | Exists here under the same name. | Runs on every branch and every pull request, and gates nothing. |
| `Audit workflows (zizmor)` | Exists here under the same name. | Runs on every pull request, and gates nothing. |
| `prettier` | Deviation, and answered by a leg of `build` rather than by a check run of its own. | `prettier` formats the target's web assets. There are no web assets here, so the formatting check covers the implementation language instead, which on this board is `ruff format` under decision 0001. It runs beside `ruff check` in the `Format and lint` leg, so a ruleset requiring it requires `build` and there is no separate context to name. |
| `dependency-review` | Exists here under the same name. | Runs on every pull request, and gates nothing. |

## Additions this subject needs

The target gate does not carry these, and it has no reason to. They come from
what this board is doing rather than from parity.

| Addition | Reason | Owed by |
| --- | --- | --- |
| A determinism check | Decision 0013 says the same input through the same version produces byte-identical output. That promise is worth nothing until a check runs a fixture twice and compares. | #14 |
| A headless check | The default suite has to run with no display, so an operator with a scanner and a workstation is not blocked by a test that wanted a window. | #23 |
| An offline check | Nothing is to leave the host by default, which is the decision #15 records. A suite that quietly reaches the network passes on a runner that has one and fails in the place this software is meant to run. | Landed. The refusal is in `tests/conftest.py` and runs inside the suite leg of `build` rather than as a check of its own, so there is no separate context to name. |
| A coverage bar on the arithmetic that reaches a published number | A number this pipeline publishes can be wrong without anything crashing, which is the whole subject of this board. The bar is aimed at the arithmetic behind published numbers rather than at the repository as a whole, because a repository-wide percentage is met by testing the parts that are easy to test. | #28 |

## The list proposed for the ruleset

Changing a repository setting is not this board's act. What follows is the exact
list, ready to apply, and it is derived from check runs observed green on a
merged pull request rather than from the workflow files. A check that has never
run green cannot be required, because requiring it blocks every merge including
the one that would fix it.

| Check-run name | Observed green on |
| --- | --- |
| `build` | [run](https://github.com/iderex/plattenschrank/actions/runs/31292783258/job/93192746989) on the head of merged pull request #105 |
| `dependency floor` | [run](https://github.com/iderex/plattenschrank/actions/runs/31292958791/job/93193233070) on the head of merged pull request #105 |
| `DCO sign-off` | [run](https://github.com/iderex/plattenschrank/actions/runs/31216128525/job/92989964796) on the head of merged pull request #81 |
| `Reject Trojan Source Unicode` | [run](https://github.com/iderex/plattenschrank/actions/runs/31216128544/job/92989965763) on the head of merged pull request #81 |
| `Audit workflows (zizmor)` | [run](https://github.com/iderex/plattenschrank/actions/runs/31216128510/job/92989964699) on the head of merged pull request #81 |
| `dependency-review` | [run](https://github.com/iderex/plattenschrank/actions/runs/31216129759/job/92989968010) on the head of merged pull request #81 |
| `package` | [run](https://github.com/iderex/plattenschrank/actions/runs/31306494130/job/93227605187) on the head of merged pull request #110 |
| `bill of materials` | [run](https://github.com/iderex/plattenschrank/actions/runs/31306494130/job/93227605172) on the head of merged pull request #110 |
| `CodeQL` | [run](https://github.com/iderex/plattenschrank/runs/93343754717) on the head of merged pull request #120 |
| `Analyze (python)` | [run](https://github.com/iderex/plattenschrank/actions/runs/31351744124/job/93343761433) on the head of merged pull request #120 |
| `Deterministic PR-hygiene checks` | [run](https://github.com/iderex/plattenschrank/actions/runs/31351744164/job/93343761724) on the head of merged pull request #120 |
| `Enforce greppable invariants` | [run](https://github.com/iderex/plattenschrank/actions/runs/31351744169/job/93343761813) on the head of merged pull request #120 |

`build` was also green on the heads of merged pull requests #103 and #104, and
`dependency floor` has existed for one merged pull request, which is #105.
`package` and `bill of materials` have existed for one, which is #110. A
name is listed here after it has been green on a merged head and not before,
because requiring a check that has never run green blocks every merge including
the one that would fix it.

The last four arrived with #113. Each was green on the head of merged pull
request #114, which is the first merge after the one that added them, and again
on the heads of #119 and #120:

    gh api repos/iderex/plattenschrank/commits/f9aeabb/check-runs --jq '[.check_runs[] | select(.name | test("CodeQL|Analyze|hygiene|invariants")) | "\(.name) \(.conclusion)"] | unique'
    ["Analyze (python) success","CodeQL success","Deterministic PR-hygiene checks success","Enforce greppable invariants success"]

Twelve names now, where there were eight.

Four notes for whoever applies it.

Most of the names above are produced twice on the same commit, once by the push
trigger and once by the pull-request trigger, because their workflows declare
both. Which ones is counted rather than listed, since it follows from the
triggers and moves when they do:

    gh api repos/iderex/plattenschrank/commits/104a434/check-runs --jq '[.check_runs[].name] | group_by(.) | map({name: .[0], runs: length})'
    [{"name":"Analyze (python)","runs":2},{"name":"Audit workflows (zizmor)","runs":1},{"name":"CodeQL","runs":1},{"name":"DCO sign-off","runs":1},{"name":"Deterministic PR-hygiene checks","runs":1},{"name":"Enforce greppable invariants","runs":2},{"name":"Reject Trojan Source Unicode","runs":2},{"name":"bill of materials","runs":2},{"name":"build","runs":2},{"name":"dependency floor","runs":2},{"name":"dependency-review","runs":1},{"name":"package","runs":2},{"name":"zizmor","runs":1}]

Which of the two a required context binds to, or whether it binds to both, is
not measured here and no command in this repository answers it. Check it before
applying the list, because the answer decides whether one green run is enough.
It was written here about one name when only one had the shape, then three, then
five, and the count above is what it is today, which is why it is read rather
than restated.

`Deterministic PR-hygiene checks` has the opposite shape and it is the only name
in the list that does. Its workflow declares a pull-request trigger and no push
trigger, so it produces one run and produces none at all on a branch pushed
without a pull request open. Every other name here can be exercised on a scratch
branch; this one cannot, and a reader looking for it there will not find it.

There is also a check run named `zizmor` on these commits. It is the
code-scanning analysis produced by the SARIF upload, not a workflow job, and its
upload step is deliberately allowed to fail without failing the gate. It is not
in the list above for that reason: requiring it would make a merge depend on a
step that is permitted to fail. `CodeQL` is a code-scanning check run of the
same kind and is in the list, because the analysis that produces it has no step
permitted to fail. That is the difference between the two rather than a
judgement about which analysis matters more, and it is one line of the tree:

    git grep -nE '^[[:space:]]*continue-on-error:' -- .github/workflows/
    .github/workflows/zizmor.yml:77:        continue-on-error: true

Three check runs exist in this tree that the two tables above do not name, and
none of them is proposed. `Scorecard analysis` declares a weekly schedule, a
push to `main` and a change to the branch protection rule, so it never runs on a
pull request and a required context would wait for a run that does not come.
`integration (needs network)` and `integration (needs GPU)` declare a manual
trigger and a weekly schedule and nothing else, so neither reaches a pull
request either, and both are red today rather than passing on a selection that
collected nothing.

Every check-run name the two tables above resolve to is now in this list. What
is not in it is the two rows that resolve to no context of their own, `prettier`
and the offline check, and the three additions still owed by #14, #23 and #28.

## No check is required by the ruleset

As of the commands at the top of this document, no check run is required before
a merge on this repository. Every check named above runs and refuses nothing.
The protection this repository was born with is that pull requests are required,
deletion and non-fast-forward are refused, and there is no bypass actor.

That sentence stays here until the ruleset carries a required list, which is
tracked in #36 and is a maintainer act.
