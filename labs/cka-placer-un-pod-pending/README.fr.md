# Lire pourquoi quatre Pods restent en Pending et placer chacun

La leçon montre comment lire pourquoi un Pod reste en `Pending` : le
scheduler écrit sa raison dans un événement `FailedScheduling`. Ce cours
ajoute des cas que la leçon ne montre pas : compter les nœuds qui acceptent
vraiment un Pod, une anti-affinité impossible à satisfaire, un volume local
attaché à un autre nœud que celui demandé, et un Pod retenu exprès par une
porte de planification.

Vous travaillez dans un namespace d'essai, `essai-attente`. Le challenge
porte sur un autre namespace et d'autres applications : vous le ferez seul, à
la fin.

Page associée : [Pods en Pending](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/operer/pods-pending-kubernetes/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run cka-placer-un-pod-pending
```

Le lab ajoute un second worker, `k8s-w2.lab`. Vous êtes maintenant connecté à
`k8s-cp.lab`, le nœud qui pilote le cluster kubeadm (le control plane). Votre
kubectl le vise déjà.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
21 novembre 2026, avec Kubernetes v1.37.2.

## 🔢 Exercice 1 : compter les nœuds qui acceptent un Pod

Créez le namespace, et listez les nœuds avec la clé de leurs taints :

```bash
kubectl create namespace essai-attente; kubectl get nodes -o custom-columns=NOM:.metadata.name,TAINTS:.spec.taints[*].key
```

```text
namespace/essai-attente created
NOM          TAINTS
k8s-cp.lab   <none>
k8s-w1.lab   equipe
k8s-w2.lab   <none>
```

Trois nœuds, mais `k8s-w1.lab` porte une taint, `equipe`, posée par le
challenge. Un Pod sans tolérance n'a donc que deux nœuds possibles :
`k8s-cp.lab` et `k8s-w2.lab`. Avant de raisonner sur un `Pending`, comptez
les nœuds qui acceptent ce Pod, pas tous les nœuds.

## 🙅 Exercice 2 : trois Pods qui ne veulent pas se croiser

Créez un Deployment de 3 réplicas avec une anti-affinité obligatoire : deux
Pods de `solitaire` ne doivent jamais partager un nœud.

```bash
cat <<YAML | kubectl apply -n essai-attente -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: solitaire
spec:
  replicas: 3
  selector:
    matchLabels: {app: solitaire}
  template:
    metadata:
      labels: {app: solitaire}
    spec:
      affinity:
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            - labelSelector:
                matchLabels: {app: solitaire}
              topologyKey: kubernetes.io/hostname
      containers:
        - {name: c, image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4, command: [sleep, "3600"]}
YAML
sleep 15; kubectl get pods -n essai-attente -l app=solitaire -o custom-columns=NOM:.metadata.name,ETAT:.status.phase,NOEUD:.spec.nodeName
```

```text
deployment.apps/solitaire created
NOM                          ETAT      NOEUD
solitaire-55b5fddd6b-knw9f   Running   k8s-w2.lab
solitaire-55b5fddd6b-thr5f   Running   k8s-cp.lab
solitaire-55b5fddd6b-z5bns   Pending   <none>
```

Deux Pods tournent, un sur chaque nœud libre, et le troisième attend. Lisez la
raison du scheduler :

```bash
P=$(kubectl get pods -n essai-attente -l app=solitaire --field-selector status.phase=Pending -o jsonpath='{.items[0].metadata.name}'); kubectl get events -n essai-attente --field-selector reason=FailedScheduling,involvedObject.name=$P -o custom-columns=MESSAGE:.message --no-headers | tail -1
```

```text
0/3 nodes are available: 1 node(s) had untolerated taint(s), 2 node(s) didn't match pod anti-affinity rules. preemption: 0/3 nodes are available: 1 Preemption is not helpful for scheduling, 2 No preemption victims found for incoming pod.
```

Le scheduler détaille son refus nœud par nœud : un nœud a une taint non
tolérée, les deux autres portent déjà un Pod `solitaire`. Le message ne dit
pas quoi faire, il dit quel filtre a écarté chaque nœud. Ici, il faudrait un
nœud de plus, ou une anti-affinité seulement préférée (`preferred`).

## 💾 Exercice 3 : un volume qui vit sur un autre nœud

Un volume `local` est attaché à un nœud précis. Créez-en un sur
`k8s-cp.lab`, une demande liée à lui, et un Pod qui exige `k8s-w2.lab` :

```bash
cat <<'YAML' | kubectl apply -f -
apiVersion: v1
kind: PersistentVolume
metadata:
  name: essai-carnet-local
spec:
  capacity: {storage: 64Mi}
  accessModes: [ReadWriteOnce]
  storageClassName: essai-locale
  local: {path: /tmp}
  nodeAffinity:
    required:
      nodeSelectorTerms:
        - matchExpressions:
            - {key: kubernetes.io/hostname, operator: In, values: [k8s-cp.lab]}
YAML
cat <<YAML | kubectl apply -n essai-attente -f -
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: carnet-local
spec:
  accessModes: [ReadWriteOnce]
  storageClassName: essai-locale
  volumeName: essai-carnet-local
  resources: {requests: {storage: 64Mi}}
---
apiVersion: v1
kind: Pod
metadata:
  name: carnet
spec:
  nodeSelector: {kubernetes.io/hostname: k8s-w2.lab}
  containers:
    - {name: c, image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4, command: [sleep, "3600"], volumeMounts: [{name: v, mountPath: /data}]}
  volumes:
    - {name: v, persistentVolumeClaim: {claimName: carnet-local}}
YAML
sleep 20; kubectl get pvc carnet-local -n essai-attente; kubectl get pod carnet -n essai-attente; kubectl get events -n essai-attente --field-selector reason=FailedScheduling,involvedObject.name=carnet -o custom-columns=MESSAGE:.message --no-headers | tail -1
```

```text
persistentvolume/essai-carnet-local created
persistentvolumeclaim/carnet-local created
pod/carnet created
NAME           STATUS   VOLUME               CAPACITY   ACCESS MODES   STORAGECLASS   VOLUMEATTRIBUTESCLASS   AGE
carnet-local   Bound    essai-carnet-local   64Mi       RWO            essai-locale   <unset>                 20s
NAME     READY   STATUS    RESTARTS   AGE
carnet   0/1     Pending   0          20s
0/3 nodes are available: 1 node(s) didn't match PersistentVolume's node affinity, 1 node(s) didn't match Pod's node affinity/selector, 1 node(s) had untolerated taint(s). preemption: 0/3 nodes are available: 3 Preemption is not helpful for scheduling.
```

La demande est bien liée (`Bound`), et pourtant le Pod attend. Les trois
nœuds sont écartés, chacun pour une raison : l'un n'est pas celui du volume,
l'autre n'est pas celui du sélecteur, le dernier a une taint. Le Pod demande
un nœud, son volume en impose un autre : aucun ne satisfait les deux. Un
volume local se choisit avec le nœud, pas après.

## 🚦 Exercice 4 : un Pod retenu exprès

Une porte de planification (`schedulingGates`) empêche le scheduler de
s'occuper d'un Pod tant qu'elle est là. Créez un Pod avec une porte :

```bash
kubectl run retenu --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-attente --overrides='{"spec":{"schedulingGates":[{"name":"essai.lab/feu-vert"}]}}' -- sleep 3600; sleep 5; kubectl get pod retenu -n essai-attente
```

```text
pod/retenu created
NAME     READY   STATUS            RESTARTS   AGE
retenu   0/1     SchedulingGated   0          5s
```

`SchedulingGated` : ce n'est pas un échec, le Pod attend qu'on le libère.
Retirez la porte :

```bash
kubectl patch pod retenu -n essai-attente --type json -p '[{"op":"remove","path":"/spec/schedulingGates"}]'; sleep 8; kubectl get pod retenu -n essai-attente -o custom-columns=NOM:.metadata.name,ETAT:.status.phase,NOEUD:.spec.nodeName
```

```text
pod/retenu patched
NOM      ETAT      NOEUD
retenu   Running   k8s-w2.lab
```

Le Pod est placé dès que la porte disparaît. Un outil peut ainsi préparer des
Pods et ne les lâcher qu'au bon moment.

## 🧹 Nettoyage

Supprimez le namespace et le PersistentVolume, qui n'appartient à aucun
namespace :

```bash
kubectl delete namespace essai-attente; kubectl delete pv essai-carnet-local
```

```text
namespace "essai-attente" deleted
persistentvolume "essai-carnet-local" deleted
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset cka-placer-un-pod-pending
dsoxlab check cka-placer-un-pod-pending
```

```text
╭─ Résultat : cka-placer-un-pod-pending ─╮
│  0 / 100 pts                           │
│  ░░░░░░░░░░░░░░░░░░░░  0/5 tests       │
╰────────────────────────────────────────╯
```

0 sur 5 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : quatre applications en `Pending`, une cause chacune,
à diagnostiquer puis à placer.

```bash
dsoxlab run cka-placer-un-pod-pending
dsoxlab challenge cka-placer-un-pod-pending
```
