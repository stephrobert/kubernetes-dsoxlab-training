# Explorer l'API avec api-resources et explain

Lab guidé du module **Déployer ses applications** de la formation Kubernetes :
trouver l'apiVersion et le kind d'une CRD inconnue, écrire un objet avec les
champs que seul `explain` révèle, ajouter une sonde trouvée champ par champ, et
dresser l'inventaire complet d'un namespace.

| | |
|---|---|
| Cible | `k8s-kind.lab`, cluster kind `lab` ; le lab installe une CRD et le namespace `archives` |
| Durée | environ 25 minutes |
| Page associée | [kubectl api-resources et explain, section Mettre en pratique](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/outils/kubectl-api-resources-explain/#mettre-en-pratique) |

```bash
dsoxlab run   k8s-explorer-l-api
dsoxlab check k8s-explorer-l-api
```
