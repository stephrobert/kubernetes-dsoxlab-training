# Épreuve du niveau 2 : déployer une application qui garde ses données

Épreuve de fin du niveau 2 de la formation Kubernetes : à partir d'un cahier des
charges qui ne nomme aucun objet, déployer la boutique avec ses données. Une
vitrine fiable livrée par Kustomize, une base à identité stable, une sauvegarde
planifiée, un agent par nœud et une ressource personnalisée. Dix critères, seuil
70, cinq critiques.

| | |
|---|---|
| Cible | `k8s-kind.lab`, cluster kind `multi` (un control plane, deux workers) ; le lab pose le namespace `magasin` et la CRD `Sauvegarde` |
| Durée | environ 90 minutes |
| Page associée | [Épreuve du niveau 2](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/epreuves/deployer-une-application/) |

```bash
dsoxlab run    k8s-epreuve-deployer-une-application
dsoxlab check  k8s-epreuve-deployer-une-application
dsoxlab submit k8s-epreuve-deployer-une-application
```
