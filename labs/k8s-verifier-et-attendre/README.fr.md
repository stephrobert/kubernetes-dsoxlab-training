# Prévisualiser avec diff, attendre avec wait

Lab guidé du module **Déployer ses applications** de la formation Kubernetes :
prévisualiser avec `kubectl diff`, attendre avec `kubectl wait` et
`kubectl rollout status`, et écrire un script de déploiement qui s'arrête au bon
moment.

| | |
|---|---|
| Cible | `k8s-kind.lab`, cluster kind `lab` ; le lab pose le namespace `paiements` et le dossier `~/deploiement/` |
| Durée | environ 25 minutes |
| Page associée | [kubectl diff et wait, section Mettre en pratique](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/outils/kubectl-wait-diff/#mettre-en-pratique) |

```bash
dsoxlab run   k8s-verifier-et-attendre
dsoxlab check k8s-verifier-et-attendre
```
