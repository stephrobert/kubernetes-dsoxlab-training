# Épingler une image par son digest, et prouver que le tag ne suffit pas

Lab **CKS**, domaine *Supply Chain Security* (20 % de l'épreuve). Ce domaine
pèse un cinquième de l'examen et n'avait aucun lab dans le catalogue.

Le lab hérité de K8sExamLab s'arrêtait à chercher `@sha256:` dans le champ
`image`. C'est un contrôle de **forme** : une chaîne de la bonne tête, copiée
d'une autre image, passait. Ici le dernier test compare le digest déclaré à
`status.containerStatuses[].imageID`, ce que le kubelet écrit après que le
runtime a résolu l'image. C'est ce qui tourne, pas ce qu'on a demandé.

Le lab hérité supposait aussi `docker inspect`. Ce cluster tourne sous
containerd et n'a pas docker : les indices renvoient vers `crictl`.

| | |
|---|---|
| Cible | `k8s-cp.lab`, control plane du cluster kubeadm vanilla |
| Durée | environ 15 minutes |
| Leçon jumelée | [Supply Chain Security](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/supply-chain-security/) |

```bash
dsoxlab run   cks-image-pinned-digest
dsoxlab check cks-image-pinned-digest
```

Transposé de K8sExamLab le 2026-09-15, puis validé par
`scripts/valider-labs.py` : 0 avant le travail, 100 après la solution du
formateur, rejouable et sans trace.
