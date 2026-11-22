# Scanner une image et choisir une version moins vulnérable

La leçon montre comment scanner une image avec Grype et Trivy, et comment lire
un rapport de failles (CVE). Ce cours ajoute quatre gestes qu'elle ne montre
pas : écarter une faille jusqu'à une date, séparer les failles du système de
celles de l'application, scanner l'image exacte qu'un nœud exécute, et
rescanner un inventaire (SBOM) sans retélécharger l'image.

Vous travaillez dans le dossier `~/essai-trivy`, avec les images `redis` et
`python`. Le challenge porte sur une autre image : vous le ferez seul, à la
fin.

Page associée : [Scanner les images](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/image-scanning/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run cks-image-scanning-trivy
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le nœud qui pilote le cluster
kubeadm (le control plane). `trivy` y est installé.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
22 novembre 2026, avec trivy 0.74.0. Les chiffres de failles changent chaque
jour, au fil des publications de CVE : les vôtres seront différents.

Créez le dossier d'essai :

```bash
mkdir -p ~/essai-trivy && trivy --version | head -1
```

```text
Version: 0.74.0
```

Les commandes de ce cours utilisent un **gabarit de sortie** (`--format
template`) : pour chaque partie de l'image analysée, il affiche son type et
son nombre de failles. Une image en contient souvent plusieurs : les paquets
du système (`debian`), un binaire Go (`gobinary`), des bibliothèques Python
(`python-pkg`)…

## 📅 Exercice 1 : écarter une faille jusqu'à une date

Comptez les failles élevées et critiques de l'image `redis` :

```bash
cd ~/essai-trivy && trivy image --quiet --scanners vuln --format template --template '{{range .}}{{.Type}} : {{len .Vulnerabilities}}{{println}}{{end}}' --severity HIGH,CRITICAL redis:7.4.8-bookworm@sha256:3e0669e42d4fe421c9dea0ba5fbc04d336b80b4f32a6c7d25bee3a1d089288a1
```

```text
debian : 59
gobinary : 60
```

Deux parties : le système Debian, et `gosu`, un binaire Go livré dans l'image.
Écartez maintenant la première faille élevée jusqu'au 31 décembre 2026, avec
`exp:` dans le fichier `.trivyignore` :

```bash
cd ~/essai-trivy && ID=$(trivy image --quiet --scanners vuln --severity HIGH --format json redis:7.4.8-bookworm@sha256:3e0669e42d4fe421c9dea0ba5fbc04d336b80b4f32a6c7d25bee3a1d089288a1 | grep -o '"VulnerabilityID": "[^"]*"' | head -1 | cut -d'"' -f4); echo "$ID exp:2026-12-31" > .trivyignore; cat .trivyignore; trivy image --quiet --scanners vuln --format template --template '{{range .}}{{.Type}} : {{len .Vulnerabilities}}{{println}}{{end}}' --severity HIGH,CRITICAL redis:7.4.8-bookworm@sha256:3e0669e42d4fe421c9dea0ba5fbc04d336b80b4f32a6c7d25bee3a1d089288a1
```

```text
CVE-2026-109518 exp:2026-12-31
debian : 57
gobinary : 60
```

La partie Debian passe de 59 à 57 : la même faille touchait deux paquets.
Changez la date pour une date passée :

```bash
cd ~/essai-trivy && sed -i 's/exp:2026-12-31/exp:2026-01-01/' .trivyignore; cat .trivyignore; trivy image --quiet --scanners vuln --format template --template '{{range .}}{{.Type}} : {{len .Vulnerabilities}}{{println}}{{end}}' --severity HIGH,CRITICAL redis:7.4.8-bookworm@sha256:3e0669e42d4fe421c9dea0ba5fbc04d336b80b4f32a6c7d25bee3a1d089288a1
```

```text
CVE-2026-109518 exp:2026-01-01
debian : 59
gobinary : 60
```

La faille revient d'elle-même : une exception datée expire, et personne n'a à
se souvenir de la retirer. Une exception sans date, elle, reste pour toujours.

## 🧩 Exercice 2 : le système d'un côté, l'application de l'autre

`--pkg-types` limite le scan à une famille de paquets. Comptez d'abord les
failles du système de l'image `python` :

```bash
cd ~/essai-trivy && rm -f .trivyignore; trivy image --quiet --scanners vuln --format template --template '{{range .}}{{.Type}} : {{len .Vulnerabilities}}{{println}}{{end}}' --severity HIGH,CRITICAL --pkg-types os python:3.13.11-slim-bookworm@sha256:20080e807bfc404f8450b185cf0fc95d553462673598549613735f70a5b4d5d0
```

```text
debian : 78
```

Puis celles des bibliothèques Python qu'elle contient :

```bash
cd ~/essai-trivy && trivy image --quiet --scanners vuln --format template --template '{{range .}}{{.Type}} : {{len .Vulnerabilities}}{{println}}{{end}}' --severity HIGH,CRITICAL --pkg-types library python:3.13.11-slim-bookworm@sha256:20080e807bfc404f8450b185cf0fc95d553462673598549613735f70a5b4d5d0
```

```text
python-pkg : 0
```

78 failles dans le système, aucune dans les bibliothèques. Ce partage dit qui
corrige : les failles du système disparaissent en changeant d'image de base,
celles des bibliothèques en changeant les dépendances de l'application. Ce
ne sont pas les mêmes équipes.

## 🖥️ Exercice 3 : scanner ce que le nœud a vraiment

Un scan par nom d'image télécharge l'image du registre, qui a pu changer
depuis. Pour scanner l'image exacte qu'un nœud exécute, lisez-la dans
containerd. Plusieurs versions peuvent y cohabiter :

```bash
sudo crictl images | grep -E 'IMAGE|kube-proxy'
```

```text
IMAGE                                      TAG                 IMAGE ID            SIZE
registry.k8s.io/kube-proxy                 v1.36.6             c407131a44390       30.1MB
registry.k8s.io/kube-proxy                 v1.37.2             55b428162aa8c       30.2MB
```

Deux versions de kube-proxy : l'ancienne reste après une montée de version.
Prenez celle que le Pod kube-proxy du nœud utilise vraiment, et scannez-la
dans containerd :

```bash
IMG=$(kubectl -n kube-system get pods -l k8s-app=kube-proxy --field-selector spec.nodeName=k8s-cp.lab -o jsonpath='{.items[0].spec.containers[0].image}'); echo "image du Pod kube-proxy : $IMG"; sudo CONTAINERD_NAMESPACE=k8s.io trivy image --quiet --scanners vuln --format template --template '{{range .}}{{.Type}} : {{len .Vulnerabilities}}{{println}}{{end}}' --image-src containerd --severity HIGH,CRITICAL $IMG
```

```text
image du Pod kube-proxy : registry.k8s.io/kube-proxy:v1.37.2
debian : 1
gobinary : 0
gobinary : 0
gobinary : 6
```

Deux réglages comptent ici : `--image-src containerd`, pour lire l'image sur
le nœud, et `CONTAINERD_NAMESPACE=k8s.io`, parce que Kubernetes range ses
images dans l'espace de noms `k8s.io` de containerd, et non dans `default`
où trivy cherche sinon. kube-proxy contient plusieurs binaires Go, d'où
plusieurs lignes `gobinary`.

## 📦 Exercice 4 : scanner un SBOM au lieu de l'image

Un SBOM est l'inventaire de tout ce qu'une image contient. Générez celui de
l'image `redis`, au format CycloneDX :

```bash
cd ~/essai-trivy && trivy image --quiet --format cyclonedx --output redis.cdx.json redis:7.4.8-bookworm@sha256:3e0669e42d4fe421c9dea0ba5fbc04d336b80b4f32a6c7d25bee3a1d089288a1; ls -l redis.cdx.json | awk '{print $5, $9}'
```

```text
199629 redis.cdx.json
```

Scannez maintenant ce fichier, sans l'image :

```bash
cd ~/essai-trivy && trivy sbom --quiet --severity HIGH,CRITICAL --format template --template '{{range .}}{{.Type}} : {{len .Vulnerabilities}}{{println}}{{end}}' redis.cdx.json
```

```text
debian : 59
gobinary : 60
```

Les chiffres sont ceux du scan de l'image. Le SBOM, archivé à chaque
livraison, se rescanne quand de nouvelles CVE sont publiées, sans
retélécharger ni reconstruire l'image.

## 🧹 Nettoyage

Supprimez le dossier d'essai :

```bash
rm -rf ~/essai-trivy; ls -d ~/essai-trivy
```

```text
ls: cannot access '/home/ansible/essai-trivy': No such file or directory
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset cks-image-scanning-trivy
dsoxlab check cks-image-scanning-trivy
```

```text
╭─ Résultat : cks-image-scanning-trivy ─╮
│  0 / 100 pts                          │
│  ░░░░░░░░░░░░░░░░░░░░  0/2 tests      │
╰───────────────────────────────────────╯
```

C'est le résultat attendu sur un lab neuf. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : une application en production sur une version
vulnérable, à faire passer sur une version qui porte moins de failles
critiques, scan à l'appui.

```bash
dsoxlab run cks-image-scanning-trivy
dsoxlab challenge cks-image-scanning-trivy
```
