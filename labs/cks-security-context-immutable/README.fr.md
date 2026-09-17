# Rendre un conteneur immuable sans le faire tomber

Lab **CKS**, domaine *Minimize Microservice Vulnerabilities* (20 % de
l'épreuve), le conteneur immuable.

Distinct de [`cks-secure-existing-pod`](../cks-secure-existing-pod/), qui
porte sur le privilège, le partage de namespaces avec l'hôte et l'identité du
processus. Celui-ci porte sur le **système de fichiers**, et sur le coût réel
de cette contrainte : une application qui écrit pendant son démarrage ne
redémarre pas.

**Le choix du chemin de preuve a été mesuré, pas supposé**, et c'est le point
délicat du lab. L'image tourne déjà sous l'UID 101 : la racine lui est refusée
par les droits POSIX avant tout durcissement. Un test qui ferait
`touch /preuve` serait donc **vert avant le travail**.

Mesuré le 2026-09-16, sur un Pod nu puis sur un Pod durci :

| chemin | Pod nu | Pod durci |
|---|---|---|
| `/preuve` | Permission denied | Read-only file system |
| `/usr/share/nginx/html` | Permission denied | Read-only file system |
| `/var/log/nginx` | Permission denied | Read-only file system |
| **`/etc/nginx/conf.d`** | **INSCRIPTIBLE** | Read-only file system |

Seul le dernier distingue les deux états : l'image l'ouvre à son propre UID
pour que ses scripts d'entrée y écrivent, et seul `readOnlyRootFilesystem` le
ferme.

L'autre mesure qui fait le lab : sans volumes éphémères, nginx s'arrête sur
`mkdir() "/tmp/proxy_temp" failed (30: Read-only file system)`. Le candidat
doit lire ce journal plutôt que deviner, ce que le scénario lui dit sans lui
donner les chemins.

| | |
|---|---|
| Cible | `k8s-cp.lab`, control plane du cluster kubeadm vanilla |
| Durée | environ 20 minutes |
| Leçon jumelée | [Security Context](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/security-context/) |

```bash
dsoxlab run   cks-security-context-immutable
dsoxlab check cks-security-context-immutable
```
