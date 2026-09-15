# Publier une version de kubernetes-dsoxlab-training

**Langue :** [English](./RELEASING.md) · [Français](./RELEASING.fr.md)

Ce dépôt livre du **contenu de labs**, pas un paquet Python. Une version publie
un **bundle `tar.gz`** du catalogue comme asset d'une Release GitHub : pas de
PyPI, pas de wheel, aucun registre d'artefacts externe.

## Ce que contient une version

Le workflow `release.yml` construit
`kubernetes-dsoxlab-training-<version>.tar.gz` avec :

- `labs/`, `shared/`, `meta.yml`, `conftest.py`, `requirements.yml`,
  `pyproject.toml` et `uv.lock`, `ssh/` (la clé publique du lab),
- `scripts/` et `tests/`, parce qu'un catalogue qui prétend se valider doit
  livrer de quoi le faire,
- `validation-labs.json`, la preuve que chaque lab a été joué dans les deux
  sens, avec sa date et la version de Kubernetes,
- les documents de gouvernance (`README`, `LICENSE`, `CONTRIBUTING`,
  `CODE_OF_CONDUCT`, `SECURITY`, `CHANGELOG`), **dans les deux langues** :
  l'archive est ce que reçoit quelqu'un qui n'a pas le dépôt.

Le verrou voyage avec `pyproject.toml` délibérément. Une contrainte `>=` laisse
chaque installation résoudre ce qu'elle veut ; une archive qui prétend livrer
de quoi se valider ne dirait pas **avec quoi**.

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

## Pourquoi trois jobs, et pas un seul

Le workflow est découpé en **construire**, **attester**, **publier**, et ce
découpage est la seule chose qui sépare SLSA Build Level 2 de Level 3.

La documentation GitHub le dit en deux phrases : « Artifact attestations by
itself provides SLSA v1.0 Build Level 2 », et « Reusable workflows can provide
isolation between the build process and the calling workflow, to meet SLSA
v1.0 Build Level 3 ». Tant que le job qui construit l'archive est aussi celui
qui signe sa provenance, rien n'empêche techniquement le processus de build de
produire une provenance qui ment. Le niveau 3 exige que la signature se fasse
hors de sa portée.

D'où `.github/workflows/attester.yml`, appelé comme workflow réutilisable :

- il est le **seul du dépôt** à recevoir la permission `attestations: write` ;
- il ne reçoit qu'un **nom et une empreinte**, jamais l'archive ni le dépôt : il
  ne fait aucun `checkout` ;
- le job de publication, lui, peut écrire la release mais **ne peut pas
  attester**, faute de cette permission ;
- l'archive est recomparée à son empreinte **avant** publication, pour qu'un
  artefact altéré entre deux jobs ne soit pas publié avec une provenance qui ne
  le décrit pas.

L'appel s'écrit `uses: ./.github/workflows/attester.yml`, et non la forme
« self-repository » `$/`, plus récente, que zizmor recommande pourtant. La
raison mérite d'être consignée : l'outillage de sécurité ne sait pas encore
lire `$/`, et un analyseur qui ne comprend pas une construction ne peut pas la
juger sûre. Mesuré le 2026-09-15, sur cette ligne exactement : actionlint la
rejette comme un format invalide, zizmor 1.26.1 refuse de charger le fichier et
n'audite plus rien, et Plumber la prend pour une action tierce non épinglée
venant d'une source non autorisée, deux constats HIGH et un score de 70/100 au
lieu de 100/100. Le workflow appelé est celui qui SIGNE : c'est la dernière
ligne du dépôt sur laquelle se priver du regard des analyseurs.

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

**La vérification qui atteste le niveau 3** nomme le workflow signataire. Elle
échoue si la provenance a été produite ailleurs que par le workflow
d'attestation isolé, et c'est elle qu'il faut lancer à la première release pour
confirmer que la chaîne tient :

```bash
gh attestation verify kubernetes-dsoxlab-training-<version>.tar.gz \
  --repo stephrobert/kubernetes-dsoxlab-training \
  --signer-workflow stephrobert/kubernetes-dsoxlab-training/.github/workflows/attester.yml
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
