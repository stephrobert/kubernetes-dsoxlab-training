# Lire ce que déclare un Node worker

Un **nœud** (Node) est une machine du cluster. Sur chaque nœud, un programme,
le **kubelet**, fait tourner les Pods et écrit sans arrêt dans le cluster ce
que la machine offre et comment elle va. La leçon montre comment lire ces
informations. Dans ce cours, vous provoquez des changements sur un nœud, puis
vous relisez ce qu'il déclare : un kubelet arrêté, un nœud qui revient, un Pod
système supprimé.

Vous travaillez sur le nœud `architecture-worker3`. Le challenge vous
demandera la fiche d'un autre nœud : vous la remplirez seul, à la fin.

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
20 novembre 2026.

## 📚 Exercice 1 : voir ce qui distingue deux nœuds

Sur ce cluster, les nœuds sont des conteneurs de la même machine : beaucoup de
leurs valeurs sont identiques. Comparez deux workers sur trois lignes de leur
fiche :

```bash
kubectl describe node architecture-worker | grep -E 'InternalIP|PodCIDR:|Machine ID'
kubectl describe node architecture-worker3 | grep -E 'InternalIP|PodCIDR:|Machine ID'
```

```text
  InternalIP:  172.18.0.7
  Machine ID:                 f524842260574d1fbf3b8ff528d7412d
PodCIDR:                      10.244.1.0/24
  InternalIP:  172.18.0.4
  Machine ID:                 6313db26e58b44398528deda41404384
PodCIDR:                      10.244.4.0/24
```

Ces trois valeurs sont propres à chaque nœud :

- `InternalIP` est l'adresse du nœud sur le réseau des machines ;
- `PodCIDR` est la plage d'adresses où les Pods de ce nœud reçoivent la leur :
  un Pod d'`architecture-worker3` aura une adresse en `10.244.4.x` ;
- `Machine ID` est l'identifiant de la machine, tiré au hasard à sa création.

Elles changent aussi quand le cluster est recréé : chez vous, elles seront
différentes. D'autres lignes, au contraire, sont les mêmes partout :

```bash
kubectl describe node architecture-worker3 | grep -E 'Kubelet Version|Container Runtime Version|^  memory'
```

```text
  memory:             4009788Ki
  memory:             4009788Ki
  Container Runtime Version:  containerd://2.3.4
  Kubelet Version:            v1.37.0
  memory             50Mi (1%)  0 (0%)
```

Les deux premières lignes `memory` viennent de `Capacity` et `Allocatable`, la
dernière de `Allocated resources` : la mémoire déjà réservée par les Pods du
nœud. Version du kubelet, runtime et mémoire sont les mêmes sur les quatre
nœuds de ce cluster.

## 📚 Exercice 2 : placer un Pod témoin et lire ses tolérances

Créez un namespace d'essai et un Deployment de quatre Pods, pour en avoir au
moins un sur `architecture-worker3` :

```bash
kubectl create namespace essai-noeud
kubectl create deployment temoin \
  --image=nginx:1.30@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb \
  --replicas=4 -n essai-noeud
kubectl wait --for=condition=Available deployment/temoin -n essai-noeud --timeout=180s
kubectl get pods -n essai-noeud -o wide --field-selector spec.nodeName=architecture-worker3
```

```text
namespace/essai-noeud created
deployment.apps/temoin created
deployment.apps/temoin condition met
NAME                      READY   STATUS    RESTARTS   AGE   IP            NODE                   NOMINATED NODE   READINESS GATES
temoin-556cf4ff8c-8w9th   1/1     Running   0          1s    10.244.4.12   architecture-worker3   <none>           <none>
```

L'option `--field-selector spec.nodeName=...` ne garde que les Pods de ce
nœud. Son adresse, `10.244.4.12`, est bien dans le `PodCIDR` du nœud.
Kubernetes a ajouté à ce Pod deux **tolérances**, des règles qui disent combien
de temps il reste sur un nœud en difficulté :

