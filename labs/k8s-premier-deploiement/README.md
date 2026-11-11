# Deploy, expose and scale a first application

Guided lab of the **Fondamentaux** module of the Kubernetes course: a dedicated
namespace, an nginx Deployment on the pinned image, a ClusterIP Service,
scaling, and the HTTP answer read from a client Pod.

| | |
|---|---|
| Target | `k8s-kind.lab`, kind cluster `boutique` (Kubernetes 1.37), namespace `demo-app` |
| Duration | about 20 minutes |
| Related page | [Déployer votre première application, section Mettre en pratique](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/fondamentaux/premier-deploiement/#mettre-en-pratique) |

```bash
dsoxlab run   k8s-premier-deploiement
dsoxlab check k8s-premier-deploiement
```
