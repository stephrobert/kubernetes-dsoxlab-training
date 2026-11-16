# Surcharger les values d'un chart Helm sans tomber dans le piège du typage

Lab **CKAD**, domaine *Application Deployment*, compétence « Use the Helm
package manager to deploy existing packages ».

Une montée de version de chart perd en silence les réglages posés à la main, et
`--set` change le type d'une valeur qui ressemble à un nombre. Ce lab fait
monter une release en gardant les réglages de l'exploitation et en posant une
valeur qui doit rester une chaîne, avec Helm 4.3.2.

| | |
|---|---|
| Cible | `k8s-cp.lab`, control plane du cluster kubeadm |
| Durée | environ 20 minutes |
| Leçon jumelée | [Les values Helm](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/outils/helm/values/) |

```bash
dsoxlab run   k8s-surcharger-les-values-d-un-chart-helm
dsoxlab check k8s-surcharger-les-values-d-un-chart-helm
```
