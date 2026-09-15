# Cloisonner trois tiers avec des NetworkPolicy ingress et egress

Lab **CKAD**, domaine *Services and Networking* (20 % de l'épreuve),
compétence « Demonstrate basic understanding of NetworkPolicies ».

Le lab hérité lisait huit specs sans jamais tenter une connexion. Ici chaque
règle se mesure par une vraie requête, celle qui passe et celle qui est
bloquée : c'est pour ce lab, entre autres, que le socle est passé à Calico.

| | |
|---|---|
| Cible | `k8s-cp.lab`, control plane du cluster kubeadm vanilla |
| Durée | environ 20 minutes |
| Leçon jumelée | [Network Policies](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/network-policies/) |

```bash
dsoxlab run   ckad-networkpolicy-ingress-egress
dsoxlab check ckad-networkpolicy-ingress-egress
```

Transposé de K8sExamLab le 2026-09-15, puis validé par
`scripts/valider-labs.py` : 0 avant le travail, 100 après la solution du
formateur, rejouable et sans trace.
