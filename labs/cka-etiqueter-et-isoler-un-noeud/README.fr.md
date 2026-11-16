# Étiqueter un nœud, afficher son rôle et le réserver à une équipe

Lab **CKA**, domaine *Troubleshooting* (30 % de l'épreuve), compétence
« Troubleshoot clusters and nodes », et domaine *Workloads and Scheduling*,
compétence « Configure Pod admission and scheduling ».

Étiquette, rôle, annotation, taint : quatre gestes sur un nœud, et une seule
décision qui compte, l'effet de la taint. Se tromper d'effet sur un nœud de
production laisse en place ce qu'on voulait faire partir, ou l'inverse.

| | |
|---|---|
| Cible | `k8s-cp.lab`, control plane du cluster kubeadm, avec ses deux workers |
| Durée | environ 20 minutes |
| Leçon jumelée | [Gérer les nœuds](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/operer/gerer-noeuds-kubernetes/) |

```bash
dsoxlab run   cka-etiqueter-et-isoler-un-noeud
dsoxlab check cka-etiqueter-et-isoler-un-noeud
```
