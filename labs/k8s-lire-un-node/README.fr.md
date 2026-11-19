# Lire ce que déclare un Node worker

Un **nœud** (Node) est une machine du cluster. Sur chaque nœud, un programme,
le **kubelet**, fait tourner les Pods et écrit sans arrêt dans le cluster ce
que la machine offre et comment elle va. Dans ce cours, vous apprenez à lire
ces informations, comme dans la leçon :

- le **battement de cœur** du kubelet, qui dit que le nœud est vivant ;
- la **vue d'ensemble** de tous les nœuds, puis la **fiche** d'un seul ;
- **kube-proxy**, présent sur chaque nœud ;
- ce qui se passe quand un nœud **ne répond plus**.

Vous lisez surtout le nœud `architecture-worker3`. Le challenge vous demandera
la fiche d'un autre nœud : vous la remplirez seul, à la fin.

Page associée : [Fonctionnement des Worker Nodes Kubernetes](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/worker-nodes/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run k8s-lire-un-node
```

Vous êtes maintenant connecté à la machine `k8s-kind.lab`. Le cluster kind
`architecture` y tourne, avec un control plane et trois workers, et votre
kubectl le vise déjà.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
19 novembre 2026.

## 📚 Exercice 1 : voir le battement de cœur du kubelet

Toutes les dix secondes, le kubelet renouvelle un petit objet, un **bail**
(Lease), qui porte le nom de son nœud. Listez les baux :

```bash
kubectl get lease -n kube-node-lease
```

```text
NAME                         HOLDER                       AGE
architecture-control-plane   architecture-control-plane   10m
architecture-worker          architecture-worker          10m
architecture-worker2         architecture-worker2         10m
architecture-worker3         architecture-worker3         10m
```

Un bail par nœud. Lisez l'heure de renouvellement de celui
d'`architecture-worker3`, deux fois, à dix secondes d'écart :

```bash
kubectl get lease -n kube-node-lease architecture-worker3 -o jsonpath='{.spec.renewTime}'; echo
sleep 10
kubectl get lease -n kube-node-lease architecture-worker3 -o jsonpath='{.spec.renewTime}'; echo
```

```text
2026-11-19T11:12:13.857703Z
2026-11-19T11:12:23.871343Z
```

L'heure a avancé de dix secondes : le kubelet a renouvelé son bail. Tant qu'il
le fait, le cluster sait que le nœud est vivant.

## 📚 Exercice 2 : voir tous les nœuds d'un coup

```bash
kubectl get nodes -o wide
```

```text
NAME                         STATUS   ROLES           AGE   VERSION   INTERNAL-IP   EXTERNAL-IP   OS-IMAGE                       KERNEL-VERSION                 CONTAINER-RUNTIME
architecture-control-plane   Ready    control-plane   10m   v1.37.0   172.18.0.2    <none>        Debian GNU/Linux 13 (trixie)   6.12.117+deb13-amd64 (amd64)   containerd://2.3.4
architecture-worker          Ready    <none>          10m   v1.37.0   172.18.0.5    <none>        Debian GNU/Linux 13 (trixie)   6.12.117+deb13-amd64 (amd64)   containerd://2.3.4
architecture-worker2         Ready    <none>          10m   v1.37.0   172.18.0.7    <none>        Debian GNU/Linux 13 (trixie)   6.12.117+deb13-amd64 (amd64)   containerd://2.3.4
architecture-worker3         Ready    <none>          10m   v1.37.0   172.18.0.6    <none>        Debian GNU/Linux 13 (trixie)   6.12.117+deb13-amd64 (amd64)   containerd://2.3.4
```

Trois colonnes répondent aux questions de la leçon :

- `STATUS` : `Ready` veut dire que le kubelet signale un nœud prêt ;
- `VERSION` : la version du kubelet, ici `v1.37.0` ;
- `CONTAINER-RUNTIME` : le programme qui lance vraiment les conteneurs, et sa
  version, ici `containerd://2.3.4`.

## 📚 Exercice 3 : n'afficher que les colonnes utiles

L'option `-o custom-columns` affiche seulement les champs que vous choisissez,
sous la forme `TITRE:chemin.du.champ`. Affichez la **capacité** de chaque
nœud :

```bash
kubectl get nodes -o custom-columns=NOM:.metadata.name,CPU:.status.capacity.cpu,MEMOIRE:.status.capacity.memory,PODS:.status.capacity.pods
```

```text
NOM                          CPU   MEMOIRE     PODS
architecture-control-plane   2     4009780Ki   110
architecture-worker          2     4009780Ki   110
architecture-worker2         2     4009780Ki   110
architecture-worker3         2     4009780Ki   110
```

Les quatre nœuds ont la même capacité : ce sont des conteneurs qui partagent
la même machine. Sur un vrai cluster, chaque nœud a la sienne. `PODS` vaut
110, le nombre maximal de Pods par nœud.

## 📚 Exercice 4 : lire la fiche d'un nœud

`kubectl describe node` affiche tout ce que le cluster sait d'un nœud. La
sortie est longue : `sed` n'en garde qu'une partie à la fois. Commencez par
les **conditions** :

```bash
kubectl describe node architecture-worker3 | sed -n '/^Conditions:/,/^Addresses:/p'
```

```text
Conditions:
  Type             Status  LastHeartbeatTime                 LastTransitionTime                Reason                       Message
  ----             ------  -----------------                 ------------------                ------                       -------
  MemoryPressure   False   Thu, 19 Nov 2026 11:10:52 +0000   Thu, 19 Nov 2026 11:02:01 +0000   KubeletHasSufficientMemory   kubelet has sufficient memory available
  DiskPressure     False   Thu, 19 Nov 2026 11:10:52 +0000   Thu, 19 Nov 2026 11:02:01 +0000   KubeletHasNoDiskPressure     kubelet has no disk pressure
  PIDPressure      False   Thu, 19 Nov 2026 11:10:52 +0000   Thu, 19 Nov 2026 11:02:01 +0000   KubeletHasSufficientPID      kubelet has sufficient PID available
  Ready            True    Thu, 19 Nov 2026 11:10:52 +0000   Thu, 19 Nov 2026 11:02:16 +0000   KubeletReady                 kubelet is posting ready status
Addresses:
```

Les trois premières conditions signalent un problème quand elles valent
`True` : manque de mémoire, de disque ou de processus. `Ready`, elle, doit
valoir `True`. Un nœud en bonne santé affiche donc `False`, `False`,
`False`, `True`.

Lisez ensuite ce que la machine possède et ce qui reste pour les Pods :

```bash
kubectl describe node architecture-worker3 | sed -n '/^Capacity:/,/^System Info:/p'
```

```text
Capacity:
  cpu:                2
  ephemeral-storage:  31491104768
  hugepages-1Gi:      0
  hugepages-2Mi:      0
  memory:             4009780Ki
  pods:               110
Allocatable:
  cpu:                2
  ephemeral-storage:  31491104768
  hugepages-1Gi:      0
  hugepages-2Mi:      0
  memory:             4009780Ki
  pods:               110
System Info:
```

`Capacity` est ce que la machine possède. `Allocatable` est ce qui reste aux
Pods, une fois la part du système retirée. Ici les deux sont égaux, parce que
kind ne réserve rien pour le système.

Enfin, les versions :

```bash
kubectl describe node architecture-worker3 | grep -E 'Container Runtime Version|Kubelet Version'
```

```text
  Container Runtime Version:  containerd://2.3.4
  Kubelet Version:            v1.37.0
```

Ce sont les mêmes valeurs que les colonnes de l'exercice 2, lues cette fois
dans la fiche du nœud.

## 📚 Exercice 5 : voir kube-proxy sur chaque nœud

**kube-proxy** prépare, sur chaque nœud, les règles réseau qui font marcher
les Services. Son mode de fonctionnement se lit dans sa configuration :

```bash
kubectl -n kube-system get configmap kube-proxy -o yaml | grep 'mode:'
```

```text
    mode: iptables
```

Il tourne sous la forme d'un **DaemonSet**, un objet qui place un Pod sur
chaque nœud :

```bash
kubectl get pods -n kube-system -l k8s-app=kube-proxy -o wide
```

```text
NAME               READY   STATUS    RESTARTS   AGE   IP           NODE                         NOMINATED NODE   READINESS GATES
kube-proxy-6zbcq   1/1     Running   0          10m   172.18.0.7   architecture-worker2         <none>           <none>
kube-proxy-gsm7l   1/1     Running   0          10m   172.18.0.6   architecture-worker3         <none>           <none>
kube-proxy-hskwd   1/1     Running   0          10m   172.18.0.2   architecture-control-plane   <none>           <none>
kube-proxy-mscg7   1/1     Running   0          10m   172.18.0.5   architecture-worker          <none>           <none>
```

Regardez la colonne `NODE` : exactement un Pod `kube-proxy` par nœud, control
plane compris.

## 📚 Exercice 6 : arrêter un nœud, puis le relancer

Sur kind, un nœud est un conteneur Docker. Arrêtez celui
d'`architecture-worker3` (rien n'est détruit), puis regardez les nœuds tout
de suite :

