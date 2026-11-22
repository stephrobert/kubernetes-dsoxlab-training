# Épingler une image par son digest

La leçon montre pourquoi épingler une image par son digest, et comment lire
celui que le nœud a réellement résolu. Ce cours ajoute trois cas qu'elle ne
montre pas : un digest bien formé qui ne désigne aucune image, une référence
qui porte à la fois un tag et un digest, et la différence entre le digest d'une
image multi-plateforme et l'image que le nœud garde pour sa propre
architecture.

Vous travaillez dans le namespace `essai-digest`, avec l'image `busybox`. Le
challenge porte sur un autre namespace et une autre image : vous le ferez
seul, à la fin.

Page associée : [Sécuriser la chaîne d'approvisionnement](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/supply-chain-security/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run cks-image-pinned-digest
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le nœud qui pilote le cluster
kubeadm (le control plane). Votre kubectl le vise déjà, et `ssh` atteint les
workers.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
22 novembre 2026, avec Kubernetes v1.37.2 et containerd.

## 👻 Exercice 1 : un digest qui ne désigne aucune image

Un digest se reconnaît à sa forme : `sha256:` suivi de 64 caractères
hexadécimaux. Rien ne vérifie qu'il existe au moment où vous l'écrivez.
Lancez un Pod sur un tag, et un autre sur un digest inventé :

```bash
kubectl create namespace essai-digest; kubectl run double --image=busybox:1.38.0 -n essai-digest -- sleep 3600; kubectl run fantome --image=busybox@sha256:1111111111111111111111111111111111111111111111111111111111111111 -n essai-digest -- sleep 3600; kubectl wait --for=condition=Ready pod/double -n essai-digest --timeout=120s; sleep 15; kubectl get pods -n essai-digest
```

```text
namespace/essai-digest created
pod/double created
pod/fantome created
pod/double condition met
NAME      READY   STATUS             RESTARTS   AGE
double    1/1     Running            0          16s
fantome   0/1     ImagePullBackOff   0          16s
```

L'API server accepte les deux Pods. Celui du tag tourne, celui du digest reste
en `ImagePullBackOff`. Lisez la raison :

```bash
kubectl get pod fantome -n essai-digest -o jsonpath='{.status.containerStatuses[0].state.waiting.message}{"\n"}' | cut -c1-230
```

```text
Back-off pulling image "busybox@sha256:1111111111111111111111111111111111111111111111111111111111111111": ErrImagePull: rpc error: code = NotFound desc = failed to pull and unpack image "docker.io/library/busybox@sha256:1111111111
```

`NotFound` : le registre ne connaît aucun contenu de cette empreinte. Un
digest faux ne se voit qu'au moment du tirage, sur le nœud. Retirez ce Pod :

```bash
kubectl delete pod fantome -n essai-digest
```

```text
pod "fantome" deleted from essai-digest namespace
```

## 🏷️ Exercice 2 : avec un digest, le tag ne compte plus

Une référence peut porter les deux : `image:tag@sha256:...`. Le tag sert alors
à la lecture humaine, et seul le digest décide. Pour le prouver, écrivez un
tag qui n'existe pas, `9.9.9`, devant un vrai digest :

```bash
kubectl run faux-tag --image=busybox:9.9.9@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-digest -- sleep 3600; kubectl wait --for=condition=Ready pod/faux-tag -n essai-digest --timeout=120s; kubectl get pod faux-tag -n essai-digest -o jsonpath='{.status.containerStatuses[0].image} -> {.status.containerStatuses[0].imageID}{"\n"}'
```

```text
pod/faux-tag created
pod/faux-tag condition met
docker.io/library/busybox:1.38.0 -> docker.io/library/busybox@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
```

Le Pod démarre. containerd affiche l'image sous le nom `busybox:1.38.0`, le
tag local qui correspond à ce contenu, et le digest est celui que vous avez
écrit. Le tag `9.9.9` a été ignoré : un tag faux devant un digest ne vous
alerte pas, il trompe seulement celui qui relit le manifeste.

## 🧱 Exercice 3 : un index, plusieurs plateformes

Le digest publié pour `busybox:1.38.0` désigne un **index** : une liste qui
pointe vers une image par architecture (amd64, arm64…). Le nœud tire l'index,
puis garde l'image de sa propre architecture. Regardez ce que containerd
retient sur le nœud du Pod `double` :

```bash
N=$(kubectl get pod double -n essai-digest -o jsonpath='{.spec.nodeName}'); ssh -o StrictHostKeyChecking=no $N 'sudo crictl inspecti -o json busybox:1.38.0 | python3 -c "import json,sys; s=json.load(sys.stdin)[\"status\"]; print(\"repoDigests\", s[\"repoDigests\"]); print(\"id local\", s[\"id\"][:19])"'
```

```text
repoDigests ['docker.io/library/busybox@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4']
id local sha256:aaef90e06523
```

`repoDigests` porte le digest de l'index, celui que vous écrivez dans un
manifeste. L'identifiant local est celui de l'image amd64, différent : c'est
pour cela qu'il ne faut jamais recopier dans un manifeste un identifiant lu
avec `crictl images`. Lancez un troisième Pod, sur le digest seul, et
comparez :

```bash
kubectl run plateforme --image=busybox@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-digest -- sleep 3600; kubectl wait --for=condition=Ready pod/plateforme -n essai-digest --timeout=120s; kubectl get pods -n essai-digest -o custom-columns=NOM:.metadata.name,IMAGE-ID:.status.containerStatuses[0].imageID
```

```text
pod/plateforme created
pod/plateforme condition met
NOM          IMAGE-ID
double       docker.io/library/busybox@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
faux-tag     docker.io/library/busybox@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
plateforme   docker.io/library/busybox@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
```

Les trois Pods, déclarés par tag, par tag faux plus digest, et par digest
seul, tournent tous sur le même contenu : `imageID` porte le même digest
d'index pour les trois.

## 🧹 Nettoyage

Supprimez le namespace d'essai, avec ses trois Pods :

```bash
kubectl delete namespace essai-digest
```

```text
namespace "essai-digest" deleted
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset cks-image-pinned-digest
dsoxlab check cks-image-pinned-digest
```

```text
╭─ Résultat : cks-image-pinned-digest ─╮
│  0 / 100 pts                         │
│  ░░░░░░░░░░░░░░░░░░░░  0/3 tests     │
╰──────────────────────────────────────╯
```

0 sur 3 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : un Deployment qui tourne sur un tag, à épingler sur
le digest de l'image qu'il exécute réellement, sans l'arrêter.

```bash
dsoxlab run cks-image-pinned-digest
dsoxlab challenge cks-image-pinned-digest
```
