# Imposer une règle d'admission et prouver le refus, sans guidage

Challenge du module **Politiques d'admission** de la formation Kubernetes, dans
la section Mettre en pratique de la leçon « VAP vs Kyverno vs Gatekeeper » : le
standard restricted sur un namespace, un Pod privilégié à reconstruire sans
aucun de ses défauts sur un autre, et une politique d'admission native qui
refuse les images désignées par un tag sur un troisième, sans toucher au
reste. Dix états, seuil 70, deux bloquants.

| | |
|---|---|
| Cible | `k8s-cp.lab`, cluster kubeadm du catalogue ; le lab pose les namespaces `vitrine`, `paiement`, `production` et `recette` |
| Durée | environ 45 minutes |
| Page associée | [VAP vs Kyverno vs Gatekeeper](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/vap-vs-kyverno-gatekeeper/) |

```bash
dsoxlab run    k8s-challenge-faire-refuser-par-admission
dsoxlab check  k8s-challenge-faire-refuser-par-admission
dsoxlab submit k8s-challenge-faire-refuser-par-admission
```