```bash
POD=$(kubectl get pods -n essai-noeud --field-selector spec.nodeName=architecture-worker3 -o jsonpath='{.items[0].metadata.name}')
kubectl describe pod $POD -n essai-noeud | sed -n '/^Tolerations:/,/^Events:/p'
```

```text
Tolerations:                 node.kubernetes.io/not-ready:NoExecute op=Exists for 300s
                             node.kubernetes.io/unreachable:NoExecute op=Exists for 300s
Events:
```

Si le nœud n'est plus prêt (`not-ready`) ou plus joignable (`unreachable`), ce
Pod y reste encore 300 secondes, puis il en est retiré. Gardez ce chiffre pour
l'exercice suivant.

## 📚 Exercice 3 : arrêter le kubelet d'un nœud

Toutes les dix secondes environ, le kubelet renouvelle un **bail** (Lease) au
nom de son nœud : c'est son battement de cœur. Lisez l'heure du dernier
renouvellement, puis arrêtez le kubelet d'`architecture-worker3`. Sur kind, le
nœud est un conteneur Docker : `docker exec` lance une commande dedans.

```bash
kubectl get lease -n kube-node-lease architecture-worker3 -o jsonpath='{.spec.renewTime}'; echo
docker exec architecture-worker3 systemctl stop kubelet
docker exec architecture-worker3 systemctl is-active kubelet
```

```text
2026-11-20T07:41:39.949102Z
inactive
```

Attendez une quinzaine de secondes, puis relisez le bail :

```bash
kubectl get lease -n kube-node-lease architecture-worker3 -o jsonpath='{.spec.renewTime}'; echo
date -u +%H:%M:%S
```

```text
2026-11-20T07:41:39.949102Z
07:41:56
```

L'heure du bail n'a pas bougé, alors que l'horloge a avancé de 17 secondes :
plus personne ne le renouvelle. Attendez encore une minute, puis regardez les
nœuds et la fiche d'`architecture-worker3` :

```bash
sleep 60
kubectl get nodes
kubectl describe node architecture-worker3 | grep -E '^Taints|unreachable|^  Ready'
```

```text
NAME                         STATUS     ROLES           AGE   VERSION
architecture-control-plane   Ready      control-plane   14m   v1.37.0
architecture-worker          Ready      <none>          14m   v1.37.0
architecture-worker2         Ready      <none>          14m   v1.37.0
architecture-worker3         NotReady   <none>          14m   v1.37.0
Taints:             node.kubernetes.io/unreachable:NoExecute
                    node.kubernetes.io/unreachable:NoSchedule
  Ready            Unknown   Fri, 20 Nov 2026 07:41:09 +0000   Fri, 20 Nov 2026 07:42:33 +0000   NodeStatusUnknown   Kubelet stopped posting node status.
```

Sur cette machine, le nœud est passé `NotReady` au bout d'une minute environ.
La condition `Ready` vaut `Unknown` : le cluster ne sait pas si le nœud est en
panne, il sait seulement que le kubelet ne donne plus de nouvelles. Il a posé
deux **marques** (taints) `unreachable` :

- `NoSchedule` : aucun nouveau Pod ne sera placé sur ce nœud ;
- `NoExecute` : les Pods déjà présents en seront retirés, après le délai de
  leur tolérance, soit 300 secondes pour votre Pod témoin.

Regardez ce Pod :

```bash
kubectl get pods -n essai-noeud -o wide --field-selector spec.nodeName=architecture-worker3
```

```text
NAME                      READY   STATUS    RESTARTS   AGE   IP            NODE                   NOMINATED NODE   READINESS GATES
temoin-556cf4ff8c-8w9th   1/1     Running   0          57s   10.244.4.12   architecture-worker3   <none>           <none>
```

