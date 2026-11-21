# Lire les interfaces CRI, CNI et CSI d'un nœud

La leçon présente les trois interfaces par lesquelles le kubelet délègue son
travail : CRI pour le runtime de conteneurs, CNI pour le réseau des Pods, CSI
pour le stockage. Ce cours vous fait toucher à ce qui se trouve derrière ces
interfaces, sur le nœud, et ajoute des cas que la leçon ne montre pas : un
conteneur arrêté sans passer par l'API, le même conteneur vu par containerd,
l'espace réseau qu'a préparé le CNI, et l'accord entre le kubelet et
containerd sur les cgroups.

Vous travaillez dans un namespace d'essai, `essai-cri`, avec un Pod `cobaye`
placé sur le control plane. Le challenge porte sur d'autres questions : vous
le ferez seul, à la fin.

Page associée : [CNI, CSI et CRI](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/cni-csi-cri/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run k8s-lire-les-interfaces-d-un-noeud
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le nœud qui pilote le cluster
kubeadm (le control plane). Votre kubectl le vise déjà. Les outils du runtime,
`crictl` et `ctr`, demandent `sudo`.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
21 novembre 2026, avec Kubernetes v1.37.2.

Créez le namespace et un Pod nginx sur ce nœud, pour pouvoir l'observer de
près :

```bash
kubectl create namespace essai-cri; kubectl run cobaye --image=nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb -n essai-cri --overrides='{"spec":{"nodeName":"k8s-cp.lab"}}'; kubectl wait --for=condition=Ready pod/cobaye -n essai-cri --timeout=120s
```

```text
namespace/essai-cri created
pod/cobaye created
pod/cobaye condition met
```

## 🛑 Exercice 1 : arrêter un conteneur sans passer par l'API

`crictl` parle au runtime par l'interface CRI, comme le kubelet. Trouvez le
conteneur du Pod :

```bash
sudo crictl ps --name cobaye -o json | python3 -c 'import json,sys; c=json.load(sys.stdin)["containers"][0]; print(c["id"][:13], c["state"])'
```

```text
1a5f03e39416f CONTAINER_RUNNING
```

Arrêtez-le directement, sans rien demander à l'API, attendez 15 secondes, et
regardez le Pod :

```bash
C=$(sudo crictl ps --name cobaye -q | head -1); sudo crictl stop $C >/dev/null; sleep 15; kubectl get pod cobaye -n essai-cri -o jsonpath='redémarrages={.status.containerStatuses[0].restartCount} dernier arrêt={.status.containerStatuses[0].lastState.terminated.reason}{"\n"}'
```

```text
redémarrages=1 dernier arrêt=Error
```

Le kubelet a vu le conteneur arrêté et l'a relancé : un redémarrage, avec
`Error` comme raison du dernier arrêt. L'API reste la source de vérité. Ce que
vous changez à la main sur le nœud, le kubelet le ramène à ce que l'API
demande.

## 📦 Exercice 2 : le même conteneur vu par containerd

`ctr` est l'outil de containerd lui-même, sous l'interface CRI. containerd
range ses objets par espaces de noms, qui n'ont rien à voir avec ceux de
Kubernetes :

```bash
sudo ctr namespaces list
```

```text
NAME   LABELS 
k8s.io        
```

Kubernetes utilise l'espace `k8s.io`. Cherchez-y le conteneur de `cobaye`,
puis regardez l'espace `default` :

```bash
C=$(sudo crictl ps --name cobaye -q | head -1); sudo ctr -n k8s.io containers list | grep ${C:0:12} | cut -c1-120; echo "--- espace default :"; sudo ctr -n default containers list
```

```text
aa6998223b7e400850d6898929ea2bf767100345905b31e9d2492ae6ef4ffe62    docker.io/library/nginx@sha256:9bf97bd7714f5e24c1ccd
--- espace default :
CONTAINER    IMAGE    RUNTIME    
```

Le conteneur est dans `k8s.io`, avec son identifiant complet et l'image
épinglée. `default` est vide. Un `ctr containers list` sans `-n k8s.io` ne
montre donc rien des conteneurs de Kubernetes, et fait croire à tort que le
nœud est vide.

## 🌐 Exercice 3 : entrer dans l'espace réseau du Pod

Le CNI prépare, pour chaque Pod, un espace réseau du noyau. Lisez son chemin
dans la description du Pod faite par le runtime :

```bash
P=$(sudo crictl pods --name cobaye -q | head -1); sudo crictl inspectp $P | python3 -c 'import json,sys; d=json.load(sys.stdin); print([n["path"] for n in d["info"]["runtimeSpec"]["linux"]["namespaces"] if n["type"]=="network"])'
```

```text
['/var/run/netns/cni-d4842914-f343-e68d-eb7d-683afeb59948']
```

Entrez dans cet espace avec `nsenter`, listez ses interfaces, et comparez avec
l'adresse que l'API annonce :

```bash
P=$(sudo crictl pods --name cobaye -q | head -1); NS=$(sudo crictl inspectp $P | python3 -c 'import json,sys; d=json.load(sys.stdin); print([n["path"] for n in d["info"]["runtimeSpec"]["linux"]["namespaces"] if n["type"]=="network"][0])'); sudo nsenter --net=$NS ip -br addr; kubectl get pod cobaye -n essai-cri -o jsonpath='IP annoncée : {.status.podIP}{"\n"}'
```

```text
lo               UNKNOWN        127.0.0.1/8 ::1/128 
eth0@if242       UP             10.244.163.39/32 fe80::681f:deff:fe64:5e8a/64 
IP annoncée : 10.244.163.39
```

L'interface `eth0` porte l'adresse annoncée par l'API, et son autre bout est
l'interface n° 242 du nœud (`@if242`). C'est le CNI (ici Calico) qui a créé
cette paire et posé l'adresse. `nsenter` permet de diagnostiquer le réseau
d'un Pod même quand son image n'a aucun outil.

## ⚙️ Exercice 4 : kubelet et containerd d'accord sur les cgroups

Le kubelet et le runtime doivent gérer les cgroups (les limites de ressources
du noyau) de la même façon. Lisez le réglage de chacun :

```bash
sudo grep -E '^cgroupDriver' /var/lib/kubelet/config.yaml; sudo grep -n 'SystemdCgroup' /etc/containerd/config.toml
```

```text
cgroupDriver: systemd
109:            SystemdCgroup = true
```

Les deux utilisent systemd. Un désaccord entre les deux fait tomber le
kubelet ou redémarrer les Pods sans raison apparente. C'est une des premières
vérifications sur un nœud qui ne devient pas Ready.

## 🧹 Nettoyage

Supprimez le namespace d'essai :

```bash
kubectl delete namespace essai-cri
```

```text
namespace "essai-cri" deleted
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset k8s-lire-les-interfaces-d-un-noeud
dsoxlab check k8s-lire-les-interfaces-d-un-noeud
```

```text
╭─ Résultat : k8s-lire-les-interfaces-d-un-noeud ─╮
│  0 / 100 pts                                    │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests                │
╰─────────────────────────────────────────────────╯
```

0 sur 4 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : relever ce que le nœud utilise pour chacune des
trois interfaces, et l'écrire dans un fichier de réponses.

```bash
dsoxlab run k8s-lire-les-interfaces-d-un-noeud
dsoxlab challenge k8s-lire-les-interfaces-d-un-noeud
```
