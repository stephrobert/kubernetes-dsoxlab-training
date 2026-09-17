# Obtenir un volume sans qu'un administrateur l'ait créé, et voir ce qu'il devient

Lab **CKA**, domaine *Storage* (10 % de l'épreuve), provisionnement dynamique.

Pendant de [`cka-pv-pvc-storageclass`](../cka-pv-pvc-storageclass/), qui porte
sur le provisionnement **statique**, où un administrateur crée le
PersistentVolume à la main. Celui-ci porte sur le cas dynamique, et sur ce qu'il
change à la suppression.

**Le contrôle décisif n'est pas que la revendication soit liée**, mais que le
volume appartienne à la classe et en porte la politique. Créer un volume à la
main lierait aussi la revendication, sans qu'aucun provisionnement dynamique
n'ait eu lieu : le test ne s'y laisse pas prendre.

L'état de départ repose sur une distinction que la documentation mentionne à
peine : `storageClassName: ""`, une chaîne **vide**, **désactive explicitement**
le provisionnement dynamique, là où un champ **absent** laisse jouer la classe
par défaut. La revendication attend donc un volume que personne ne créera.

Mesuré le 2026-09-17 avec `local-path-provisioner` v0.0.33 de Rancher :

| | |
|---|---|
| classe créée | `local-path` |
| mode de liaison | `WaitForFirstConsumer`, donc rien ne se lie avant qu'un Pod n'utilise la revendication |
| politique | `Delete`, le volume suit la revendication |

Le `cleanup.yaml` retire le provisionneur, sa StorageClass et son namespace, et
efface `/opt/local-path-provisioner` sur le nœud : ce sont des objets de cluster
et des fichiers qui rempliraient le disque au fil des labs.

| | |
|---|---|
| Cible | `k8s-cp.lab`, control plane du cluster kubeadm vanilla |
| Durée | environ 25 minutes |
| Leçon jumelée | [StorageClass](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/storageclass/) |

```bash
dsoxlab run   cka-storageclass-provisionnement-dynamique
dsoxlab check cka-storageclass-provisionnement-dynamique
```
