# Faire lire à un conteneur ce qu'un autre écrit, et pas le reste

Lab **CKAD**, domaine *Application Design and Build* (20 % de l'épreuve), les
volumes applicatifs.

Distinct de [`ckad-multi-container-sidecar`](../ckad-multi-container-sidecar/),
qui porte sur le **motif** à deux conteneurs. Celui-ci porte sur ce qui les
relie, et sur ce qu'un système de fichiers de conteneur ne partage justement
pas : deux conteneurs d'un même Pod partagent le réseau et l'adresse IP, jamais
leur système de fichiers.

**Le second contrôle du test final est celui qui compte.** Un candidat qui
monterait le volume sur la racine des deux conteneurs, ou sur `/tmp`, ferait
passer la première moitié sans avoir compris ce qu'un volume partage. Le test
écrit donc un fichier **hors** du volume et vérifie qu'il ne traverse pas.

L'état de départ est mesurable avant toute intervention : le producteur écrit
toutes les cinq secondes, et `ls` dans le lecteur ne trouve rien.

| | |
|---|---|
| Cible | `k8s-cp.lab`, control plane du cluster kubeadm vanilla |
| Durée | environ 20 minutes |
| Leçon jumelée | [Volumes applicatifs](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/volumes-applicatifs/) |

```bash
dsoxlab run   ckad-volumes-partage-entre-conteneurs
dsoxlab check ckad-volumes-partage-entre-conteneurs
```
