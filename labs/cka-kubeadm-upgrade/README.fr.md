# Monter un cluster d'une version mineure, sans interrompre ce qui tourne

La leçon montre la montée de version d'un cluster kubeadm, nœud par nœud. Ici,
la montée est le challenge : ce cours ne monte aucune version. Il prépare la
montée et mesure ce qu'elle ferait, avec des cas que la leçon ne montre pas :
les versions que le dépôt propose, ce que dit le plan quand kubeadm est en
retard, ce qui changerait dans les manifestes, et une montée jouée à blanc.

Page associée : [Mettre à jour un cluster Kubernetes sans interruption](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/operer/mettre-a-jour-cluster-kubernetes/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run cka-kubeadm-upgrade
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le nœud qui pilote le cluster
kubeadm (le control plane). Votre kubectl le vise déjà. La préparation du lab
a posé un cluster en v1.36 : c'est lui que vous monterez dans le challenge.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
21 novembre 2026.

## 🔢 Exercice 1 : les versions en présence

Lisez la version de l'API server, celle de chaque kubelet, puis celles que le
dépôt de paquets propose :

```bash
kubectl version 2>/dev/null | grep -E 'Server|Client'; kubectl get nodes -o custom-columns=NOEUD:.metadata.name,KUBELET:.status.nodeInfo.kubeletVersion
```

```text
Client Version: v1.36.4
Server Version: v1.36.6
NOEUD        KUBELET
k8s-cp.lab   v1.36.4
k8s-w1.lab   v1.36.4
```

L'API server est en v1.36.6, les kubelets en v1.36.4 : un kubelet peut avoir
quelques versions de retard sur l'API server, jamais d'avance.

```bash
apt-cache madison kubeadm | head -4; apt-mark showhold
```

```text
   kubeadm | 1.37.2-1.1 | https://pkgs.k8s.io/core:/stable:/v1.37/deb  Packages
   kubeadm | 1.37.1-1.1 | https://pkgs.k8s.io/core:/stable:/v1.37/deb  Packages
   kubeadm | 1.37.0-1.1 | https://pkgs.k8s.io/core:/stable:/v1.37/deb  Packages
   kubeadm | 1.36.6-1.1 | https://pkgs.k8s.io/core:/stable:/v1.36/deb  Packages
kubeadm
kubectl
kubelet
```

Le dépôt propose plusieurs versions de la série v1.37. Les trois paquets sont
**bloqués** (`apt-mark hold`) : un `apt upgrade` ordinaire ne les montera pas
par accident. Il faudra les débloquer, un par un, au moment voulu.

## 🗺️ Exercice 2 : ce que dit le plan

`kubeadm upgrade plan` dit vers quelle version le cluster peut monter :

```bash
sudo kubeadm upgrade plan 2>&1 | grep -E 'upgrade/versions|falling back'
```

```text
[upgrade/versions] Cluster version: 1.36.6
[upgrade/versions] kubeadm version: v1.36.4
I1121 10:38:54.539512   23758 version.go:260] remote version is much newer: v1.37.2; falling back to: stable-1.36
[upgrade/versions] Target version: v1.36.6
[upgrade/versions] Latest version in the v1.36 series: v1.36.6
```

Le plan voit bien la v1.37.2, mais il « se replie » sur la série v1.36 : un
kubeadm ne propose jamais que la dernière version de sa propre série. Pour
qu'il propose la v1.37, il faut d'abord que kubeadm lui-même soit en v1.37.

## 🔍 Exercice 3 : ce que la montée changerait dans les manifestes

`kubeadm upgrade diff` montre, sans rien appliquer, les changements que la
montée ferait dans les manifestes statiques du control plane :

```bash
V=$(apt-cache madison kubeadm | awk '{print $3}' | sort -V | tail -1 | cut -d- -f1); echo "version visée : v$V"; sudo kubeadm upgrade diff v$V 2>&1 | grep -E '^[-+] .*image:' | head -6
```

```text
version visée : v1.37.2
-    image: registry.k8s.io/kube-controller-manager:v1.36.6
+    image: registry.k8s.io/kube-controller-manager:v1.37.2
-    image: registry.k8s.io/kube-scheduler:v1.36.6
+    image: registry.k8s.io/kube-scheduler:v1.37.2
-    image: registry.k8s.io/kube-apiserver:v1.36.6
+    image: registry.k8s.io/kube-apiserver:v1.37.2
```

Chaque composant du control plane changerait d'image. Rien n'est écrit sur
le disque.

## 🧪 Exercice 4 : une montée jouée à blanc

`--dry-run` déroule la montée sans rien appliquer. Essayez-la vers la même
version :

```bash
V=$(apt-cache madison kubeadm | awk '{print $3}' | sort -V | tail -1 | cut -d- -f1); sudo kubeadm upgrade apply v$V --dry-run --yes 2>&1 | grep -E 'Specified version|^error'
```

```text
error: error execution phase preflight: the version argument is invalid due to these fatal errors:
	- Specified version to upgrade to "v1.37.2" is at least one minor release higher than the kubeadm minor release (37 > 36). Such an upgrade is not supported
```

Le contrôle préalable refuse : kubeadm v1.36 ne sait pas monter un cluster en
v1.37. C'est la même règle que le plan, dite cette fois par une erreur.
Vérifiez que rien n'a bougé :

```bash
kubectl version 2>/dev/null | grep Server; echo "(rien n'a bougé)"
```

```text
Server Version: v1.36.6
(rien n'a bougé)
```

Toujours en v1.36.6. Chaque dry-run laisse cependant un répertoire de travail
sous `/etc/kubernetes/tmp/`, que kubeadm ne retire pas.

## 🧹 Nettoyage

Le cours n'a créé aucun objet. Quittez la machine et remettez le lab à zéro.
`dsoxlab reset` rejoue le nettoyage puis la préparation du lab : vous
retrouvez exactement l'état de départ du challenge. Il vous demande de
confirmer : répondez `y`.

```bash
exit
dsoxlab reset cka-kubeadm-upgrade
dsoxlab check cka-kubeadm-upgrade
```

```text
╭─ Résultat : cka-kubeadm-upgrade ──╮
│  0 / 100 pts                      │
│  ░░░░░░░░░░░░░░░░░░░░  0/2 tests  │
╰───────────────────────────────────╯
```

0 sur 2 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : monter le cluster d'une version mineure, nœud par
nœud, sans interrompre l'application qui tourne dessus.

```bash
dsoxlab run cka-kubeadm-upgrade
dsoxlab challenge cka-kubeadm-upgrade
```
