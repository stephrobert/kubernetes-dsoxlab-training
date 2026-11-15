# Épreuve du niveau 5 : sécuriser un cluster

Épreuve de fin de niveau de la formation Kubernetes : à partir d'un état hérité
faible et d'un cahier des charges qui ne nomme aucun objet Kubernetes,
sécuriser le cluster qui héberge la boutique. Plan de contrôle, journal
d'audit, admission, confinement, réseau, détection avec Falco et chaîne
d'approvisionnement, sans que la boutique cesse de répondre. Notée sur l'état
final : dix-neuf états à poids égal, seuil 70, sept états critiques, indices
payants.

| | |
|---|---|
| Cible | `k8s-cp.lab`, cluster kubeadm du catalogue ; le lab installe Falco 0.45.2, Istio 1.31, gVisor, trivy, cosign et crane, un registre local, et pose les espaces `boutique`, `facturation`, `commandes`, `partenaires`, `paiement`, `registre` et `conformite` |
| Durée | environ 150 minutes |
| Page associée | [Épreuve du niveau 5 : sécuriser un cluster](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/epreuves/securiser-un-cluster/) |

```bash
dsoxlab run    k8s-epreuve-securiser-un-cluster
dsoxlab check  k8s-epreuve-securiser-un-cluster
dsoxlab submit k8s-epreuve-securiser-un-cluster
```
