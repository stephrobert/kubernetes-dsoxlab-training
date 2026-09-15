# Contributing to kubernetes-dsoxlab-training

**Language:** [English](./CONTRIBUTING.md) · [Français](./CONTRIBUTING.fr.md)

This repository is a **lab catalogue** consumed by the
[`dsoxlab`](https://github.com/stephrobert/dsoxlab) CLI. Contributions are new
labs and fixes. The CLI lives in its own repository: do not add engine code
here, and if you hit a limit of the engine, open an issue there rather than
working around it locally.

## Setting up

```bash
uv tool install dsoxlab        # the CLI, an external tool
git clone https://github.com/stephrobert/kubernetes-dsoxlab-training.git
cd kubernetes-dsoxlab-training
ansible-galaxy collection install -r requirements.yml
pre-commit install --install-hooks
dsoxlab doctor                 # check the environment
```

## The non-negotiable rule: a lab is proven in both directions

A passing test proves nothing until you have seen **fail** what must fail. A lab
whose tests pass **before** the work measures nothing, and that is the costliest
defect in this field precisely because it shows up no other way.

```bash
python3 scripts/valider-labs.py --lab <id>
```

The validator photographs the cluster, sets the initial state, checks that the
tests return **0**, plays the trainer's solution, checks that they return
**100**, cleans up, replays, cleans up again, then compares the cluster to its
photograph. A forgotten namespace, a `ClusterRole`, a taint or a CoreDNS left at
zero replicas turns the lab **RED**: it is not that lab that would pay the
price, it is the next one. Every lab's verdict is recorded in
[`validation-labs.json`](validation-labs.json), and the README catalogue carries
its date.

The two mechanical checks below say **nothing** about whether a lab is correct,
but they refuse a non-conforming lab before a human reads it:

```bash
dsoxlab validate-structure                       # the declarative contract
python3 scripts/check-labs-completude.py --check # what is left to do
```

## Tests read the state of the system, never the commands typed

The candidate reaches the result by whatever path they choose. So we query the
cluster and the node, not a history.

```python
# NO: re-reading what the learner typed
assert "apparmor_parser" in history

# YES: querying the real state
profiles = json.loads(host.run("sudo aa-status --json").stdout)["profiles"]
assert profiles["k8s-refuser-ecriture"] == "enforce"
```

One test per claim, **including one that really proves something**. Checking
that a profile is loaded and that a Pod declares it does not prove the
confinement acts: an empty profile would pass. A lab's last test must exercise
both sides, what is forbidden and what remains allowed.

## Anatomy of a lab

```text
labs/<exam>-<subject>/
├── lab.yaml                          # the contract: level = blueprint domain,
│                                     # doc_url = the companion lesson
├── lab.fr.yaml                       # French override of title and description ONLY
├── scenario.md / scenario.fr.md      # the situation and the goal, not the solution
├── README.md / README.fr.md          # the lab's fact sheet
├── setup.yaml                        # sets the initial state, includes the foundation
├── cleanup.yaml                      # undoes the lab, LEAVES the cluster in place
├── fixtures/prepare.sh               # the situation, cluster side
└── challenge/
    ├── hints.yaml                    # base64 hints, bilingual, increasing cost
    ├── solution.sh                   # the trainer's solution, replayable
    └── tests/test_functional.py      # the proof: the cluster's state
```

`dsoxlab new lab <id> --runtime vm` creates the skeleton. The identifier follows
`<exam>-<subject>`, lowercase: `cks-apparmor-confiner-un-pod`.

`level` repeats the **official blueprint domain** word for word
(`troubleshooting`, `system-hardening`, `workloads-scheduling`…): that is what
lets the repository answer the only question that drives it, "how many exam
competencies can I actually demonstrate?".

`doc_url` points at the blog lesson the lab puts to the test. A lab with no
companion lesson is a lab that teaches instead of testing, and teaching is the
site's job.

## Two languages, English first

Everything the learner reads exists in both languages, English being the file
without a suffix:

| Content | English | French |
| --- | --- | --- |
| Lab title and description | `lab.yaml` | `lab.fr.yaml` (these two keys only) |
| Situation | `scenario.md` | `scenario.fr.md` |
| Fact sheet | `README.md` | `README.fr.md` |
| Hints | `text_en` | `text_fr` |
| Governance | `SECURITY.md`, … | `SECURITY.fr.md`, … |

`dsoxlab validate-structure` reports `content_missing_english` when a document
is translated on one side only: a half-translated lab does not pass.

Two things stay in French and it is deliberate: the **assertion messages** of
the tests, and the **comments** in playbooks and scripts. The former teach at
the moment a test fails and the sibling Linux catalogue keeps them in French
too; the latter are addressed at whoever maintains the lab.

## Four traps, each cost a validation cycle

They are checked by `tests/test_pieges_du_depot.py`, but knowing them saves you
from discovering them through a hook.

- **Every `ssh` in a solution carries `-n`.** The solution is read by `bash -s`
  from standard input: without `-n`, `ssh` swallows the rest of the script as
  its input, nothing after it runs, and the script returns 0.
- **Every `fixtures/prepare.sh` logs on the node.** dsoxlab only returns
  "non-zero return code" when a fixture script fails; without the log, the
  diagnosis starts from nothing. Copy the header of an existing lab.
- **Every `setup.yaml` includes the foundation.** There is no hook after
  provisioning: the cluster exists only because each lab installs it. A lab that
  forgets the include works as long as another lab ran before it, and fails
  alone on a fresh cluster.
- **Every namespace created is deleted on cleanup.** The cluster itself stays:
  it is the namespace that goes.

## Writing style

The blog's register: clear, pragmatic, no needless jargon.

- **No emoji, no em dash** in what the learner reads: `scenario`, `README`,
  hints, assertion messages. A hook checks it.
- **Assertion messages teach.** A failing test must say what is wrong and why,
  not only what was expected. It is often the only text the learner reads
  closely.
- `scenario.md` describes a **situation**, not a list of commands. A candidate
  gets a context and a goal, never a walkthrough.
- Hints are **base64-encoded** and **bilingual**, four of increasing cost, from
  the vaguest to the most explicit, never giving away the full YAML.

## Before opening a pull request

The hooks do the work if you installed them. By hand:

```bash
pre-commit run --all-files                       # hygiene, lint, checkers
pre-commit run --all-files --hook-stage pre-push # contract + README freshness
python3 scripts/gen_catalog.py                   # regenerate the README catalogue
```

`README.md` and `README.fr.md` must list **every** lab with its companion
lesson. The catalogue is generated from the real `lab.yaml` files: run
`gen_catalog.py` after adding or renaming a lab. Both the CI and the `pre-push`
hook refuse a stale catalogue.

## Conventions

- **Commits**: messages in French, a factual subject line saying what changed
  and why, no conventional prefix. The body tells what was **measured**,
  including measurements discarded along the way: they are often worth more than
  the result.
- **A dedicated branch**, a clear description, and the lab played in both
  directions before asking for review.

## Security

Vulnerabilities are reported privately, never through a public issue: see
[`SECURITY.md`](SECURITY.md).
