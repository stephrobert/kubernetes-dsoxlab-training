# Publier une version de kubernetes-dsoxlab-training

Ce dépôt livre du **contenu de labs**, pas un paquet Python. Une version publie
un **bundle `tar.gz`** du catalogue comme asset d'une Release GitHub : pas de
PyPI, pas de wheel, aucun registre d'artefacts externe.

## Ce que contient une version

Le workflow `release.yml` construit
`kubernetes-dsoxlab-training-<version>.tar.gz` avec :

- `labs/`, `shared/`, `meta.yml`, `conftest.py`, `requirements.yml`,
  `pyproject.toml`, `ssh/` (la clé publique du lab),
- `scripts/` et `tests/`, parce qu'un catalogue qui prétend se valider doit
  livrer de quoi le faire,
- `validation-labs.json`, la preuve que chaque lab a été joué dans les deux
  sens, avec sa date et la version de Kubernetes,
- les documents de gouvernance (`README`, `LICENSE`, `CONTRIBUTING`,
  `CODE_OF_CONDUCT`, `SECURITY`, `CHANGELOG`).

Il **exclut** le pilotage local (`.claude/`, `todo/`, `CLAUDE.md`) et les
fichiers générés (caches, état runtime de dsoxlab). Ces trois premiers ne sont
de toute façon pas versionnés : les exclure est une ceinture de sécurité, pas
une nécessité. Une exclusion qui ne correspond à rien ne fait pas échouer `tar`,
contrairement à un chemin listé mais absent, ce qui a déjà cassé une release
dans le dépôt Linux jumeau.

Quatre artefacts accompagnent l'archive :

| Artefact | Rôle |
| --- | --- |
| `<pkg>.tar.gz.sha256` | empreinte d'intégrité |
| `provenance.intoto.jsonl` | provenance SLSA, ce que lit Scorecard Signed-Releases |
| `<pkg>.tar.gz.cosign.bundle` | bundle de signature Cosign keyless |
| (côté registre) | attestation de build native GitHub |

## Produire une version

1. Vérifier que le catalogue est vert, et pas seulement livrable :

   ```bash
   dsoxlab validate-structure --check-urls
   pre-commit run --all-files --hook-stage pre-push
   python3 scripts/check-labs-completude.py --check
   ```

2. Basculer les entrées de `CHANGELOG.md` sous une nouvelle version.
3. Taguer et pousser le tag, ce qui déclenche `release.yml` :

   ```bash
   git tag vX.Y.Z
   git push origin vX.Y.Z
   ```

4. Le workflow construit le `tar.gz`, atteste sa provenance, le signe en
   keyless et crée la Release GitHub avec des notes générées automatiquement.

## Vérifier une version

Intégrité et contenu :

```bash
sha256sum -c kubernetes-dsoxlab-training-<version>.tar.gz.sha256
tar tzf kubernetes-dsoxlab-training-<version>.tar.gz | head
```

Provenance du build. Prouve que l'archive a bien été produite par le workflow de
ce dépôt, et non reconstruite par quelqu'un d'autre :

```bash
gh attestation verify kubernetes-dsoxlab-training-<version>.tar.gz \
  --repo stephrobert/kubernetes-dsoxlab-training
```

Signature Cosign keyless. Les **deux** options de certificat sont obligatoires :
sans elles, `cosign verify-blob` accepte n'importe quelle identité, ce qui vide
la vérification de son sens.

```bash
cosign verify-blob \
  --bundle kubernetes-dsoxlab-training-<version>.tar.gz.cosign.bundle \
  --certificate-identity-regexp "https://github.com/stephrobert/kubernetes-dsoxlab-training/.github/workflows/release.yml@.*" \
  --certificate-oidc-issuer "https://token.actions.githubusercontent.com" \
  kubernetes-dsoxlab-training-<version>.tar.gz
```

> **Piège de version Cosign.** La CI installe **Cosign 3.x**, qui écrit un
> nouveau format de bundle. Un **Cosign 2.x** local répond `no signatures found`
> sur une archive pourtant parfaitement signée : la release n'est pas cassée,
> c'est l'outil local qui ne sait pas lire le format. Vérifiez `cosign version`
> et alignez-le avant de conclure quoi que ce soit.

## Réglages GitHub à faire une fois

Deux workflows ont besoin d'une configuration qui ne vit pas dans le dépôt :

- **`plumber.yml`** attend un environnement `security`, restreint à la branche
  `main`, portant le secret `PLUMBER_ADMIN_TOKEN` : un PAT à portée fine avec
  Administration, Contents et Metadata en lecture. Sans lui, le workflow tourne
  quand même, sur le jeton du job, mais le contrôle `branchMustBeProtected`
  s'abstient et le score reste incomplet.
- **La protection de la branche `main`**, par le ruleset « Protection de main » :
  c'est elle que Scorecard et Plumber mesurent. Historique linéaire, suppression
  et poussée en force interdites, passage par pull request avec résolution des
  fils de discussion, et les six jobs de la CI en contrôles obligatoires.

> Les commits et les tags sont créés par un humain, jamais par un assistant.
