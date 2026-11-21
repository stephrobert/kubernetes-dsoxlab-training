# Sortir un Pod de l'ImagePullBackOff

La leçon montre l'état `ImagePullBackOff` : le kubelet n'arrive pas à
récupérer l'image d'un conteneur, et il réessaie de plus en plus rarement. Ce
cours ajoute des cas que la leçon ne montre pas : une image absente qu'on
interdit de télécharger, un nom d'image refusé avant même d'atteindre le
cluster, une empreinte (digest) qui n'existe pas, et le téléchargement essayé
directement depuis le nœud.

Vous travaillez dans un namespace d'essai, `essai-tirage`. Le challenge porte
sur un autre Pod : vous le ferez seul, à la fin.

Page associée : [ImagePullBackOff](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/operer/imagepullbackoff-kubernetes/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run cka-troubleshoot-imagepullbackoff
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le nœud qui pilote le cluster
kubeadm (le control plane). Votre kubectl le vise déjà.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
21 novembre 2026, avec Kubernetes v1.37.2.

## 🚫 Exercice 1 : interdire le téléchargement d'une image absente

Avec `imagePullPolicy: Never`, le kubelet n'utilise que les images déjà
présentes sur le nœud. Créez un Pod avec une image qui n'y est pas :

```bash
kubectl create namespace essai-tirage; kubectl run jamais --image=nginx:1.29.99-absente -n essai-tirage --image-pull-policy=Never; sleep 8; kubectl get pod jamais -n essai-tirage -o jsonpath='{.status.containerStatuses[0].state.waiting.reason}: {.status.containerStatuses[0].state.waiting.message}{"\n"}' | cut -c1-220
```

```text
namespace/essai-tirage created
pod/jamais created
ErrImageNeverPull: Container image "nginx:1.29.99-absente" is not present with pull policy of Never
```

`ErrImageNeverPull` : ce n'est pas un échec de téléchargement, le kubelet n'a
pas essayé. Cette politique sert aux images préchargées. Avec une image
absente, elle bloque le Pod pour toujours.

## ✏️ Exercice 2 : un nom d'image invalide

Les noms d'image s'écrivent en minuscules. Essayez une majuscule :

```bash
kubectl run majuscules --image=Nginx:1.30 -n essai-tirage; echo "run : code $?"; kubectl get pods -n essai-tirage -o name
```

```text
error: invalid image name "Nginx:1.30": invalid reference format
run : code 1
pod/jamais
```

kubectl refuse avant d'envoyer quoi que ce soit (`invalid reference
format`), et seul `jamais` existe dans le namespace. Une faute de forme ne
donne donc pas d'`ImagePullBackOff` : elle donne une erreur tout de suite. Un
`ImagePullBackOff` signale un nom bien formé, qui ne mène à rien.

## 🔏 Exercice 3 : une empreinte qui n'existe pas

Désigner une image par son empreinte (`@sha256:…`) garantit qu'on reçoit
exactement cette image. Demandez une empreinte que personne n'a publiée :

```bash
kubectl run empreinte --image=nginx@sha256:0000000000000000000000000000000000000000000000000000000000000000 -n essai-tirage; sleep 15; kubectl get pod empreinte -n essai-tirage -o jsonpath='{.status.containerStatuses[0].state.waiting.reason}: {.status.containerStatuses[0].state.waiting.message}{"\n"}' | cut -c1-220
```

```text
pod/empreinte created
ImagePullBackOff: Back-off pulling image "nginx@sha256:0000000000000000000000000000000000000000000000000000000000000000": ErrImagePull: rpc error: code = NotFound desc = failed to pull and unpack image "docker.io/library
```

`NotFound` : le registre répond, mais n'a aucune image avec cette empreinte.
Le message est coupé ici, mais il nomme l'image complète, avec son registre
(`docker.io/library/nginx`). C'est ce nom complet qu'il faut vérifier.

## 🖥️ Exercice 4 : essayer le téléchargement depuis le nœud

`crictl pull` télécharge une image sur un nœud comme le ferait le kubelet.
Essayez la même empreinte depuis le nœud du Pod :

```bash
N=$(kubectl get pod empreinte -n essai-tirage -o jsonpath='{.spec.nodeName}'); echo "nœud : $N"; ssh -o StrictHostKeyChecking=no $N 'sudo crictl pull nginx@sha256:0000000000000000000000000000000000000000000000000000000000000000 2>&1 | tail -1 | cut -c1-200'
```

```text
nœud : k8s-w1.lab
time="2026-11-21T05:47:12Z" level=error msg="pulling image: rpc error: code = NotFound desc = failed to pull and unpack image \"docker.io/library/nginx@sha256:00000000000000000000000000000000000000000
```

Même erreur que dans l'état du Pod. Essayez maintenant une image qui existe,
et cherchez-la parmi les images du nœud :

```bash
N=$(kubectl get pod empreinte -n essai-tirage -o jsonpath='{.spec.nodeName}'); ssh -o StrictHostKeyChecking=no $N 'sudo crictl pull nginx:1.30.5 2>&1 | tail -1; sudo crictl images --digests | grep -m1 "nginx.*1.30.5"' | cut -c1-140
```

```text
Image is up to date for sha256:3a8edbda21b6357f9d8e8d441c00c44673e89af4c157e76f0f117f2429570e60
docker.io/library/nginx                                                       1.30.5              9bf97bd7714f5       3a8edbda21b63       63
```

L'image est là, avec son empreinte (`9bf97bd7714f5`, le début de celle
qu'utilisent les cours). Tester depuis le nœud sépare deux questions : le
nœud peut-il atteindre le registre et télécharger, et le Pod demande-t-il la
bonne image.

## 🧹 Nettoyage

Supprimez le namespace d'essai :

```bash
kubectl delete namespace essai-tirage
```

```text
namespace "essai-tirage" deleted
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset cka-troubleshoot-imagepullbackoff
dsoxlab check cka-troubleshoot-imagepullbackoff
```

```text
╭─ Résultat : cka-troubleshoot-imagepullbackoff ─╮
│  0 / 100 pts                                   │
│  ░░░░░░░░░░░░░░░░░░░░  0/3 tests               │
╰────────────────────────────────────────────────╯
```

0 sur 3 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : un Pod bloqué sur son image, à remettre en marche
avec l'image que l'équipe voulait.

```bash
dsoxlab run cka-troubleshoot-imagepullbackoff
dsoxlab challenge cka-troubleshoot-imagepullbackoff
```
