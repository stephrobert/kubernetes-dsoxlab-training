# Reach an application: expose and port-forward

Guided lab of the **Les ressources de base** module of the Kubernetes course:
expose a Deployment through a Service on the right port and targetPort, then
reach it from the machine through a `kubectl port-forward` tunnel.

| | |
|---|---|
| Target | `k8s-kind.lab`, kind cluster `boutique` (Kubernetes 1.37), namespace `acces` |
| Duration | about 15 minutes |
| Related page | [Accéder à une application, section Mettre en pratique](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/outils/kubectl-expose-port-forward-proxy/#mettre-en-pratique) |

```bash
dsoxlab run   k8s-atteindre-une-application
dsoxlab check k8s-atteindre-une-application
```
