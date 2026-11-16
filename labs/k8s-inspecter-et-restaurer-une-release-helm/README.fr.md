# Inspecter une release Helm en échec et la restaurer

Lab **CKAD**, domaine *Application Deployment*, compétence « Use the Helm
package manager to deploy existing packages ».

Une montée de version qui échoue laisse une release dans un état qu'il faut
d'abord lire, puis réparer. Ce lab fait chercher un chart, lire l'historique
d'une release, revenir à la dernière révision saine et lancer les tests du
chart, avec Helm 4.3.2.

| | |
|---|---|
| Cible | `k8s-cp.lab`, control plane du cluster kubeadm |
| Durée | environ 20 minutes |
| Leçon jumelée | [La commande helm](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/outils/helm/commande-helm/) |

```bash
dsoxlab run   k8s-inspecter-et-restaurer-une-release-helm
dsoxlab check k8s-inspecter-et-restaurer-une-release-helm
```
