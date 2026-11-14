# Configure an application through ConfigMaps

Guided lab of the **Les ressources de base** module of the Kubernetes course:
inject values from a ConfigMap as variables and a file from another through a
volume, change both, and see what only a restart refreshes.

| | |
|---|---|
| Target | `k8s-kind.lab`, kind cluster `boutique` (Kubernetes 1.37), namespace `configuration` |
| Duration | about 20 minutes |
| Related page | [ConfigMaps, section Mettre en pratique](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/configmaps/) |

```bash
dsoxlab run   k8s-configurer-par-configmap
dsoxlab check k8s-configurer-par-configmap
```
