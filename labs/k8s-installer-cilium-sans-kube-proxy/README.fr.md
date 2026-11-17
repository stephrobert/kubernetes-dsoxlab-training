# Installer Cilium sans kube-proxy

Lab guidé de la leçon « Installer Cilium sans kube-proxy et choisir son
IPAM », module Réseau avancé de la formation Kubernetes (niveau 6, objectifs
CKNE du domaine Core Infrastructure and CNI). Initialiser un cluster kubeadm
sans kube-proxy, y joindre deux workers, installer Cilium 1.20.4 par Helm en
remplacement de kube-proxy sur le pool `10.244.0.0/16`, puis prouver qu'un
Service est servi par Cilium et non par des règles iptables.

| | |
|---|---|
| Cible | `net-cp.lab`, avec les workers `net-w1.lab` et `net-w2.lab` : le cluster Cilium du catalogue, distinct du cluster partagé `k8s-cp.lab` |
| Durée | environ 45 minutes |
| Versions | Kubernetes 1.37, Cilium 1.20.4 (qui déclare Kubernetes 1.33 à 1.36), Helm 4.3.2 |
| Page liée | [Cilium](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/cilium/) |

Les trois nœuds sont des hôtes optionnels du catalogue : `dsoxlab run` les
monte la première fois (8 Go de mémoire au total), et
`dsoxlab destroy --optional-hosts` les retire.

La méthode est dans `scenario.fr.md` : `kubeadm init
--skip-phases=addon/kube-proxy`, `kubeadm join` sur les deux workers,
`helm install` avec `kubeProxyReplacement`, `k8sServiceHost`,
`k8sServicePort` et l'IPAM cluster-pool, puis la lecture de
`cilium-dbg status`, des tables nat et d'un Service.

Le `cleanup.yaml` remet les trois nœuds à zéro par `kubeadm reset`, retire la
configuration CNI, l'état de l'agent Cilium et les chaînes KUBE et CILIUM : le
lab suivant remonte le cluster prêt.

```bash
dsoxlab run   k8s-installer-cilium-sans-kube-proxy
dsoxlab check k8s-installer-cilium-sans-kube-proxy
```
