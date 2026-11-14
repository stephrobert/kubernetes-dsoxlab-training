# Initialiser un plan de contrôle avec kubeadm

## La situation

Le cluster a été démonté : **`k8s-cp.lab`** et **`k8s-w1.lab`** ont été remis à
zéro par `kubeadm reset`. Sur `k8s-cp.lab`, la préparation du nœud a aussi été
défaite. L'équipe veut un plan de contrôle neuf, monté proprement : à partir
d'un **fichier de configuration** qu'elle pourra relire et versionner, et sur
une machine qui reste prête **après un redémarrage**.

Vous êtes sur **`k8s-cp.lab`**, avec les droits `sudo`. Les manifestes de
Calico v3.32.2 vous attendent dans **`~/kubeadm/calico/`** : pas besoin
d'Internet pour poser le réseau. Le worker n'est pas à joindre dans ce lab.

## Ce que vous devez obtenir

1. Le cluster est initialisé à partir du fichier **`~/kubeadm/init.yaml`**. Il
   s'appelle **`catalogue`**, et son réseau de Pods est **`10.244.0.0/16`**.
2. Votre **kubeconfig** (`~/.kube/config`) joint ce nouveau cluster **sans
   `sudo`**.
3. **Calico** tourne sur `k8s-cp.lab`.
4. Le nœud est **Ready**, et **CoreDNS** tourne.
5. La préparation du nœud **survit à un redémarrage** : modules `overlay` et
   `br_netfilter`, `net.ipv4.ip_forward = 1`, swap coupé.
6. **kubeadm**, **kubelet** et **kubectl** sont **figés**.

## Les repères utiles

- `kubeadm init` vérifie la machine **avant** de toucher à quoi que ce soit (le
  *preflight*). Ses erreurs disent ce qui manque.
- Un réglage fait à chaud (`modprobe`, `sysctl -w`, `swapoff`) disparaît au
  redémarrage. Ce qui le rend durable vit dans `/etc/modules-load.d/`,
  `/etc/sysctl.d/` et `/etc/fstab`.
- Le fichier de configuration de kubeadm porte des documents
  `InitConfiguration` et `ClusterConfiguration` (API `kubeadm.k8s.io/v1beta4`).
  `kubeadm config print init-defaults` en montre un exemple complet.
- `kubeadm version -o short` donne la version installée. Sans version écrite
  dans le fichier, kubeadm la demande à Internet.
- Le cidr de `~/kubeadm/calico/installation.yaml` doit être celui du réseau de
  Pods du cluster.
- La configuration que kubeadm a réellement servie se relit dans le ConfigMap
  `kubeadm-config` du namespace `kube-system`.
