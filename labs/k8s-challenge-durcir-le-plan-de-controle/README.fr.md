# Corriger les écarts CIS d'un cluster, sans guidage

Challenge du module **Durcir le cluster** de la formation Kubernetes, dans la
section Mettre en pratique de la leçon « Audit Logs » : un API server à durcir
sans le casser, un écart CIS à corriger sur trois composants du plan de
contrôle et à prouver par un second audit kube-bench, et une politique d'audit
à deux niveaux dont la trace doit apparaître dans le journal. Sept états,
seuil 70, deux bloquants.

| | |
|---|---|
| Cible | `k8s-cp.lab`, cluster kubeadm du catalogue ; le lab pose le namespace `conformite` et restaure les trois manifestes du plan de contrôle à chaque passage |
| Durée | environ 50 minutes |
| Page associée | [Audit Logs](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/audit-logs/) |

```bash
dsoxlab run    k8s-challenge-durcir-le-plan-de-controle
dsoxlab check  k8s-challenge-durcir-le-plan-de-controle
dsoxlab submit k8s-challenge-durcir-le-plan-de-controle
```
