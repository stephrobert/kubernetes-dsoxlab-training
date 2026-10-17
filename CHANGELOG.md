# Changelog

**Language:** [English](./CHANGELOG.md) · [Français](./CHANGELOG.fr.md)

All notable changes to this project are documented in this file. The format is
based on [Keep a Changelog](https://keepachangelog.com/), and the project
follows [semantic versioning](https://semver.org/).

## [0.2.0] - 2026-10-17

### Changed

- **The validator reads the contract, not the terminal panel.**
  `scripts/valider-labs.py` parsed the score out of what `dsoxlab check`
  *displays*. That panel is interface: it changed in dsoxlab 0.4.0 and the
  regex stopped finding anything. It now reads `check --json`, which carries a
  `schema`, and the reading lives in `scripts/verdict_check.py`, **identical in
  all twelve catalogs**.

- **Three verdicts, not two.** A run where every collected test skipped
  measured nothing: it is **SKIP**, neither green nor red, and it stays to be
  measured. Painting it red would accuse the lab of what is missing from the
  machine. `--check` therefore exits `10` in that case, against `1` for a RED,
  mirroring `dsoxlab doctor --strict` where 9 is repaired and 10 is remeasured.

- **The README takes the reference structure** shared by the twelve catalogs:
  fourteen sections, in both languages. Seven of them describe dsoxlab rather
  than the subject, and are therefore identical everywhere.

### Requires

- **dsoxlab 0.4.1 or later**, which introduced the `status` field of
  `check --json`. Without it the validator refuses to conclude rather than
  guessing.

## [0.1.1] - 2026-10-15

The three labs the 2026-10-12 record marked ROUGE are green, and the record now
holds sixty-four VALIDE verdicts out of sixty-four labs.

None of the three had a teaching defect: they teach what they claim, and two
even carried, in a comment, the measurement that should have protected them.
What had aged in all three cases is a value written by hand where the world had
to be read instead.

### Fixed

- **`cks-runtime-sandbox-gvisor`: the gVisor archive carries seven binaries, not
  two.** It now holds `runsc`, `containerd-shim-runsc-v1` and a `gvisor-bin/`
  directory of five binaries, including the `gvisor_sentry` that runsc requires.
  `fixtures/prepare.sh` installed only the two at the root, so runsc refused to
  create any sandbox at all. The message appeared only in the containerd
  journal, never in kubectl's output, which merely timed out on the Pod. The
  guard now also looks at `gvisor-bin/gvisor_sentry`, without which a node
  already carrying runsc would never reinstall the missing directory.

  The setup also declares runsc's options, `SystemdCgroup = true`: the common
  base aligned runc on systemd cgroups through a string `replace`, which did not
  reach the section added afterwards.

- **`cka-kubeadm-upgrade`: the target of the return was pinned.** The cleanup
  aimed at `1.37.0-1.1` by hand, while `shared/kubeadm-cluster.yml` warns that
  "nothing pins the PATCH" in `pkgs.k8s.io/v1.37`. 1.37.1 has shipped since, so
  the cleanup downgraded the cluster by one patch on every run. The setup now
  records the catalog's version before degrading it, the cleanup reads it back,
  and no version number is left in that file. The package number is asked of APT
  rather than rebuilt, its suffix varying from one release to the next.

- **`cks-istio-mtls-lockdown`: one more ConfigMap that istiod distributes.** The
  cleanup removed `istio-ca-root-cert` namespace by namespace, but istiod pushes
  a second one, `istio-ca-crl`, added by a more recent version. Removal now goes
  by the `istio-ca-` prefix: naming the objects one by one was the real cause,
  since the list could only fall behind Istio.

- The README catalog had fallen behind on lab titles, the hook that catches it
  running only on push.

### Added

- **Two probes in the `cks-runtime-sandbox-gvisor` setup**, and one of them
  named the cause on the first attempt. The second is the only one that proves
  anything: it starts a witness Pod in `runsc` and, on failure, prints its
  Events and the containerd journal before exiting 1. It takes its own throwaway
  namespace, returned by a `trap`. A setup must fail at home, with a message,
  rather than let the instructor's solution fail three minutes later on a silent
  timeout.

- **`tests/test_tolerance_de_version.py`**, thirty-three cases. No test covered
  `scripts/valider-labs.py` until now, even though it is what decides whether a
  lab is publishable.

### Changed, two named tolerances in the validator

`cka-kubeadm-upgrade` is the only lab in the catalog that touches its cluster's
version: its setup downgrades it so there is something to upgrade, and its
cleanup brings it back with `kubeadm upgrade apply` where the common base builds
with `kubeadm init`. Two tolerances, both by name, acknowledge this:

- node versions may be **greater than or equal to** the initial photograph's,
  never lower. This is not "we ignore the version for this lab", it is "we
  accept that it leaves the cluster up, not that it leaves it down". A downgrade
  remains a discrepancy, and that was exactly the defect fixed above;
- the `kubeadm-config` and `kubelet-config` ConfigMaps may differ, because
  `kubeadm upgrade apply` regenerates them differently from `kubeadm init`.
  Measured by capturing their content: the difference is a single line,
  `resolvConf: /run/systemd/resolve/resolv.conf`, which the upgrade adds upon
  detecting systemd-resolved.

This second allowance is wider than the first, the photograph carrying only
digests. It stays bounded to two named keys and one identifier: `coredns`,
`kube-proxy` and every other `kube-system` object remain compared, for this lab
too. Removing it rather than accepting it would mean having the common base
write `resolvConf` at `init` time, which would change how all sixty-four labs
build their cluster.

### Measured durations

`cks-runtime-sandbox-gvisor` 231 s, `cks-istio-mtls-lockdown` 409 s,
`cka-kubeadm-upgrade` 874 s.

## [0.1.0] - 2026-10-09

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

[Unreleased]: https://github.com/stephrobert/kubernetes-dsoxlab-training/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/stephrobert/kubernetes-dsoxlab-training/releases/tag/v0.1.1
[0.1.0]: https://github.com/stephrobert/kubernetes-dsoxlab-training/releases/tag/v0.1.0
