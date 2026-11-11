# Figer une image par digest et tirer d'un registre privé

Lab guidé du module **Déployer ses applications** de la formation Kubernetes :
figer une image par digest, diagnostiquer un ImagePullBackOff, et tirer d'un
registre privé grâce à un Secret docker-registry porté par un ServiceAccount.

| | |
|---|---|
| Cible | `k8s-kind.lab`, cluster kind `lab` ; le lab pose un registre privé local au cluster et le namespace `galerie` |
| Durée | environ 30 minutes |
| Page associée | [Gérer les images conteneurs, section Mettre en pratique](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/images-kubernetes/#mettre-en-pratique) |

```bash
dsoxlab run   k8s-gerer-les-images
dsoxlab check k8s-gerer-les-images
```
