# Isoler une application dans un namespace

Lab guidé du module **Les ressources de base** de la formation Kubernetes :
ranger une application dans son namespace, la joindre depuis un autre namespace
par son nom qualifié, et constater que le nom court n'y suffit pas.

| | |
|---|---|
| Cible | `k8s-kind.lab`, cluster kind `boutique` (Kubernetes 1.37), namespaces `equipe-api` et `equipe-front` |
| Durée | environ 15 minutes |
| Page associée | [Namespaces, section Mettre en pratique](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/namespaces/#mettre-en-pratique) |

```bash
dsoxlab run   k8s-isoler-par-namespace
dsoxlab check k8s-isoler-par-namespace
```
