# Un agent sur chaque nœud, control plane compris

La leçon montre un DaemonSet qui place un Pod sur chaque nœud. Les agents
lancés ainsi (supervision, journaux, réseau) touchent souvent au nœud
lui-même. Ce cours ajoute des cas que la leçon ne montre pas : un port ouvert
sur chaque nœud avec `hostPort`, deux DaemonSets qui se disputent ce port, un
agent qui partage le réseau du nœud sans perdre le DNS du cluster, et la
vidange d'un nœud qui porte des Pods de DaemonSet.

Vous travaillez dans un namespace d'essai, `essai-ds`, avec deux DaemonSets
d'essai, `sentinelle` et `doublon`, et un Pod `sonde-hote`. Le challenge porte
sur d'autres objets : vous le ferez seul, à la fin.

Page associée : [DaemonSets](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/daemonsets/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run cka-daemonset-all-nodes
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le nœud qui pilote le cluster
kubeadm (le control plane). Votre kubectl le vise déjà. Le cluster a deux
nœuds : `k8s-cp.lab` et le worker `k8s-w1.lab`.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
21 novembre 2026, avec Kubernetes v1.37.2.

## 🔌 Exercice 1 : un port ouvert sur chaque nœud

Avec `hostPort`, le port d'un conteneur s'ouvre aussi sur l'adresse du nœud
qui porte le Pod. Créez le namespace, puis un DaemonSet `sentinelle` dont
l'agent répond son nom de Pod sur le port 9376, publié sur le port 19376 du
nœud :

```bash
kubectl create namespace essai-ds
cat <<YAML | kubectl apply -n essai-ds -f -
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: sentinelle
spec:
  selector:
    matchLabels: {app: sentinelle}
  template:
    metadata:
      labels: {app: sentinelle}
    spec:
      containers:
        - name: agent
          image: registry.k8s.io/e2e-test-images/agnhost:2.53
          args: [serve-hostname, --port=9376]
          ports:
            - {containerPort: 9376, hostPort: 19376}
YAML
kubectl rollout status daemonset/sentinelle -n essai-ds --timeout=120s; kubectl get pods -n essai-ds -o wide | cut -c1-90
```

```text
namespace/essai-ds created
daemonset.apps/sentinelle created
Waiting for daemon set "sentinelle" rollout to finish: 0 of 1 updated pods are available...
daemon set "sentinelle" successfully rolled out
NAME               READY   STATUS    RESTARTS   AGE   IP              NODE         NOMINAT
sentinelle-l9n54   1/1     Running   0          0s    10.244.38.126   k8s-w1.lab   <none> 
```

Un seul Pod, sur `k8s-w1.lab`. Appelez le port 19376 de chaque nœud :

```bash
for n in $(kubectl get nodes -o jsonpath='{.items[*].status.addresses[0].address}'); do printf '%s:19376 -> ' $n; curl -s -m 3 "http://$n:19376"; echo; done
```

```text
10.10.50.11:19376 -> 
10.10.50.12:19376 -> sentinelle-l9n54
```

Le worker répond, le control plane non : il n'a pas de Pod. Le control plane
porte une taint qui écarte les Pods qui ne la tolèrent pas, ceux d'un
DaemonSet compris. C'est précisément l'objet du challenge.

## ⚔️ Exercice 2 : deux DaemonSets veulent le même port

Créez un second DaemonSet, `doublon`, identique, qui demande lui aussi le port
19376 du nœud :

```bash
cat <<YAML | kubectl apply -n essai-ds -f -
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: doublon
spec:
  selector:
    matchLabels: {app: doublon}
  template:
    metadata:
      labels: {app: doublon}
    spec:
      containers:
        - name: agent
          image: registry.k8s.io/e2e-test-images/agnhost:2.53
          args: [serve-hostname, --port=9376]
          ports:
            - {containerPort: 9376, hostPort: 19376}
YAML
sleep 10; kubectl get pods -n essai-ds -l app=doublon
```

```text
daemonset.apps/doublon created
NAME            READY   STATUS    RESTARTS   AGE
doublon-tgfrv   0/1     Pending   0          10s
```

Son Pod reste `Pending`. Lisez la raison donnée par le scheduler :

```bash
P=$(kubectl get pods -n essai-ds -l app=doublon -o name | head -1); kubectl get events -n essai-ds --field-selector involvedObject.name=${P#pod/} -o custom-columns=MESSAGE:.message --no-headers | tail -1
```

```text
0/2 nodes are available: 1 node(s) didn't have free ports for the requested pod ports, 1 node(s) didn't satisfy plugin(s) [NodeAffinity]. preemption: 0/2 nodes are available: 1 No preemption victims found for incoming pod, 1 Preemption is not helpful for scheduling.
```

Deux raisons, une par nœud. Sur le worker, le port 19376 est déjà pris par
`sentinelle` (`didn't have free ports`). L'autre nœud est refusé par
`NodeAffinity` : chaque Pod d'un DaemonSet est attaché à un nœud précis, et ne
peut pas aller ailleurs. Deux agents qui publient le même `hostPort` ne
peuvent donc pas cohabiter sur un nœud. Supprimez `doublon` :

```bash
kubectl delete daemonset doublon -n essai-ds
```

```text
daemonset.apps "doublon" deleted from essai-ds namespace
```

## 🏠 Exercice 3 : partager le réseau du nœud sans perdre le DNS du cluster

Un agent réseau tourne souvent en `hostNetwork`. Créez un tel Pod et
demandez-lui le nom du Service `kubernetes` :

```bash
kubectl run sonde-hote --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-ds --overrides='{"spec":{"hostNetwork":true}}' -- sleep 3600; kubectl wait --for=condition=Ready pod/sonde-hote -n essai-ds --timeout=120s; kubectl exec sonde-hote -n essai-ds -- nslookup -timeout=3 kubernetes.default.svc.cluster.local; echo "code $?"
```

```text
pod/sonde-hote created
pod/sonde-hote condition met
;; connection timed out; no servers could be reached

command terminated with exit code 1
code 1
```

Pas de réponse. En `hostNetwork`, la politique DNS par défaut (`ClusterFirst`)
donne au Pod le DNS du nœud, qui ne connaît pas les noms du cluster.
Recréez-le avec `dnsPolicy: ClusterFirstWithHostNet` :

```bash
kubectl delete pod sonde-hote -n essai-ds; kubectl run sonde-hote --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-ds --overrides='{"spec":{"hostNetwork":true,"dnsPolicy":"ClusterFirstWithHostNet"}}' -- sleep 3600; kubectl wait --for=condition=Ready pod/sonde-hote -n essai-ds --timeout=120s; kubectl exec sonde-hote -n essai-ds -- nslookup kubernetes.default.svc.cluster.local. | grep -A1 Name
```

```text
pod "sonde-hote" deleted from essai-ds namespace
pod/sonde-hote created
pod/sonde-hote condition met
Name:	kubernetes.default.svc.cluster.local
Address: 10.96.0.1
```

Le nom se résout. Un agent en `hostNetwork` qui doit joindre des Services par
leur nom a besoin de cette politique.

## 🚧 Exercice 4 : vider un nœud qui porte des Pods de DaemonSet

Simulez la vidange du worker avec `--dry-run=server` : l'API vérifie tout,
mais rien n'est déplacé.

```bash
kubectl drain k8s-w1.lab --dry-run=server 2>&1 | tail -4
```

```text
There are pending nodes to be drained:
 k8s-w1.lab
cannot delete DaemonSet-managed Pods (use --ignore-daemonsets to ignore): calico-system/calico-node-8x2wb, calico-system/csi-node-driver-lh854, essai-ds/sentinelle-l9n54, kube-system/kube-proxy-rfprv
cannot delete Pods that declare no controller (use --force to override): essai-ds/sonde-hote
```

Deux blocages. Les Pods de DaemonSet ne peuvent pas être évincés : le
DaemonSet les recréerait aussitôt sur le même nœud. Et `sonde-hote`, créé
sans contrôleur, serait perdu pour de bon. Supprimez `sonde-hote`, et
relancez avec `--ignore-daemonsets` :

```bash
kubectl delete pod sonde-hote -n essai-ds; kubectl drain k8s-w1.lab --dry-run=server --ignore-daemonsets --delete-emptydir-data 2>&1 | tail -6
```

```text
pod "sonde-hote" deleted from essai-ds namespace
node/k8s-w1.lab cordoned (server dry run)
Warning: ignoring DaemonSet-managed Pods: calico-system/calico-node-8x2wb, calico-system/csi-node-driver-lh854, essai-ds/sentinelle-l9n54, kube-system/kube-proxy-rfprv
evicting pod kube-system/coredns-7dc84c8f75-sckdv (server dry run)
node/k8s-w1.lab drained (server dry run)
```

La vidange passe : les Pods de DaemonSet restent sur le nœud, les autres
seraient évincés (ici, un Pod CoreDNS). Le nœud n'a pas bougé, puisque tout
était à blanc :

```bash
kubectl get nodes
```

```text
NAME         STATUS   ROLES           AGE   VERSION
k8s-cp.lab   Ready    control-plane   35h   v1.37.2
k8s-w1.lab   Ready    <none>          35h   v1.37.2
```

## 🧹 Nettoyage

Supprimez le namespace d'essai :

```bash
kubectl delete namespace essai-ds
```

```text
namespace "essai-ds" deleted
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset cka-daemonset-all-nodes
dsoxlab check cka-daemonset-all-nodes
```

```text
╭─ Résultat : cka-daemonset-all-nodes ─╮
│  0 / 100 pts                         │
│  ░░░░░░░░░░░░░░░░░░░░  0/5 tests     │
╰──────────────────────────────────────╯
```

0 sur 5 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : un agent sur chaque nœud, control plane compris,
sans retirer sa taint.

```bash
dsoxlab run cka-daemonset-all-nodes
dsoxlab challenge cka-daemonset-all-nodes
```
