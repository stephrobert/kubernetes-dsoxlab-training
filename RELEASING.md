# Releasing kubernetes-dsoxlab-training

**Language:** [English](./RELEASING.md) · [Français](./RELEASING.fr.md)

This repository ships **lab content**, not a Python package. A release
publishes a **`tar.gz` bundle** of the catalogue as an asset of a GitHub
Release: no PyPI, no wheel, no external artifact registry.

## What a release contains

The `release.yml` workflow builds
`kubernetes-dsoxlab-training-<version>.tar.gz` with:

- `labs/`, `shared/`, `meta.yml`, `conftest.py`, `requirements.yml`,
  `pyproject.toml`, `ssh/` (the lab's public key),
- `scripts/` and `tests/`, because a catalogue that claims to validate itself
  must ship the means to do so,
- `validation-labs.json`, the proof that every lab was played in both
  directions, with its date and its Kubernetes version,
- the governance documents (`README`, `LICENSE`, `CONTRIBUTING`,
  `CODE_OF_CONDUCT`, `SECURITY`, `CHANGELOG`).

It **excludes** local steering (`.claude/`, `todo/`, `CLAUDE.md`) and generated
files (caches, dsoxlab runtime state). The first three are not versioned
anyway: excluding them is a safety belt, not a necessity. An exclusion that
matches nothing does not fail `tar`, unlike a path that is listed but absent,
which has already broken a release in the sibling Linux catalogue.

Four artifacts accompany the archive:

| Artifact | Purpose |
| --- | --- |
| `<pkg>.tar.gz.sha256` | integrity digest |
| `provenance.intoto.jsonl` | SLSA provenance, what Scorecard Signed-Releases reads |
| `<pkg>.tar.gz.cosign.bundle` | keyless Cosign signature bundle |
| (registry side) | GitHub's native build attestation |

## Why three jobs, and not one

The workflow is split into **build**, **attest**, **publish**, and that split is
the only thing separating SLSA Build Level 2 from Level 3.

GitHub's documentation puts it in two sentences: "Artifact attestations by
itself provides SLSA v1.0 Build Level 2", and "Reusable workflows can provide
isolation between the build process and the calling workflow, to meet SLSA v1.0
Build Level 3". As long as the job that builds the archive is also the one that
signs its provenance, nothing technically stops the build process from
producing provenance that lies. Level 3 requires the signing to happen out of
its reach.

Hence `.github/workflows/attester.yml`, called as a reusable workflow:

- it is the **only workflow in the repository** granted `attestations: write`;
- it receives **a name and a digest**, never the archive nor the repository: it
  performs no `checkout`;
- the publish job can write the release but **cannot attest**, lacking that
  permission;
- the archive is re-checked against its digest **before** publication, so that
  an artifact altered between two jobs is not published with provenance that
  does not describe it.

The call reads `uses: ./.github/workflows/attester.yml`, and not the newer
`$/` "self-repository" form, even though zizmor recommends the latter. The
reason is worth recording: security tooling cannot read `$/` yet, and an
analyser that does not understand a construct cannot judge it safe. Measured on
2026-09-15, on that exact line: actionlint rejects it as an invalid format,
zizmor 1.26.1 refuses to load the file and audits nothing at all, and Plumber
takes it for an unpinned third-party action from an unauthorised source, two
HIGH findings and a score of 70/100 instead of 100/100. The called workflow is
the one that *signs*: it is the last line in the repository on which to give up
the analysers' scrutiny.

## Cutting a release

1. Check that the catalogue is green, not merely shippable:

   ```bash
   dsoxlab validate-structure --check-urls
   pre-commit run --all-files --hook-stage pre-push
   python3 scripts/check-labs-completude.py --check
   ```

2. Move the `CHANGELOG.md` and `CHANGELOG.fr.md` entries under a new version.
3. Tag and push the tag, which triggers `release.yml`:

   ```bash
   git tag vX.Y.Z
   git push origin vX.Y.Z
   ```

4. The workflow builds the `tar.gz`, attests its provenance, signs it keyless
   and creates the GitHub Release with auto-generated notes.

## Verifying a release

Integrity and contents:

```bash
sha256sum -c kubernetes-dsoxlab-training-<version>.tar.gz.sha256
tar tzf kubernetes-dsoxlab-training-<version>.tar.gz | head
```

Build provenance. Proves the archive really was produced by this repository's
workflow, and not rebuilt by someone else:

```bash
gh attestation verify kubernetes-dsoxlab-training-<version>.tar.gz \
  --repo stephrobert/kubernetes-dsoxlab-training
```

**The check that establishes Build Level 3** names the signing workflow. It
fails if the provenance was produced anywhere other than the isolated attester
workflow, and it is the one to run on the first release to confirm the chain
holds:

```bash
gh attestation verify kubernetes-dsoxlab-training-<version>.tar.gz \
  --repo stephrobert/kubernetes-dsoxlab-training \
  --signer-workflow stephrobert/kubernetes-dsoxlab-training/.github/workflows/attester.yml
```

Keyless Cosign signature. **Both** certificate flags are mandatory: without
them, `cosign verify-blob` accepts any identity, which empties the verification
of its meaning.

```bash
cosign verify-blob \
  --bundle kubernetes-dsoxlab-training-<version>.tar.gz.cosign.bundle \
  --certificate-identity-regexp "https://github.com/stephrobert/kubernetes-dsoxlab-training/.github/workflows/release.yml@.*" \
  --certificate-oidc-issuer "https://token.actions.githubusercontent.com" \
  kubernetes-dsoxlab-training-<version>.tar.gz
```

> **Cosign version trap.** The CI installs **Cosign 3.x**, which writes a new
> bundle format. A local **Cosign 2.x** answers `no signatures found` on a
> perfectly signed archive: the release is not broken, the local tool cannot
> read the format. Check `cosign version` and align it before concluding
> anything.

## GitHub settings to do once

Two workflows need configuration that does not live in the repository:

- **`plumber.yml`** expects a `security` environment, restricted to the `main`
  branch, holding the `PLUMBER_ADMIN_TOKEN` secret: a fine-grained PAT with
  Administration, Contents and Metadata read access. Without it the workflow
  still runs, on the job token, but the `branchMustBeProtected` control abstains
  and the score stays incomplete.
- **Protection of the `main` branch**, through the "Protection de main" ruleset:
  that is what Scorecard and Plumber measure. Linear history, deletion and force
  pushes forbidden, pull request required with review thread resolution, and the
  six CI jobs as required status checks.

> Commits and tags are created by a human, never by an assistant.
