# Faire monter en charge automatiquement avec un HorizontalPodAutoscaler

Lab **CKA**, domaine *Workloads and Scheduling* (15 % de l'épreuve),
compétence « Configure workload autoscaling ».

Le lab hérité lisait le spec du HPA et un ConfigMap qui recopiait ses
valeurs ; aucune charge n'était générée, aucune montée observée. Ici les
tests lisent les métriques courantes du HPA et l'event `SuccessfulRescale`
que le contrôleur émet quand il fait grossir le Deployment : un HPA qui n'a
jamais redimensionné n'est pas un HPA validé, comme le dit la leçon.

metrics-server 0.9.0, la version courante, est installé par le setup avec
l'option que kubeadm impose, et retiré par le nettoyage.

| | |
|---|---|
| Cible | `k8s-cp.lab`, control plane du cluster kubeadm vanilla |
| Durée | environ 20 minutes |
| Leçon jumelée | [Horizontal Pod Autoscaler](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/horizontal-pod-scaling/) |

```bash
dsoxlab run   cka-hpa-autoscaling
dsoxlab check cka-hpa-autoscaling
```

Transposé de K8sExamLab le 2026-09-15, puis validé par
`scripts/valider-labs.py` : 0 avant le travail, 100 après la solution du
formateur, rejouable et sans trace.
