# Installer Cilium sans kube-proxy

## La situation

L'équipe réseau veut un cluster dont les Services ne sont plus servis par
kube-proxy et ses milliers de règles iptables, mais par Cilium et eBPF. Vous
disposez pour cela de trois machines : **`net-cp.lab`**, le plan de contrôle,
et deux workers, **`net-w1.lab`** et **`net-w2.lab`**.

Les trois nœuds sont prêts : swap coupé, containerd configuré, `kubelet`,
`kubeadm` et `kubectl` 1.37 installés et figés, `helm` 4.3.0 sur le plan de
contrôle. Aucun cluster n'existe encore. Depuis le plan de contrôle,
`ssh net-w1.lab` et `ssh net-w2.lab` ouvrent une session sur chaque worker
sans mot de passe, et `sudo` n'en demande pas non plus.

Le réseau des nœuds est `10.10.50.0/24`. Le pool de Pods par défaut de Cilium,
`10.0.0.0/8`, le contient : un Pod pourrait recevoir une adresse qui masque un
nœud. L'équipe a choisi le pool **`10.244.0.0/16`**, un bloc `/24` par nœud.

Note de version : Cilium 1.20.4 déclare prendre en charge Kubernetes 1.33 à
1.36, et ce cluster tourne en 1.37. Le lab tourne sur cette combinaison, qui
sort de ce que Cilium déclare officiellement : un comportement inattendu peut
venir de là.

## Ce que vous devez obtenir

1. Un cluster initialisé sur `net-cp.lab` **sans kube-proxy** : ni son
   DaemonSet, ni son ConfigMap dans `kube-system`.
2. Les deux workers **joints**, et les trois nœuds **Ready**.
3. **Cilium 1.20.4** installé par Helm sur chaque nœud, l'agent annonçant
   **`KubeProxyReplacement: True`**.
4. **Aucune règle de kube-proxy** sur aucun nœud : ni chaîne `KUBE-SVC`, ni
   chaîne `KUBE-SERVICES`.
5. Un Deployment **`web`** (image `nginx:1.30.6`, 2 réplicas) dans le
   namespace **`demo`**, exposé par un Service ClusterIP **`web`** sur le
   port 80, qui répond depuis un worker et figure dans la table des services
   de Cilium.
6. L'IPAM en mode **`cluster-pool`** sur le pool **`10.244.0.0/16`**, en `/24`
   par nœud.

## La méthode, pas à pas

**Initialiser sans kube-proxy.** kubeadm installe kube-proxy dans une phase
d'addon, qui se saute : `sudo kubeadm init --skip-phases=addon/kube-proxy`.
Donnez-vous ensuite un kubeconfig, comme le dit la sortie de la commande
(`$HOME/.kube/config`). `kubectl -n kube-system get ds` ne montre aucun
kube-proxy.

**Joindre les workers.** `sudo kubeadm token create --print-join-command`
donne la commande à lancer avec `sudo` sur chaque worker, par
`ssh net-w1.lab` puis `ssh net-w2.lab`. Les nœuds apparaissent `NotReady` :
il n'y a pas encore de CNI, c'est attendu.

**Installer Cilium en remplacement de kube-proxy.** Déclarez le dépôt de
charts (`helm repo add cilium https://helm.cilium.io`), puis installez le
chart `cilium/cilium` en **version 1.20.4** dans `kube-system`. Les valeurs qui
comptent :

- `kubeProxyReplacement=true` ;
- `k8sServiceHost` et `k8sServicePort` : l'adresse du plan de contrôle
  (`ip -4 route get 1.1.1.1` la donne après `src`) et `6443`. Sans
  kube-proxy, rien ne sert le Service `kubernetes` à un agent qui démarre : il
  doit joindre l'API server en direct ;
- `ipam.mode=cluster-pool`, `ipam.operator.clusterPoolIPv4PodCIDRList` à
  `{10.244.0.0/16}` et `ipam.operator.clusterPoolIPv4MaskSize=24`. Le pool se
  fixe à l'installation : le changer ensuite ne déplace pas les blocs déjà
  attribués.

`kubectl -n kube-system rollout status ds/cilium`, puis `kubectl get nodes` :
les trois nœuds passent `Ready`.

**Lire ce que dit Cilium.** `kubectl -n kube-system exec ds/cilium -c
cilium-agent -- cilium-dbg status` affiche une ligne `KubeProxyReplacement:`.
Sur chaque worker, `sudo iptables-save -t nat | grep KUBE-SVC` ne rend rien.

**Servir un Service.** Créez le namespace `demo`, le Deployment `web` et son
Service. Depuis un worker, `curl http://<ClusterIP>/` répond, et
`cilium-dbg service list` dans un agent montre la ClusterIP avec ses deux
backends. Le paquet n'est jamais passé par iptables.

**Lire l'IPAM.** `kubectl get ciliumnodes -o wide` montre le bloc de chaque
nœud, et `kubectl -n demo get pods -o wide` les adresses des Pods, dans
`10.244.0.0/16`.

## Comment vous saurez que ça marche

Les tests interrogent l'API server sur kube-proxy, les nœuds et les
CiliumNodes, lancent `cilium-dbg status` dans chaque agent, lisent la table
nat des trois nœuds, puis appellent le Service `web` depuis `net-w1.lab`.

```bash
dsoxlab check k8s-installer-cilium-sans-kube-proxy
```
