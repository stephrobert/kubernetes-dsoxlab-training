# Fermer le profileur de l'API server, sans fermer l'API

Lab **CKS**, domaine *Cluster Hardening* (15 % de l'épreuve), compétence
« Restrict access to Kubernetes API ».

Mesuré le 2026-09-16 sur le socle du catalogue : un cluster kubeadm sorti de
l'installation répond bien une page HTML sur `/debug/pprof/`, et ne porte
aucun des trois flags de durcissement demandés. Le lab part donc d'un état
réel, pas d'une supposition.

Le dernier test exerce **les deux moitiés** de l'exigence : le profileur doit
répondre une erreur, et `/version` doit répondre normalement. Un API server à
l'arrêt ferme le profileur aussi sûrement qu'un flag bien posé, et c'est le
contresens le plus fréquent du durcissement.

Un test refuse explicitement `--anonymous-auth=false`, qui n'était pas
demandé : les sondes que kubeadm écrit dans ce même manifeste interrogent
`/livez` et `/readyz` **sans s'authentifier**. Le flag les fait échouer, le
kubelet tue l'API server en boucle, et le durcissement casse le cluster qu'il
devait protéger.

| | |
|---|---|
| Cible | `k8s-cp.lab`, control plane du cluster kubeadm vanilla |
| Durée | environ 25 minutes |
| Leçon jumelée | [CIS Benchmark](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/cis-benchmark/) |

```bash
dsoxlab run   cks-api-server-hardening
dsoxlab check cks-api-server-hardening
```

Le setup sauvegarde le manifeste d'origine dans `/var/backups`, **jamais**
dans `/etc/kubernetes/manifests` : le kubelet y lancerait la copie comme un
second Pod statique, et deux API servers se disputeraient le même port.

Transposé de K8sExamLab le 2026-09-16, puis validé par
`scripts/valider-labs.py` : 0 avant le travail, 100 après la solution du
formateur, rejouable et sans trace.