Il affiche encore `Running`. C'est la dernière chose que le kubelet a dite au
cluster, avant de s'arrêter : le cluster n'en sait pas plus. Les 300 secondes
de sa tolérance ne sont pas écoulées.

## 📚 Exercice 4 : relancer le kubelet

Relancez le kubelet, attendez que le nœud soit prêt, puis relisez ses marques
deux fois, à dix secondes d'écart :

```bash
docker exec architecture-worker3 systemctl start kubelet
kubectl wait --for=condition=Ready node/architecture-worker3 --timeout=120s
kubectl describe node architecture-worker3 | grep -E '^Taints'
sleep 10
kubectl describe node architecture-worker3 | grep -E '^Taints'
```

```text
node/architecture-worker3 condition met
Taints:             node.kubernetes.io/unreachable:NoExecute
Taints:             <none>
```

Le nœud est `Ready` avant que la marque `NoExecute` soit retirée : quelques
secondes séparent les deux. Votre Pod témoin, lui, n'a pas bougé :

```bash
kubectl get pods -n essai-noeud -o wide --field-selector spec.nodeName=architecture-worker3
```

```text
NAME                      READY   STATUS    RESTARTS   AGE   IP            NODE                   NOMINATED NODE   READINESS GATES
temoin-556cf4ff8c-8w9th   1/1     Running   0          67s   10.244.4.12   architecture-worker3   <none>           <none>
```

Même nom, aucun redémarrage : le nœud est revenu avant la fin des 300
secondes, le Pod n'a pas été retiré.

## 📚 Exercice 5 : supprimer le kube-proxy d'un nœud

**kube-proxy** prépare, sur chaque nœud, les règles réseau qui font marcher
les Services. Il tourne sous la forme d'un **DaemonSet**, un objet qui place
un Pod sur chaque nœud. Supprimez celui d'`architecture-worker3` :

```bash
kubectl get pods -n kube-system -l k8s-app=kube-proxy -o wide --field-selector spec.nodeName=architecture-worker3
PROXY=$(kubectl get pods -n kube-system -l k8s-app=kube-proxy --field-selector spec.nodeName=architecture-worker3 -o jsonpath='{.items[0].metadata.name}')
kubectl delete pod $PROXY -n kube-system
```

```text
NAME               READY   STATUS    RESTARTS   AGE   IP           NODE                   NOMINATED NODE   READINESS GATES
kube-proxy-p9gxx   1/1     Running   0          88s   172.18.0.4   architecture-worker3   <none>           <none>
pod "kube-proxy-p9gxx" deleted from kube-system namespace
```

Attendez cinq secondes et regardez de nouveau :

```bash
kubectl get pods -n kube-system -l k8s-app=kube-proxy -o wide --field-selector spec.nodeName=architecture-worker3
kubectl get daemonset kube-proxy -n kube-system
```

```text
NAME               READY   STATUS    RESTARTS   AGE   IP           NODE                   NOMINATED NODE   READINESS GATES
kube-proxy-jhhlg   1/1     Running   0          6s    172.18.0.4   architecture-worker3   <none>           <none>
NAME         DESIRED   CURRENT   READY   UP-TO-DATE   AVAILABLE   NODE SELECTOR            AGE
kube-proxy   4         4         4       4            4           kubernetes.io/os=linux   15m
```

Un Pod neuf, `kube-proxy-jhhlg`, tourne déjà sur le même nœud. Le DaemonSet
veut un Pod par nœud : `DESIRED` vaut `4`, comme le nombre de nœuds. L'adresse
du Pod, `172.18.0.4`, est celle du nœud lui-même : kube-proxy utilise le
réseau de la machine, pas une adresse du `PodCIDR`.

## 🧹 Nettoyage

Supprimez d'abord ce que vous avez créé pendant les exercices : le namespace
d'essai, et le Pod témoin avec lui.

```bash
kubectl delete namespace essai-noeud
```

```text
namespace "essai-noeud" deleted
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
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
