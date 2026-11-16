# Faire lever par Falco une alerte sur un shell ouvert dans un namespace protégé

Lab **CKS**, domaine *Monitoring, Logging and Runtime Security* (20 % de
l'épreuve), compétence « Perform behavioral analytics to detect malicious
activities ».

Les règles fournies par Falco couvrent des comportements génériques, pas votre
contexte. Ce lab demande une règle à vous, sous un nom et une priorité fixés,
limitée à un namespace, chargée en plus des règles livrées sans les modifier.

| | |
|---|---|
| Cible | `k8s-cp.lab`, control plane du cluster kubeadm, où Falco tourne |
| Durée | environ 25 minutes |
| Leçon jumelée | [Falco](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/falco/) |

```bash
dsoxlab run   cks-falco-detecter-un-shell
dsoxlab check cks-falco-detecter-un-shell
```
