# Ramener un nœud NotReady dans le cluster

La leçon montre comment dépanner un nœud `NotReady`. Dans ce lab, le worker
est en panne : c'est le challenge. Ce cours arrête une minute le kubelet du
control plane, pour observer ce que voit le cluster quand un nœud se tait, et
ajoute des cas que la leçon ne montre pas : le bail que le nœud renouvelle,
les conditions qui passent à `Unknown`, les taints posées par le contrôleur,
et le retour quand l'agent repart.

L'API server continue de répondre pendant l'arrêt : c'est un Pod statique
déjà lancé, et le kubelet arrêté ne le tue pas.

Page associée : [Dépanner un nœud Kubernetes](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/operer/depanner-un-noeud-kubernetes/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run cka-troubleshoot-node-notready
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le nœud qui pilote le cluster
kubeadm (le control plane). Votre kubectl le vise déjà.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
21 novembre 2026, avec Kubernetes v1.37.2.

## 💓 Exercice 1 : le battement de cœur d'un nœud

Chaque nœud renouvelle un bail (un objet Lease du namespace
`kube-node-lease`) toutes les quelques secondes. Lisez sa date de
renouvellement deux fois, à 12 secondes d'écart :

```bash
kubectl get lease k8s-cp.lab -n kube-node-lease -o jsonpath='renouvelé={.spec.renewTime}{"\n"}'; date -u +'maintenant=%Y-%m-%dT%H:%M:%S'; sleep 12; kubectl get lease k8s-cp.lab -n kube-node-lease -o jsonpath='renouvelé={.spec.renewTime}{"\n"}'; date -u +'maintenant=%Y-%m-%dT%H:%M:%S'
```

```text
renouvelé=2026-11-21T06:29:46.643024Z
maintenant=2026-11-21T06:29:53
renouvelé=2026-11-21T06:29:56.870270Z
maintenant=2026-11-21T06:30:05
```

Le bail a été renouvelé entre les deux lectures. Lisez aussi les conditions du
nœud :

```bash
kubectl get node k8s-cp.lab -o jsonpath='{range .status.conditions[*]}{.type}={.status} ({.lastHeartbeatTime}){"\n"}{end}'
```

```text
NetworkUnavailable=False (2026-11-21T05:56:25Z)
MemoryPressure=False (2026-11-21T06:29:26Z)
DiskPressure=False (2026-11-21T06:29:26Z)
PIDPressure=False (2026-11-21T06:29:26Z)
Ready=True (2026-11-21T06:29:26Z)
```

Tout va bien, et chaque condition porte la date du dernier rapport du kubelet.

## 🔇 Exercice 2 : arrêter l'agent du control plane

Arrêtez le kubelet de ce nœud, et attendez que le cluster le déclare `Unknown`.
La commande chronomètre l'attente :

```bash
sudo systemctl stop kubelet; debut=$(date +%s); kubectl wait --for=condition=Ready=Unknown node/k8s-cp.lab --timeout=180s; echo "NotReady au bout de $(( $(date +%s) - debut )) s"; kubectl get lease k8s-cp.lab -n kube-node-lease -o jsonpath='renouvelé={.spec.renewTime}{"\n"}'; date -u +'maintenant=%Y-%m-%dT%H:%M:%S'; kubectl get nodes
```

```text
node/k8s-cp.lab condition met
NotReady au bout de 46 s
renouvelé=2026-11-21T06:29:56.870270Z
maintenant=2026-11-21T06:30:51
NAME         STATUS     ROLES           AGE    VERSION
k8s-cp.lab   NotReady   control-plane   157m   v1.37.2
k8s-w1.lab   NotReady   <none>          150m   v1.37.2
```

Au bout d'une quarantaine de secondes sans bail renouvelé, le contrôleur des
nœuds a marqué `k8s-cp.lab` `NotReady`. Le worker est `NotReady` lui aussi,
mais pour une autre raison : c'est le challenge. Lisez les conditions et les
taints :

```bash
kubectl get node k8s-cp.lab -o jsonpath='{range .status.conditions[*]}{.type}={.status} {.reason}{"\n"}{end}{range .spec.taints[*]}taint {.key}:{.effect}{"\n"}{end}'
```

```text
NetworkUnavailable=False CalicoIsUp
MemoryPressure=Unknown NodeStatusUnknown
DiskPressure=Unknown NodeStatusUnknown
PIDPressure=Unknown NodeStatusUnknown
Ready=Unknown NodeStatusUnknown
taint node.kubernetes.io/unreachable:NoSchedule
taint node.kubernetes.io/unreachable:NoExecute
```

Toutes les conditions venant du kubelet passent à `Unknown` : personne ne
répond plus pour elles. Le contrôleur pose deux taints `unreachable`.
`NoSchedule` bloque les nouveaux Pods. `NoExecute` expulse les Pods du nœud :
chaque Pod reçoit d'office une tolérance de 300 secondes pour cette taint, il
est donc expulsé au bout de 5 minutes d'absence.

## 🔊 Exercice 3 : l'agent repart, le nœud revient

Relancez le kubelet, attendez que le nœud soit `Ready`, et relisez les taints
tout de suite :

```bash
sudo systemctl start kubelet; kubectl wait --for=condition=Ready node/k8s-cp.lab --timeout=120s; kubectl get node k8s-cp.lab -o jsonpath='{range .spec.taints[*]}taint {.key}:{.effect}{"\n"}{end}'
```

```text
node/k8s-cp.lab condition met
taint node.kubernetes.io/unreachable:NoExecute
```

Le nœud est `Ready`, mais la taint `NoExecute` est encore là. Relisez 10
secondes plus tard :

```bash
sleep 10; kubectl get node k8s-cp.lab -o jsonpath='taints={.spec.taints}{"\n"}'
```

```text
taints=
```

Plus aucune taint : le contrôleur les retire peu après le retour du nœud. Un
nœud `NotReady` quelques minutes ne laisse donc pas de trace, à condition que
ses Pods aient toléré l'absence.

## 🧹 Nettoyage

Vérifiez que le kubelet tourne et que le nœud est prêt :

```bash
systemctl is-active kubelet; kubectl get node k8s-cp.lab
```

```text
active
NAME         STATUS   ROLES           AGE    VERSION
k8s-cp.lab   Ready    control-plane   157m   v1.37.2
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset cka-troubleshoot-node-notready
dsoxlab check cka-troubleshoot-node-notready
```

```text
╭─ Résultat : cka-troubleshoot-node-notready ─╮
│  0 / 100 pts                                │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests            │
╰─────────────────────────────────────────────╯
```

0 sur 4 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : un worker `NotReady` à ramener dans le cluster, et
pour de bon.

```bash
dsoxlab run cka-troubleshoot-node-notready
dsoxlab challenge cka-troubleshoot-node-notready
```
