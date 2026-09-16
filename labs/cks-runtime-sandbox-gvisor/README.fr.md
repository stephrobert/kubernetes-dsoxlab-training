# Isoler un Pod du noyau de l'hôte, et le prouver en lisant sa version

Lab **CKS**, domaine *Minimize Microservice Vulnerabilities* (20 % de
l'épreuve), isolation par bac à sable.

**Ce lab lève une attestation négative de la formation.** Le champ
`non_couvert` du guide `runtime-sandboxes` disait « containerd ne déclare que
runc » : la compétence n'était éprouvable nulle part. Le setup installe gVisor
et le déclare auprès de containerd, ce qui la rend mesurable pour la première
fois.

La preuve ne se truque pas et ne tient à aucune chaîne choisie par nous : le
test compare le noyau vu par le Pod confiné, celui vu par un Pod témoin lancé
avec le runtime par défaut, et celui de la machine. Mesuré le 2026-09-16 : le
Pod confiné lit `Linux version 4.19.0-gvisor`, le nœud tourne sous
`6.8.0-139-generic`.

**Trois pièges de distribution**, tous mesurés le même jour :

- gVisor **ne publie plus ses binaires séparément**. L'URL
  `.../latest/x86_64/containerd-shim-runsc-v1` rend 404, et seule l'archive
  `gvisor.tar.bz2` porte encore le shim ;
- **bzip2 n'est pas installé** sur une Ubuntu 24.04 minimale : `tar` échoue
  sur « bzip2: Cannot exec » ;
- le paquet APT `runsc` d'Ubuntu date de 2023 et **ne fournit pas le shim**.

| | |
|---|---|
| Cible | `k8s-cp.lab`, control plane du cluster kubeadm vanilla |
| Durée | environ 25 minutes |
| Leçon jumelée | [Runtime Sandboxes](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/runtime-sandboxes/) |

```bash
dsoxlab run   cks-runtime-sandbox-gvisor
dsoxlab check cks-runtime-sandbox-gvisor
```

Le `cleanup.yaml` retire la RuntimeClass, qui est un objet de cluster et
survivrait au namespace.

Transposé de K8sExamLab le 2026-09-16, puis validé par
`scripts/valider-labs.py` : 0 avant le travail, 100 après la solution du
formateur, rejouable et sans trace.
