# Modifier un Deployment en production sans perdre un conteneur, et résorber la dérive

Lab **CKA**, domaine *Workloads and Scheduling*, compétence « Understand
application deployments and how to perform rolling updates and rollbacks ».

`edit`, `patch` et `replace` écrivent directement dans le cluster. Chacun a son
piège : le JSON merge efface un conteneur, `replace --force` arrête tout, et
toute correction faite hors de Git sera défaite au prochain `apply`. Ce lab les
met en jeu sur un Deployment à deux conteneurs, déjà en dérive.

| | |
|---|---|
| Cible | `k8s-cp.lab`, control plane du cluster kubeadm |
| Durée | environ 25 minutes |
| Leçon jumelée | [Modifier une ressource en production : edit, patch, replace](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/outils/kubectl-edit-patch-replace/) |

```bash
dsoxlab run   k8s-modifier-une-ressource-en-production
dsoxlab check k8s-modifier-une-ressource-en-production
```
