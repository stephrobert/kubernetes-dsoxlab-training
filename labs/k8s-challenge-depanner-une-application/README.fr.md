# Remettre en service une application en panne et son cluster

Challenge du module **Diagnostiquer** de la formation Kubernetes (niveau 4),
dans la section Mettre en pratique de la leçon « Dépanner un nœud » : quatre
pannes à la fois sur le cluster kubeadm du catalogue, deux côté application (un
Deployment en `CrashLoopBackOff`, un Pod en `ImagePullBackOff`) et deux côté
cluster (un API server qui ne démarre plus, un worker dont le kubelet est
tombé). La cause de chaque panne se consigne avant sa réparation. Dix états,
seuil 70, deux bloquants.

| | |
|---|---|
| Cibles | `k8s-cp.lab`, le cluster kubeadm du catalogue, et `k8s-w1.lab` joignable en `ssh` depuis le control plane ; le lab pose le namespace `commerce` |
| Durée | environ 60 minutes |
| Page associée | [Dépanner un nœud : kubelet et NotReady](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/operer/depanner-un-noeud-kubernetes/) |

```bash
dsoxlab run    k8s-challenge-depanner-une-application
dsoxlab check  k8s-challenge-depanner-une-application
dsoxlab submit k8s-challenge-depanner-une-application
```

Le setup laisse `kubectl` sans réponse, et c'est voulu : l'API server est la
dernière panne qu'il pose. `dsoxlab clean` rend le cluster en état de marche,
API server et worker compris.
