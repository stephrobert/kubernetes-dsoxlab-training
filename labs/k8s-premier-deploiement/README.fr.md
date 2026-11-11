# Déployer, exposer et mettre à l'échelle une première application

Lab guidé du module **Fondamentaux** de la formation Kubernetes : un namespace
dédié, un Deployment nginx sur l'image épinglée, un Service ClusterIP, la mise à
l'échelle, et la réponse HTTP lue depuis un Pod client.

| | |
|---|---|
| Cible | `k8s-kind.lab`, cluster kind `boutique` (Kubernetes 1.37), namespace `demo-app` |
| Durée | environ 20 minutes |
| Page associée | [Déployer votre première application, section Mettre en pratique](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/fondamentaux/premier-deploiement/#mettre-en-pratique) |

```bash
dsoxlab run   k8s-premier-deploiement
dsoxlab check k8s-premier-deploiement
```
