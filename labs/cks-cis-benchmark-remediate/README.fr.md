# Faire baisser le compte d'un audit CIS, et le prouver par un second audit

Lab **CKS**, domaine *Cluster Setup* (15 % de l'épreuve), compétence « Use CIS
benchmark to review the security configuration of Kubernetes components ».

Mesuré le 2026-09-16 sur le socle du catalogue : kube-bench échoue à **dix
contrôles** sur un cluster kubeadm sorti de l'installation, dont trois qui
partagent une même cause sur trois composants différents.

Le lab hérité demandait de consigner les constats dans un ConfigMap de texte
libre. Ici, le dernier test **relance l'outil** et compte : un rapport
s'édite, un audit qui tourne sous nos yeux ne s'édite pas. Il exige aussi que
le total d'échecs ait baissé, ce qu'un contrôle par contrôle ne verrait pas :
une correction qui en casse une autre laisse le compte inchangé.

**kube-bench n'est pas dans mise**, contrairement à trivy et cosign. Il n'en a
pas besoin : il tourne comme Job DANS le cluster, avec les répertoires du nœud
montés en lecture seule, ce qui est aussi la façon dont on l'emploie en
production.

| | |
|---|---|
| Cible | `k8s-cp.lab`, control plane du cluster kubeadm vanilla |
| Durée | environ 30 minutes |
| Leçon jumelée | [CIS Benchmark](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/cis-benchmark/) |

```bash
dsoxlab run   cks-cis-benchmark-remediate
dsoxlab check cks-cis-benchmark-remediate
```

Le setup sauvegarde les **trois** manifestes du control plane sous
`/var/backups`, et le cleanup les restaure : ce sont des fichiers du nœud, que
le validateur ne photographie pas, et les laisser modifiés ferait passer le
premier test du prochain passage avant tout travail.

Transposé de K8sExamLab le 2026-09-16, puis validé par
`scripts/valider-labs.py` : 0 avant le travail, 100 après la solution du
formateur, rejouable et sans trace.
