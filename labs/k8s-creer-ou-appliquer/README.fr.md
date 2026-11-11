# Créer ou appliquer : apply, server-side apply et prune

Lab guidé du module **Déployer ses applications** de la formation Kubernetes :
appliquer un dossier à sous-dossiers, ménager les réplicas d'un autoscaler,
reprendre un champ par server-side apply, et élaguer sans dégât.

| | |
|---|---|
| Cible | `k8s-kind.lab`, cluster kind `lab` ; le lab pose le namespace `livraisons` et le dossier `~/livraisons/appli/` |
| Durée | environ 30 minutes |
| Page associée | [kubectl create et apply, section Mettre en pratique](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/outils/kubectl-create-apply/#mettre-en-pratique) |

```bash
dsoxlab run   k8s-creer-ou-appliquer
dsoxlab check k8s-creer-ou-appliquer
```
