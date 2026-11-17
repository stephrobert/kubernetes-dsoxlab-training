# Auditer les flux réseau avec Hubble

Lab guidé de la leçon « Observer, mesurer et auditer les flux avec Hubble »,
module Réseau avancé de la formation Kubernetes (niveau 6, objectifs CKNE du
domaine Observability). Une NetworkPolicy refuse l'un des trois clients d'une
API : retrouvez le flux avec Hubble et consignez-le, donnez à la métrique des
refus le contexte qui lui fait nommer le Pod, et journalisez les seuls flux
refusés dans un fichier du nœud, sans lever le refus.

| | |
|---|---|
| Cible | `net-cp.lab`, avec les workers `net-w1.lab` et `net-w2.lab` : le cluster Cilium du catalogue ; le lab pose le namespace `magasin` |
| Durée | environ 40 minutes |
| Versions | Kubernetes 1.37, Cilium 1.20.4 (qui déclare Kubernetes 1.33 à 1.36), Helm 4.3.2 |
| Page liée | [Hubble](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/hubble/) |

Les trois nœuds sont des hôtes optionnels du catalogue : `dsoxlab run` les
monte la première fois (8 Go de mémoire au total), et monte le cluster Cilium
sans kube-proxy s'il n'est pas là.

La méthode est dans `scenario.fr.md` : `hubble observe --verdict DROPPED` dans
l'agent du nœud de destination, la métrique `hubble_drop_total` sur le port
9965, puis un `helm upgrade` qui donne à la métrique drop un contexte par Pod
et active l'export statique des flux refusés.

Le `cleanup.yaml` ramène Cilium aux valeurs du socle du catalogue (les agents
redémarrent), retire les fichiers d'export des trois nœuds, puis le namespace
`magasin`. Le cluster reste.

```bash
dsoxlab run   k8s-auditer-les-flux-avec-hubble
dsoxlab check k8s-auditer-les-flux-avec-hubble
```
