# Ramener au dépôt Git les modifications faites en direct

Challenge de la formation Kubernetes, dans la section Mettre en pratique de la
leçon « kubectl edit, patch et replace » : retrouver les modifications faites
en direct sur un cluster, reporter dans Git celle que l'équipe garde, défaire
les autres, sans recréer aucun objet. Cinq exigences, seuil 80 %, trois
bloquantes.

| | |
|---|---|
| Cible | `k8s-cp.lab`, control plane du cluster kubeadm ; le lab pose le namespace `annuaire` et le dépôt `~/annuaire` |
| Durée | environ 35 minutes |
| Pages associées | [kubectl edit, patch et replace](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/outils/kubectl-edit-patch-replace/#mettre-en-pratique), [kubectl create et apply](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/outils/kubectl-create-apply/) |

```bash
dsoxlab run    k8s-challenge-ramener-le-cluster-au-depot
dsoxlab check  k8s-challenge-ramener-le-cluster-au-depot
dsoxlab submit k8s-challenge-ramener-le-cluster-au-depot
```
