# Rendre lisible la santé d'un cluster et rédiger son bulletin

La leçon montre comment lire la santé d'un cluster : les points de contrôle de
l'API server, `kubectl top`, ce que les Pods réservent sur chaque nœud. Ce
cours va voir ce qu'il y a derrière ces outils, et ajoute des cas que la
leçon ne montre pas : le détail des contrôles de `/readyz`, la mesure du
kubelet lue sans metrics-server, et la mémoire réservée par nœud recalculée à
la main.

Vous travaillez dans un namespace d'essai, `essai-sante`, avec deux Pods,
`glouton` et `sobre`. Le challenge porte sur un autre namespace : vous le
ferez seul, à la fin.

Page associée : [Observer la santé d'un cluster Kubernetes](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/operer/observer-sante-cluster-kubernetes/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run k8s-observer-la-sante-d-un-cluster
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le nœud qui pilote le cluster
kubeadm (le control plane). Votre kubectl le vise déjà.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
21 novembre 2026, avec Kubernetes v1.37.2.

## 🩺 Exercice 1 : le détail des contrôles de l'API server

`/readyz` dit si l'API server est prêt à servir. Avec `?verbose`, il détaille
chaque contrôle. Lisez la fin de la liste :

```bash
kubectl get --raw '/readyz?verbose' | tail -6
```

```text
[+]poststarthook/kube-apiserver-autoregistration ok
[+]autoregister-completion ok
[+]poststarthook/apiservice-openapi-controller ok
[+]poststarthook/apiservice-openapiv3-controller ok
[+]shutdown ok
readyz check passed
```

Chaque ligne `[+]` est un contrôle réussi, et la dernière ligne donne le
verdict. Un contrôle peut aussi se demander seul, ou s'exclure :

```bash
kubectl get --raw '/readyz/etcd'; echo; kubectl get --raw '/livez?exclude=etcd' ; echo
```

```text
ok
ok
```

`/readyz/etcd` ne teste que l'accès à etcd. `/livez?exclude=etcd` dit si le
processus est vivant sans tenir compte d'etcd. Quand l'API répond mal, ces
adresses disent tout de suite quel composant est en cause.

## 📏 Exercice 2 : ce que mesure le kubelet, sans metrics-server

Créez deux Pods : `glouton` remplit 48 Mi de mémoire, `sobre` ne fait rien.
La commande attend ensuite 20 secondes, le temps que le kubelet les mesure :

```bash
kubectl create namespace essai-sante; kubectl run glouton --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-sante -- sh -c 'dd if=/dev/zero of=/dev/shm/bloc bs=1M count=48; sleep 3600'; kubectl run sobre --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-sante -- sleep 3600; kubectl wait --for=condition=Ready pod --all -n essai-sante --timeout=120s; sleep 20
```

```text
namespace/essai-sante created
pod/glouton created
pod/sobre created
pod/glouton condition met
pod/sobre condition met
```

Le kubelet mesure lui-même la consommation de chaque Pod, et la publie dans
un résumé que l'API server sait relayer (`/proxy/stats/summary`). Lisez la
mémoire de vos deux Pods dans ce résumé :

```bash
N=$(kubectl get pod glouton -n essai-sante -o jsonpath='{.spec.nodeName}'); kubectl get --raw /api/v1/nodes/$N/proxy/stats/summary | python3 -c 'import json,sys; d=json.load(sys.stdin); [print(p["podRef"]["name"], p["memory"]["workingSetBytes"]//1048576, "Mi") for p in d["pods"] if p["podRef"]["namespace"]=="essai-sante"]'
```

```text
glouton 48 Mi
sobre 0 Mi
```

48 Mi pour `glouton`, rien pour `sobre`. C'est cette mesure que metrics-server
collecte sur chaque nœud pour répondre à `kubectl top`. Sur ce cluster,
regardez s'il est enregistré :

```bash
kubectl get apiservice v1beta1.metrics.k8s.io -o jsonpath='{.status.conditions[0].type}={.status.conditions[0].status} ({.status.conditions[0].reason}){"\n"}'
```

```text
Error from server (NotFound): apiservices.apiregistration.k8s.io "v1beta1.metrics.k8s.io" not found
```

La Metrics API n'existe pas : `kubectl top` ne peut pas répondre. La rendre
disponible est l'objet du challenge. En attendant, le résumé du kubelet
reste lisible : la mesure existe, c'est son relais qui manque.

## 🧮 Exercice 3 : la mémoire réservée par les Pods de chaque nœud

Additionnez, nœud par nœud, les demandes de mémoire (`requests`) des
conteneurs de tous les Pods en marche ou en attente :

```bash
kubectl get pods -A -o json | python3 -c '
import json,sys,collections
def mi(v):
    u={"Ki":1/1024,"Mi":1,"Gi":1024}
    for s,f in u.items():
        if v.endswith(s): return float(v[:-2])*f
    return float(v)/1048576
total=collections.Counter()
for p in json.load(sys.stdin)["items"]:
    if p["status"].get("phase") not in ("Running","Pending"): continue
    for c in p["spec"]["containers"]:
        total[p["spec"].get("nodeName","?")]+=mi(c.get("resources",{}).get("requests",{}).get("memory","0"))
for n,v in sorted(total.items()): print(n, round(v), "Mi demandés")'
```

```text
k8s-cp.lab 240 Mi demandés
k8s-w1.lab 64 Mi demandés
```

Comparez avec le total que `kubectl describe node` affiche pour chaque nœud :

```bash
for n in $(kubectl get nodes -o jsonpath='{.items[*].metadata.name}'); do printf '%s : ' $n; kubectl describe node $n | awk '/Allocated resources/{f=1} f&&/memory/{print $2, $3; exit}'; done
```

```text
k8s-cp.lab : 240Mi (6%)
k8s-w1.lab : 64Mi (2%)
```

Les mêmes chiffres. Ce total est une réservation, pas une consommation :
`glouton` utilise 48 Mi mais n'en demande aucun, et n'est pas compté. Le
scheduler place les Pods d'après les demandes, jamais d'après la
consommation.

## 🧹 Nettoyage

Supprimez le namespace d'essai :

```bash
kubectl delete namespace essai-sante
```

```text
namespace "essai-sante" deleted
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset k8s-observer-la-sante-d-un-cluster
dsoxlab check k8s-observer-la-sante-d-un-cluster
```

```text
╭─ Résultat : k8s-observer-la-sante-d-un-cluster ─╮
│  0 / 100 pts                                    │
│  ░░░░░░░░░░░░░░░░░░░░  0/3 tests                │
╰─────────────────────────────────────────────────╯
```

0 sur 3 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : rendre `kubectl top` disponible, puis rédiger le
bulletin de santé d'un namespace.

```bash
dsoxlab run k8s-observer-la-sante-d-un-cluster
dsoxlab challenge k8s-observer-la-sante-d-un-cluster
```
