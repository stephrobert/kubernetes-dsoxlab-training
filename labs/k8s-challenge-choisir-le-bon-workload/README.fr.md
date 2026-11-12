# Choisir et déployer le bon workload pour trois besoins

Challenge du module **Workloads avancés** de la formation Kubernetes, dans la
section Mettre en pratique de la leçon « Operators et CRDs pour développeurs » :
trois besoins décrits sans nommer d'objet, une base à identité stable, un agent
par nœud et une ressource personnalisée bornée. Sept exigences, seuil 70, trois
bloquantes.

| | |
|---|---|
| Cible | `k8s-kind.lab`, cluster kind `multi` (un control plane, deux workers) ; le lab pose le namespace `entrepot` et la CRD à installer |
| Durée | environ 50 minutes |
| Page associée | [Operators et CRDs pour développeurs, section Mettre en pratique](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/operators-crds-developpeurs/#mettre-en-pratique) |

```bash
dsoxlab run    k8s-challenge-choisir-le-bon-workload
dsoxlab check  k8s-challenge-choisir-le-bon-workload
dsoxlab submit k8s-challenge-choisir-le-bon-workload
```
