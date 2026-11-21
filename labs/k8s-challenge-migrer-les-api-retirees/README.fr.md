# Détecter et migrer les API retirées avant une montée de version

Challenge de la formation Kubernetes, dans la section Mettre en pratique de la
leçon « Gérer les API dépréciées » : trouver les manifestes d'un dépôt qui
emploient une API retirée, les nommer avec leur remplaçante dans un rapport,
les migrer sans changer leur intention, et appliquer le dépôt. Cinq
exigences, seuil 80 %, deux bloquantes.

| | |
|---|---|
| Cible | `k8s-cp.lab`, control plane du cluster kubeadm ; le lab pose le namespace `plateforme` et le dépôt `~/plateforme` |
| Durée | environ 40 minutes |
| Page associée | [Gérer les API dépréciées, section Mettre en pratique](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/api-deprecations/#mettre-en-pratique) |

```bash
dsoxlab run    k8s-challenge-migrer-les-api-retirees
dsoxlab check  k8s-challenge-migrer-les-api-retirees
dsoxlab submit k8s-challenge-migrer-les-api-retirees
```
