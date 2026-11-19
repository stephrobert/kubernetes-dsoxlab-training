# Challenge : Étiqueter un nœud, afficher son rôle et le réserver à une équipe

## La situation

Le cluster kubeadm compte trois nœuds : le control plane `k8s-cp.lab` et deux
workers, `k8s-w1.lab` et `k8s-w2.lab`. L'**équipe data** reprend le worker
**`k8s-w2.lab`** : ses traitements y auront le nœud pour eux.

Dans le namespace **`equipes`**, deux applications tournent déjà, ou
voudraient tourner :

- **`rapports`** appartient à une autre équipe. Ses deux réplicas sont
  répartis sur `k8s-w1.lab` et `k8s-w2.lab`.
- **`entrepot`** est l'application de l'équipe data. Elle exige un nœud
  étiqueté pour son équipe et tolère déjà la réserve que vous allez poser. Elle
  reste en **Pending** tant qu'aucun nœud ne porte cette étiquette.

Vous êtes sur le control plane, avec `kubectl` configuré, en root.

## Ce que vous devez obtenir

1. `k8s-w2.lab`, et **aucun autre** nœud, porte l'étiquette **`equipe=data`**.
2. La colonne **ROLES** de `kubectl get nodes` affiche le rôle **`data`** pour
   `k8s-w2.lab`.
3. Le nœud porte l'annotation **`maintenance-contact=data@formation.test`**.
4. Le nœud est **réservé** à l'équipe data par une taint de clé `equipe` et de
   valeur `data` : les Pods des autres équipes **déjà installés** sur le nœud
   doivent en partir, et ne plus y revenir.
5. `entrepot` tourne sur `k8s-w2.lab`, et `rapports` tourne toujours avec ses
   deux réplicas, **ailleurs**.

## Les repères

Une étiquette se pose sur un nœud en service, sans le redémarrer : elle ne
change que les décisions de placement à venir. La colonne ROLES lit les
étiquettes `node-role.kubernetes.io/<rôle>`, dont la valeur est vide par
convention ; elles améliorent la lisibilité, elles ne placent rien.

Une taint repousse les Pods qui ne la tolèrent pas. Toute la question est
l'**effet** : deux des trois effets n'agissent que sur les Pods à venir, le
troisième évince aussi ceux qui sont déjà là. Isoler un nœud déplace les Pods
des autres équipes, cela ne doit pas les arrêter.

## Comment vous saurez que ça marche

Les tests lisent les étiquettes, l'annotation et les taints des nœuds, puis
cherchent où tournent les Pods des deux applications.

```bash
dsoxlab check cka-etiqueter-et-isoler-un-noeud
```
