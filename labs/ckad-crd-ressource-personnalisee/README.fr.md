# Utiliser une ressource personnalisée, lire les refus de son schéma, la débloquer

Lab guidé de la leçon « Operators et CRDs pour développeurs » du module
**Workloads avancés** de la formation Kubernetes : découvrir le groupe d'API
d'une CRD, créer et modifier des ressources personnalisées, lire le refus de
l'API pour une valeur hors bornes, et débloquer une ressource restée en
Terminating.

| | |
|---|---|
| Cible | `k8s-kind.lab`, cluster kind `lab` ; le lab pose la CRD `Sauvegarde` et le namespace `sauvegardes` |
| Durée | environ 25 minutes |
| Page associée | [Operators et CRDs pour développeurs, section Mettre en pratique](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/operators-crds-developpeurs/#mettre-en-pratique) |

```bash
dsoxlab run   ckad-crd-ressource-personnalisee
dsoxlab check ckad-crd-ressource-personnalisee
```