```bash
docker stop architecture-worker3
kubectl get nodes
```

```text
architecture-worker3
NAME                         STATUS   ROLES           AGE   VERSION
architecture-control-plane   Ready    control-plane   10m   v1.37.0
architecture-worker          Ready    <none>          10m   v1.37.0
architecture-worker2         Ready    <none>          10m   v1.37.0
architecture-worker3         Ready    <none>          10m   v1.37.0
```

Le nœud est encore `Ready` : le cluster ne sait pas encore qu'il est arrêté.
Attendez une minute, puis regardez de nouveau :

```bash
sleep 60
kubectl get nodes
```

```text
NAME                         STATUS     ROLES           AGE   VERSION
architecture-control-plane   Ready      control-plane   11m   v1.37.0
architecture-worker          Ready      <none>          11m   v1.37.0
architecture-worker2         Ready      <none>          11m   v1.37.0
architecture-worker3         NotReady   <none>          11m   v1.37.0
```

`NotReady` : le kubelet ne renouvelle plus son bail, et au bout d'environ
50 secondes le cluster le considère perdu. Sa fiche le dit :

```bash
kubectl describe node architecture-worker3 | grep -E '^Taints|unreachable|^  Ready'
```

```text
Taints:             node.kubernetes.io/unreachable:NoExecute
                    node.kubernetes.io/unreachable:NoSchedule
  Ready            Unknown   Thu, 19 Nov 2026 11:10:52 +0000   Thu, 19 Nov 2026 11:13:14 +0000   NodeStatusUnknown   Kubelet stopped posting node status.
```

