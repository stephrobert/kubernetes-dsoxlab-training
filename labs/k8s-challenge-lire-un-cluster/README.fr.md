# Lire un cluster : quel composant fait quoi

Challenge du module **Architecture** de la formation Kubernetes, sans guidage,
noté sur l'état réel du cluster (seuil 70). Il mobilise les gestes du domaine
KCNA *Kubernetes Fundamentals* : lire les Nodes, les composants du control
plane, le runtime de conteneurs et les événements.

| | |
|---|---|
| Cible | `k8s-kind.lab`, cluster kind `architecture`, un control plane et trois workers (Kubernetes 1.37) |
| Durée | environ 30 minutes |
| Page associée | [Nœuds worker, section Mettre en pratique](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/worker-nodes/#mettre-en-pratique) |

```bash
dsoxlab run   k8s-challenge-lire-un-cluster
dsoxlab check k8s-challenge-lire-un-cluster
```

Il tourne sur un cluster kind, l'outil qu'enseigne la formation, dans la
topologie multi-nœuds qu'elle prend pour référence.
