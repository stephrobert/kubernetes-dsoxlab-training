# Isolate an application in a namespace

Guided lab of the **Les ressources de base** module of the Kubernetes course:
put an application in its own namespace, reach it from another namespace by its
qualified name, and see that the short name is not enough there.

| | |
|---|---|
| Target | `k8s-kind.lab`, kind cluster `boutique` (Kubernetes 1.37), namespaces `equipe-api` and `equipe-front` |
| Duration | about 15 minutes |
| Related page | [Namespaces, section Mettre en pratique](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/namespaces/#mettre-en-pratique) |

```bash
dsoxlab run   k8s-isoler-par-namespace
dsoxlab check k8s-isoler-par-namespace
```