La condition `Ready` vaut `Unknown`, avec le message `Kubelet stopped posting
node status`. Le cluster a aussi posé deux **marques** (taints)
`unreachable` : plus aucun nouveau Pod n'ira sur ce nœud. Relancez-le et
attendez qu'il revienne :

```bash
docker start architecture-worker3
kubectl wait --for=condition=Ready node/architecture-worker3 --timeout=120s
kubectl get nodes
```

```text
architecture-worker3
node/architecture-worker3 condition met
NAME                         STATUS   ROLES           AGE   VERSION
architecture-control-plane   Ready    control-plane   11m   v1.37.0
architecture-worker          Ready    <none>          11m   v1.37.0
architecture-worker2         Ready    <none>          11m   v1.37.0
architecture-worker3         Ready    <none>          11m   v1.37.0
```

Le nœud est de nouveau `Ready`.

## 🧹 Nettoyage

Les exercices n'ont rien créé : vous avez seulement lu, puis arrêté et relancé
un nœud. Quittez la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset k8s-lire-un-node
dsoxlab check k8s-lire-un-node
```

```text
╭─── Résultat : k8s-lire-un-node ───╮
│  0 / 100 pts                      │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests  │
╰───────────────────────────────────╯
```

0 sur 4 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : remplir la fiche du nœud `architecture-worker2`
avec ce qu'il déclare de lui-même.

```bash
dsoxlab run k8s-lire-un-node
dsoxlab challenge k8s-lire-un-node
```
