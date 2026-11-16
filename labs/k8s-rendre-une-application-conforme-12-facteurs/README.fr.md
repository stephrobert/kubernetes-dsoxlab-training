# Rendre une application conforme au 12-factor sur Kubernetes

Lab **CKAD**, domaine *Application Design and Build*.

Une application déployée sur Kubernetes n'est pas conforme au 12-factor pour
autant : le cluster applique ce qu'on déclare, il ne vérifie aucun facteur. Ce
lab fait reprendre une application fautive, facteur par facteur :
configuration, état, arrêt propre et tâche d'administration.

| | |
|---|---|
| Cible | `k8s-cp.lab`, control plane du cluster kubeadm |
| Durée | environ 30 minutes |
| Leçon jumelée | [Rendre une application conforme au 12-factor sur Kubernetes](https://www.stephane-robert.info/docs/conteneurs/cloud-native/application-12-factor-kubernetes/) |

```bash
dsoxlab run   k8s-rendre-une-application-conforme-12-facteurs
dsoxlab check k8s-rendre-une-application-conforme-12-facteurs
```
