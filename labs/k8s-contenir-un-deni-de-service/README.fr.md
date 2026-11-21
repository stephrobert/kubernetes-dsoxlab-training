# Contenir un déni de service dans son namespace

La leçon montre comment un Pod sans limites peut épuiser un cluster, et comment
les quotas le contiennent. Ce cours ajoute des cas qu'elle ne montre pas : le
bridage du processeur lu directement dans le cgroup du conteneur, une limite
de disque temporaire qui fait évincer le Pod, et un plancher qui refuse un
conteneur trop petit.

Vous travaillez dans un namespace d'essai, `essai-dos`. Le challenge porte sur
d'autres namespaces : vous le ferez seul, à la fin.

Page associée : [Déni de service : épuiser un cluster](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/deni-de-service-cluster/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run k8s-contenir-un-deni-de-service
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le nœud qui pilote le cluster
kubeadm (le control plane). Votre kubectl le vise déjà.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
21 novembre 2026, avec Kubernetes v1.37.2.

## 🐢 Exercice 1 : un processeur bridé

Lancez un Pod qui calcule sans arrêt, limité à 10 millièmes de processeur :

```bash
kubectl create namespace essai-dos; kubectl run frein --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-dos --overrides='{"spec":{"containers":[{"name":"frein","image":"busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4","command":["sh","-c","while :; do :; done"],"resources":{"limits":{"cpu":"100m"}}}]}}' -- true; kubectl wait --for=condition=Ready pod/frein -n essai-dos --timeout=60s; sleep 20
```

```text
namespace/essai-dos created
pod/frein created
pod/frein condition met
```

Une limite de processeur ne tue pas le conteneur : elle le **bride**. Le noyau
le lit dans le cgroup du conteneur :

```bash
kubectl exec frein -n essai-dos -- cat /sys/fs/cgroup/cpu.max; kubectl exec frein -n essai-dos -- grep -E 'nr_periods|nr_throttled' /sys/fs/cgroup/cpu.stat
```

```text
10000 100000
nr_periods 202
nr_throttled 202
```

`cpu.max` vaut `10000 100000` : 10 ms de calcul autorisées par période de
100 ms. `nr_throttled` égale `nr_periods` : le conteneur a été bridé à chaque
période. Il tourne, mais au ralenti, et c'est ce qui protège ses voisins.

```bash
kubectl top pod frein -n essai-dos 2>&1 | tail -1
```

```text
error: Metrics API not available
```

`kubectl top` ne répond pas : ce cluster n'a pas de metrics-server. La lecture
du cgroup, elle, marche partout.

## 💾 Exercice 2 : un disque temporaire plafonné

Le disque temporaire d'un conteneur (ses fichiers hors volume) se limite comme
la mémoire. Lancez un Pod limité à 50Mi qui écrit 80Mi :

```bash
kubectl run disque-plein --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-dos --overrides='{"spec":{"containers":[{"name":"d","image":"busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4","command":["sh","-c","dd if=/dev/zero of=/tmp/gros bs=1M count=80; sleep 3600"],"resources":{"limits":{"ephemeral-storage":"50Mi"}}}]}}' -- true; sleep 60; kubectl get pod disque-plein -n essai-dos; kubectl get pod disque-plein -n essai-dos -o jsonpath='{.status.reason}: {.status.message}{"\n"}'
```

```text
pod/disque-plein created
NAME           READY   STATUS   RESTARTS   AGE
disque-plein   0/1     Error    0          60s
Evicted: Pod ephemeral local storage usage exceeds the total limit of containers 50Mi. 
```

Le kubelet a **évincé** le Pod dès qu'il a dépassé sa limite, avec un message
qui donne la cause. Sans cette limite, un seul Pod pourrait remplir le disque
du nœud et faire tomber tous les autres.

## 📏 Exercice 3 : un plancher pour chaque conteneur

Un LimitRange peut aussi fixer un **minimum**. Posez un plancher de 50m de
processeur et 32Mi de mémoire, puis essayez un conteneur plus petit :

```bash
cat <<'YAML' | kubectl apply -n essai-dos -f -
apiVersion: v1
kind: LimitRange
metadata:
  name: plancher
spec:
  limits:
    - type: Container
      min: {cpu: 50m, memory: 32Mi}
YAML
kubectl run minuscule --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-dos --overrides='{"spec":{"containers":[{"name":"m","image":"busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4","command":["sleep","3600"],"resources":{"requests":{"cpu":"10m","memory":"8Mi"},"limits":{"cpu":"10m","memory":"8Mi"}}}]}}' -- true
```

```text
limitrange/plancher created
Error from server (Forbidden): pods "minuscule" is forbidden: [minimum memory usage per Container is 32Mi, but request is 8Mi, minimum cpu usage per Container is 50m, but request is 10m]
```

Refusé à la création, avec les deux raisons. Un plancher empêche de passer
sous le radar d'un quota avec une multitude de conteneurs minuscules.

## 🧹 Nettoyage

Supprimez le namespace d'essai :

```bash
kubectl delete namespace essai-dos
```

```text
namespace "essai-dos" deleted
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset k8s-contenir-un-deni-de-service
dsoxlab check k8s-contenir-un-deni-de-service
```

```text
╭─ Résultat : k8s-contenir-un-deni-de-service ─╮
│  0 / 100 pts                                 │
│  ░░░░░░░░░░░░░░░░░░░░  0/5 tests             │
╰──────────────────────────────────────────────╯
```

0 sur 5 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : un namespace bac à sable à plafonner, et une
application gourmande à borner sans priver sa voisine.

```bash
dsoxlab run k8s-contenir-un-deni-de-service
dsoxlab challenge k8s-contenir-un-deni-de-service
```
