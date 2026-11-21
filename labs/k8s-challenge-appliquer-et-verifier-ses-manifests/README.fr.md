# Appliquer et vérifier ses manifests, d'après un cahier des charges

Challenge du module **Écrire et appliquer ses manifests** de la formation
Kubernetes : une application à écrire d'après un cahier des charges qui ne
nomme pas les objets, livrée en deux variantes depuis une base Kustomize, avec
un champ d'API à trouver, un diff avant la montée de version et une livraison
qui attend la disponibilité. Six exigences, seuil 70, deux bloquantes.

| | |
|---|---|
| Cible | `k8s-kind.lab`, cluster kind `lab` ; le lab pose le cahier des charges dans `~/annuaire/` |
| Durée | environ 45 minutes |
| Page associée | [Kustomize](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/outils/kustomize/) |

```bash
dsoxlab run    k8s-challenge-appliquer-et-verifier-ses-manifests
dsoxlab check  k8s-challenge-appliquer-et-verifier-ses-manifests
dsoxlab submit k8s-challenge-appliquer-et-verifier-ses-manifests
```
