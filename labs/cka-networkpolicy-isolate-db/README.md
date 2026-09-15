# Isoler la base de données : seul le backend y accède

Lab **CKA**, domaine *Services and Networking* (20 % de l'épreuve),
compétence « Define and enforce Network Policies ».

Le lab hérité lisait le spec de la politique et tentait une connexion dans
chaque sens. Ici un Pod `intrus`, au bon label mais dans un autre namespace,
doit rester dehors : un `namespaceSelector` vide, l'erreur classique, le
laisserait entrer. Et la base doit pouvoir encore sortir, ce qu'une
politique trop large casserait. Calico applique les politiques ; sans lui,
rien de cela ne se mesurerait.

| | |
|---|---|
| Cible | `k8s-cp.lab`, control plane du cluster kubeadm vanilla |
| Durée | environ 15 minutes |
| Leçon jumelée | [Les NetworkPolicies Kubernetes](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/network-policies/) |

```bash
dsoxlab run   cka-networkpolicy-isolate-db
dsoxlab check cka-networkpolicy-isolate-db
```

Transposé de K8sExamLab le 2026-09-15, puis validé par
`scripts/valider-labs.py` : 0 avant le travail, 100 après la solution du
formateur, rejouable et sans trace.
