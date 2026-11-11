# Atteindre une application : expose et port-forward

Lab guidé du module **Les ressources de base** de la formation Kubernetes :
exposer un Deployment par un Service sur le bon port et le bon targetPort, puis
l'atteindre depuis la machine par un tunnel `kubectl port-forward`.

| | |
|---|---|
| Cible | `k8s-kind.lab`, cluster kind `boutique` (Kubernetes 1.37), namespace `acces` |
| Durée | environ 15 minutes |
| Page associée | [Accéder à une application, section Mettre en pratique](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/outils/kubectl-expose-port-forward-proxy/#mettre-en-pratique) |

```bash
dsoxlab run   k8s-atteindre-une-application
dsoxlab check k8s-atteindre-une-application
```
