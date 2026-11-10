# Livrer la vitrine et remettre le stock en marche

Challenge du module **Fondamentaux** de la formation Kubernetes, sans guidage,
noté sur l'état final (seuil 70, deux exigences bloquantes). Il mobilise les
gestes du domaine KCNA *Kubernetes Fundamentals* (Kubernetes Core Concepts) et
le réglage du client `kubectl`.

| | |
|---|---|
| Cible | `k8s-kind.lab`, cluster kind `boutique` (Kubernetes 1.37) |
| Durée | environ 30 minutes |
| Page jumelée | [Contrôle des connaissances du module](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/fondamentaux/controle-connaissances/) |

```bash
dsoxlab run   k8s-challenge-premier-deploiement
dsoxlab check k8s-challenge-premier-deploiement
```

Il tourne sur un cluster kind, l'outil que la formation enseigne, et non sur le
cluster kubeadm du catalogue.
