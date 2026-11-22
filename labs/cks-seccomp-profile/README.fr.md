# Filtrer les appels système d'un Pod avec un profil seccomp

La leçon montre comment appliquer `RuntimeDefault`, écrire un profil
`Localhost` en liste blanche, et vérifier le filtre dans `/proc`. Ce cours
ajoute trois cas qu'elle ne montre pas : un profil qui refuse une seule
famille d'appels et laisse passer le reste, un fichier de profil illisible et
l'erreur qu'il produit, et un init container confiné à part du conteneur
principal.

Vous travaillez dans le namespace `essai-seccomp`, avec deux profils d'essai
déposés sur `k8s-w1.lab`. Le challenge porte sur un autre profil et d'autres
Pods : vous le ferez seul, à la fin.

Page associée : [Seccomp](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/seccomp/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run cks-seccomp-profile
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le nœud qui pilote le cluster
kubeadm (le control plane). Votre kubectl le vise déjà, et `ssh` atteint les
workers. Un profil `Localhost` est un fichier **sur le nœud**, dans
`/var/lib/kubelet/seccomp/` : les Pods de ce cours sont donc placés sur
`k8s-w1.lab` (`nodeName`).

Les sorties montrées dans ce cours ont été relevées sur cette machine le
22 novembre 2026, avec Kubernetes v1.37.2 et containerd sur Ubuntu 24.04.

Déposez deux profils d'essai sur `k8s-w1.lab` : `sans-mkdir.json`, qui
autorise tout sauf la création de répertoire, et `casse.json`, volontairement
coupé au milieu :

```bash
ssh -o StrictHostKeyChecking=no k8s-w1.lab 'sudo mkdir -p /var/lib/kubelet/seccomp/essai; echo "{\"defaultAction\":\"SCMP_ACT_ALLOW\",\"syscalls\":[{\"names\":[\"mkdir\",\"mkdirat\"],\"action\":\"SCMP_ACT_ERRNO\"}]}" | sudo tee /var/lib/kubelet/seccomp/essai/sans-mkdir.json; echo "{\"defaultAction\": \"SCMP_ACT_ALLOW\"," | sudo tee /var/lib/kubelet/seccomp/essai/casse.json'
```

```text
{"defaultAction":"SCMP_ACT_ALLOW","syscalls":[{"names":["mkdir","mkdirat"],"action":"SCMP_ACT_ERRNO"}]}
{"defaultAction": "SCMP_ACT_ALLOW",
```

## ✂️ Exercice 1 : refuser une seule famille d'appels

La leçon part d'une liste blanche (`defaultAction: SCMP_ACT_ERRNO`) qui
refuse tout ce qui n'est pas listé. Le profil `sans-mkdir.json` fait
l'inverse : `defaultAction: SCMP_ACT_ALLOW`, et seuls `mkdir` et `mkdirat`
sont refusés. Lancez un Pod sous ce profil, puis essayez de créer un
répertoire et un fichier :

```bash
kubectl create namespace essai-seccomp; kubectl run sans-mkdir --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-seccomp --overrides='{"spec":{"nodeName":"k8s-w1.lab","securityContext":{"seccompProfile":{"type":"Localhost","localhostProfile":"essai/sans-mkdir.json"}}}}' -- sleep 3600; kubectl wait --for=condition=Ready pod/sans-mkdir -n essai-seccomp --timeout=60s; kubectl exec sans-mkdir -n essai-seccomp -- sh -c 'mkdir /tmp/rep; echo mkdir : code $?; touch /tmp/fichier; echo touch : code $?; grep Seccomp: /proc/1/status'
```

```text
namespace/essai-seccomp created
pod/sans-mkdir created
pod/sans-mkdir condition met
mkdir: can't create directory '/tmp/rep': Operation not permitted
mkdir : code 1
touch : code 0
Seccomp:	2
```

`mkdir` échoue avec `Operation not permitted` : c'est l'erreur `EPERM` que
`SCMP_ACT_ERRNO` renvoie. `touch` passe, parce que créer un fichier n'est pas
un appel `mkdir`. `Seccomp: 2` confirme qu'un filtre est actif. Une liste
noire comme celle-ci se met en place sans casser l'application, mais elle ne
bloque que ce que vous avez pensé à lister.

## 🧩 Exercice 2 : un profil illisible

Désignez maintenant le profil `casse.json`, dont le JSON est incomplet :

```bash
kubectl run casse --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-seccomp --overrides='{"spec":{"nodeName":"k8s-w1.lab","securityContext":{"seccompProfile":{"type":"Localhost","localhostProfile":"essai/casse.json"}}}}' -- sleep 3600; sleep 10; kubectl get pod casse -n essai-seccomp; kubectl get pod casse -n essai-seccomp -o jsonpath='{.status.containerStatuses[0].state.waiting.message}{"\n"}' | cut -c1-200
```

```text
pod/casse created
NAME    READY   STATUS                 RESTARTS   AGE
casse   0/1     CreateContainerError   0          11s
failed to create containerd container: decoding seccomp profile failed "/var/lib/kubelet/seccomp/essai/casse.json": unexpected end of JSON input
```

L'API server accepte le Pod, puis le conteneur reste en
`CreateContainerError`. Le message vient de containerd, sur le nœud : il nomme
le fichier et l'erreur de lecture (`unexpected end of JSON input`). Avant de
désigner un profil, vérifiez donc le fichier lui-même, par exemple avec
`python3 -m json.tool` sur le nœud.

## 🚦 Exercice 3 : un init container confiné à part

Un `securityContext` posé sur un conteneur ne vaut que pour lui. Lancez un Pod
dont seul l'init container `preparer` est sous `sans-mkdir.json`, et dont le
conteneur `app` n'a aucun profil :

```bash
kubectl run init-confine --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-seccomp --overrides='{"spec":{"nodeName":"k8s-w1.lab","initContainers":[{"name":"preparer","image":"busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4","command":["sh","-c","mkdir /tmp/rep || echo mkdir refusé pour preparer"],"securityContext":{"seccompProfile":{"type":"Localhost","localhostProfile":"essai/sans-mkdir.json"}}}],"containers":[{"name":"app","image":"busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4","command":["sh","-c","mkdir /tmp/rep && echo mkdir permis pour app; sleep 3600"]}]}}' -- true; kubectl wait --for=condition=Ready pod/init-confine -n essai-seccomp --timeout=60s; kubectl logs init-confine -n essai-seccomp -c preparer; kubectl logs init-confine -n essai-seccomp -c app
```

```text
pod/init-confine created
pod/init-confine condition met
mkdir: can't create directory '/tmp/rep': Operation not permitted
mkdir refusé pour preparer
mkdir permis pour app
```

Les journaux des deux conteneurs le montrent : `mkdir` est refusé dans
`preparer`, permis dans `app`. Le confinement d'un init container ne protège
pas le conteneur qui tourne ensuite. Pour couvrir tout le Pod, le profil se
déclare dans le `securityContext` du Pod, et chaque conteneur en hérite.

## 🧹 Nettoyage

Supprimez le namespace d'essai, puis les profils d'essai de `k8s-w1.lab` :

```bash
kubectl delete namespace essai-seccomp; ssh -o StrictHostKeyChecking=no k8s-w1.lab 'sudo rm -rf /var/lib/kubelet/seccomp/essai'
```

```text
namespace "essai-seccomp" deleted
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset cks-seccomp-profile
dsoxlab check cks-seccomp-profile
```

```text
╭─ Résultat : cks-seccomp-profile ──╮
│  0 / 100 pts                      │
│  ░░░░░░░░░░░░░░░░░░░░  0/3 tests  │
╰───────────────────────────────────╯
```

0 sur 3 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : un profil à déposer et un Pod à confiner, avec la
preuve que l'appel visé est bien refusé et qu'un témoin non confiné l'exécute
toujours.

```bash
dsoxlab run cks-seccomp-profile
dsoxlab challenge cks-seccomp-profile
```
