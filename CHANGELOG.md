# Changelog

**Language:** [English](./CHANGELOG.md) · [Français](./CHANGELOG.fr.md)

All notable changes to this project are documented in this file. The format is
based on [Keep a Changelog](https://keepachangelog.com/), and the project
follows [semantic versioning](https://semver.org/).

## [Unreleased]

### Changed, the catalogue speaks two languages

Everything the learner reads now exists in English and in French, English being
the file without a suffix, as in the sibling Linux catalogue. That covers the
lab titles and descriptions (`lab.yaml` / `lab.fr.yaml`), the situations
(`scenario.md` / `scenario.fr.md`), the fact sheets (`README.md` /
`README.fr.md`) and the governance documents. The hints were already bilingual,
carrying `text_en` and `text_fr` side by side.

`dsoxlab validate-structure` reports `content_missing_english` for a document
translated on one side only: a half-translated lab does not pass.

Two things stay in French and it is deliberate: the **assertion messages** of
the tests, and the **comments** in playbooks and scripts. The sibling Linux
catalogue keeps its assertion messages in French too.

### Changed, provenance reaches SLSA level 3

The release workflow used to attest from its own build job, which yields
**level 2**: the process that builds the archive was also the one signing what
it said about it. The badge claimed 3 in the sibling Linux repository, and 2
here. Both now say 3, and the workflow produces it.

- `.github/workflows/attester.yml`, a reusable workflow, is now the only one in
  the repository granted `attestations: write`. It performs no `checkout`,
  receives only a name and a digest, and runs no repository code.
- `release.yml` is split into three jobs: build, attest, publish. The publish
  job writes the release but cannot attest, lacking the permission. The archive
  is re-checked against its digest before publication, so that an artifact
  altered between two jobs does not go out with provenance that does not
  describe it.
- **Two linters disagreed, and the tie was broken on the merits.** zizmor
  recommends the `uses: $/...` form, available on github.com since July 2026;
  actionlint 1.7.12, released in March, still rejects it as an invalid format.
  `$/` wins because it does not depend on the runtime filesystem state and so
  cannot load a file a previous step dropped in place. The actionlint exception
  is scoped to that one message in that one file, dated, and verified narrow by
  planting another fault in the same file: the rule still catches it.
- **The zizmor version pinned in the CI had to move too.** 1.26.1 refuses to
  load a workflow using `$/` and answers `fatal: no audit was performed`, so it
  was auditing nothing at all. 1.30.1, the latest published, is refused by the
  action itself with `Unknown version`: the action embeds its own table of known
  versions, which stops at the last one published before its own release. The
  CI now runs 1.30.0, the most recent the action accepts.

The check that proves the level is in `RELEASING.md`: it names the signing
workflow and fails if the provenance came from anywhere else.

### Added, the chain of a public repository

The repository carried a catalogue and nothing around it. It now takes up what
the sibling Linux catalogue proved out, adapted to Kubernetes.

- **Continuous integration** (`.github/workflows/ci.yml`), six gates. zizmor
  analyses the workflows, actionlint checks them and runs shellcheck over every
  `run:` block, poutine looks for CI/CD exploit chains, CodeQL reads the Python,
  a parity job replays **every** pre-commit hook, and a last one checks the
  catalogue contract with the network.
  - Every action is pinned to a full commit SHA, and the ten SHAs taken from the
    Linux repository were **verified one by one** against the tag they claim
    before being written here. Copying a pin without checking it is trusting the
    clipboard.
  - The parity job installs `ansible-core`. Without `ansible-playbook` on the
    PATH, the playbook syntax check turns into a `skip`: the job would have
    stayed green having checked nothing.
  - The companion-lesson check goes through
    `dsoxlab validate-structure --check-urls`, and is wired into no hook: an
    offline commit must not fail, and the blog being down has nothing to do with
    whether a lab is correct.
- **Six catalogue checkers** (`tests/`), wired into pre-commit. Each was proven
  by planting the defect it targets on a decoy lab: all nine planted defects are
  caught.
  - `test_pieges_du_depot.py` covers the four traps this repository has paid for
    at least once: an `ssh` without `-n` in a solution read by `bash -s`, a
    `prepare.sh` that does not log on the node, a `setup.yaml` that does not
    install the foundation, a namespace created but never deleted.
  - `test_indices.py` refuses a plaintext hint, a translation that is not one
    (`text_fr` a copy of the English), and costs that do not increase.
  - `test_style_apprenant.py` refuses emoji and em dashes in what the learner
    reads, decoded hints included.
  - `test_collections_declarees.py` includes `shared/` in its scope: the
    foundation carries the repository's only call to an external collection, and
    leaving it out would have checked half the catalogue.
  - `test_playbooks_syntaxe.py` also loads the foundation for itself: it arrives
    through `include_tasks`, which Ansible only resolves at run time, so no
    `setup.yaml` checks it.
  - `test_outillage_coherent.py` refuses a checker that exists without being
    wired: an unplugged test protects nothing, silently.
- **None of these tests redo what the engine already provides.** `dsoxlab
  validate-structure` checks broken relative links, declared fixtures and target
  consistency with `meta.yml`: a second check that drifts from the first is
  worse than none.
- **Governance**: `CONTRIBUTING`, `SECURITY`, `CODE_OF_CONDUCT`, `RELEASING`,
  this changelog.
- **Supply-chain hardening**: `.github/CODEOWNERS`, a `dependabot.yml` grouped
  into a weekly batch with a cooldown, `.poutine.yml`, `.plumber.yaml`, the
  OpenSSF Scorecard and Plumber workflows, and a release workflow that publishes
  a keyless-signed `tar.gz` bundle with its SLSA provenance.
- **Generated catalogue** (`scripts/gen_catalog.py`): the README lists the labs
  by certification, with their blueprint domain, their companion lesson and the
  date of their last validation. A hand-written catalogue goes stale in silence;
  a `pre-push` hook now refuses a stale README.

### Changed

- **`CLAUDE.md` and `todo/` are no longer versioned**, as in the sibling Linux
  repository: they are local steering. The doctrine `CLAUDE.md` carried, and
  that a contributor needs, moved into `CONTRIBUTING.md`, which is published.

### Added, the catalogue

- **37 labs ported from K8sExamLab and validated**, each played in both
  directions on a two-node kubeadm 1.37 cluster: 0 before the work, 100 after
  the trainer's solution, replayable, and leaving no trace on the cluster. The
  CKAD milestone is complete. The measurements are in `validation-labs.json`.
- **`scripts/valider-labs.py`**, which delivers that verdict. It photographs the
  cluster, plays the full cycle, then compares: a lab that leaves a namespace, a
  `ClusterRole` or a taint behind is RED, because it is the next lab that would
  pay for it. The validator was itself proven in both directions, on a
  `cleanup.yaml` stripped of its namespace deletion.
- **The two-node foundation** (`shared/kubeadm-cluster.yml`): the control plane,
  then every worker declared in `meta.yml`, prepared and joined by delegation.
  Calico replaces Flannel, which does not enforce NetworkPolicies and left four
  labs unverifiable.
