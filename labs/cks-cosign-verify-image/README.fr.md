# Signer une image avec cosign et publier sa clé publique

La leçon montre comment générer une paire de clés, signer le digest d'une
image, retrouver la signature dans le registre et la vérifier. Ce cours
montre trois situations qu'elle ne fait que citer : un tag déplacé qui perd sa
signature, une annotation exigée à la vérification, et une image copiée dans
un autre dépôt qui arrive sans sa signature.

Vous travaillez dans le dossier `~/essai-cosign` et le dépôt `essai/` du
registre local, avec votre propre paire de clés. Le challenge porte sur une
autre image et d'autres clés : vous le ferez seul, à la fin.

Page associée : [Signer et vérifier une image](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/signer-et-verifier-une-image/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run cks-cosign-verify-image
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le nœud qui pilote le cluster
kubeadm (le control plane). Un registre local répond en `localhost:5000`, et
`cosign` et `crane` sont installés.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
22 novembre 2026.

Toutes les signatures de ce cours sont faites **hors ligne** : la
configuration `sans-journal.json` ne publie rien dans Rekor, le journal public
de Sigstore, d'où `--insecure-ignore-tlog=true` à la vérification. C'est la
méthode décrite dans le dépannage de la leçon. Le challenge, lui, vérifie avec
la configuration par défaut de cosign, qui exige l'entrée dans Rekor : une
signature hors ligne n'y passe pas.

Créez une paire de clés et la configuration sans journal, puis copiez une
image dans le dépôt d'essai :

```bash
mkdir -p ~/essai-cosign && cd ~/essai-cosign && COSIGN_PASSWORD= cosign generate-key-pair >/dev/null 2>&1; cosign signing-config create --out sans-journal.json >/dev/null 2>&1; ls; crane copy localhost:5000/appli/outil:1.0 localhost:5000/essai/outil:1.0 >/dev/null 2>&1; crane digest localhost:5000/essai/outil:1.0
```

```text
cosign.key
cosign.pub
sans-journal.json
sha256:a7dbc319b1438115a207e11930dc4bb3e643dcb3ec0bdd694bb36cd8fad289ec
```

## 🏷️ Exercice 1 : un tag déplacé perd sa signature

Signez l'image d'essai par son digest, puis vérifiez-la par son tag :

```bash
cd ~/essai-cosign && D=$(crane digest localhost:5000/essai/outil:1.0); COSIGN_PASSWORD= cosign sign -y --key cosign.key --signing-config sans-journal.json --allow-http-registry localhost:5000/essai/outil@$D >/dev/null 2>&1; cosign verify --key cosign.pub --insecure-ignore-tlog=true --allow-http-registry localhost:5000/essai/outil:1.0 >/dev/null 2>&1; echo "tag 1.0 : code $?"
```

```text
tag 1.0 : code 0
```

Code 0 : le tag `1.0` désigne l'image signée. Déplacez maintenant ce tag sur
une autre image, comme le ferait quelqu'un qui pousse par-dessus, et vérifiez
de nouveau par le tag :

```bash
cd ~/essai-cosign && crane copy localhost:5000/appli/web:1.0 localhost:5000/essai/outil:1.0 >/dev/null 2>&1; crane digest localhost:5000/essai/outil:1.0; cosign verify --key cosign.pub --insecure-ignore-tlog=true --allow-http-registry localhost:5000/essai/outil:1.0 2>&1 | tail -1; echo "tag 1.0 déplacé : code ${PIPESTATUS[0]}"
```

```text
sha256:65645c7bb6a0661892a8b03b89d0743208a18dd2f3f17a54ef4b76fb8e2f2a10
error during command execution: no signatures found
tag 1.0 déplacé : code 10
```

Le digest a changé, et la vérification rend le code 10 (`no signatures
found`). La signature est restée attachée à l'ancien contenu : c'est ce qui
rend impossible de faire passer une image pour une autre en déplaçant un tag.

## 🔖 Exercice 2 : exiger une annotation

Une signature peut porter des annotations, des paires clé-valeur que la
vérification peut exiger. Signez l'image en déclarant l'équipe qui la livre,
puis vérifiez avec la bonne valeur, et avec une autre :

```bash
cd ~/essai-cosign && D=$(crane digest localhost:5000/essai/outil:1.0); COSIGN_PASSWORD= cosign sign -y --key cosign.key --signing-config sans-journal.json --allow-http-registry -a equipe=boutique localhost:5000/essai/outil@$D >/dev/null 2>&1; cosign verify --key cosign.pub --insecure-ignore-tlog=true --allow-http-registry -a equipe=boutique localhost:5000/essai/outil@$D >/dev/null 2>&1; echo "equipe=boutique : code $?"; cosign verify --key cosign.pub --insecure-ignore-tlog=true --allow-http-registry -a equipe=paiement localhost:5000/essai/outil@$D 2>&1 | tail -1; echo "equipe=paiement : code ${PIPESTATUS[0]}"
```

```text
equipe=boutique : code 0
error during command execution: no matching attestations: missing or incorrect annotation
equipe=paiement : code 1
```

Avec `equipe=boutique`, code 0. Avec `equipe=paiement`, code 1 : la
signature est valide, mais elle ne porte pas l'annotation exigée. Une même
clé peut ainsi servir à plusieurs équipes, chacune ne déployant que ce qui a
été signé pour elle.

## 📋 Exercice 3 : une copie arrive sans sa signature

Copiez l'image signée dans un autre dépôt du même registre, puis comparez les
tags des deux dépôts :

```bash
cd ~/essai-cosign && D=$(crane digest localhost:5000/essai/outil:1.0); crane copy localhost:5000/essai/outil@$D localhost:5000/essai/copie:1.0 >/dev/null 2>&1; crane ls localhost:5000/essai/outil; echo ---; crane ls localhost:5000/essai/copie; cosign verify --key cosign.pub --insecure-ignore-tlog=true --allow-http-registry localhost:5000/essai/copie@$D 2>&1 | tail -1; echo "copie : code ${PIPESTATUS[0]}"
```

```text
sha256-65645c7bb6a0661892a8b03b89d0743208a18dd2f3f17a54ef4b76fb8e2f2a10
1.0
sha256-a7dbc319b1438115a207e11930dc4bb3e643dcb3ec0bdd694bb36cd8fad289ec
---
1.0
error during command execution: no signatures found
copie : code 10
```

Le dépôt d'origine porte les tags `sha256-...` des deux signatures faites dans
ce cours. Le dépôt `copie` n'a que `1.0` : `crane copy` a recopié l'image,
pas l'artefact de signature qui vit à côté. La vérification rend le code 10.
Une vérification qui échoue après une migration de registre a souvent cette
cause : il faut copier aussi les signatures, ou resigner.

## 🧹 Nettoyage

Supprimez le dossier d'essai et ses clés :

```bash
rm -rf ~/essai-cosign; ls -d ~/essai-cosign
```

```text
ls: cannot access '/home/ansible/essai-cosign': No such file or directory
```

Le dépôt `essai/` du registre disparaît avec le `reset`, qui recrée le
registre du lab. Quittez la machine et remettez le lab à zéro. `dsoxlab reset`
rejoue le nettoyage puis la préparation du lab : vous retrouvez exactement
l'état de départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset cks-cosign-verify-image
dsoxlab check cks-cosign-verify-image
```

```text
╭─ Résultat : cks-cosign-verify-image ─╮
│  0 / 100 pts                         │
│  ░░░░░░░░░░░░░░░░░░░░  0/3 tests     │
╰──────────────────────────────────────╯
```

0 sur 3 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : une image d'équipe à signer, et une clé publique à
publier dans le cluster, sans que la clé privée quitte le nœud.

```bash
dsoxlab run cks-cosign-verify-image
dsoxlab challenge cks-cosign-verify-image
```
