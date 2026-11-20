# Challenge : Lire ce que déclare un Node worker

## 📍 La situation

Le cluster kind **`architecture`** fait tourner un control plane et trois
workers. Votre kubectl le vise déjà. La fiche **`~/lire-un-node/fiche.txt`**
attend ce que le nœud **`architecture-worker2`** dit de lui-même.

## 🎯 Ce que vous devez obtenir

Pour le nœud `architecture-worker2`, complétez la fiche :

1. Après **`adresse-interne`** : son adresse IP interne.

2. Après **`plage-des-pods`** : la plage d'adresses dans laquelle ses Pods
   reçoivent leur adresse.

3. Après **`machine-id`** : son identifiant de machine.

4. Après **`ready-depuis`** : la date et l'heure auxquelles il est devenu
   **Ready**.

## 🧭 Les repères utiles

`kubectl describe node` donne la fiche complète d'un nœud, section par
section : les conditions (`Conditions`), les adresses (`Addresses`), la
capacité (`Capacity`), les versions et identifiants (`System Info`), puis la
plage d'adresses des Pods (`PodCIDR`).

Ces quatre valeurs sont propres à `architecture-worker2` : les autres nœuds en
ont d'autres. Lisez bien la fiche de ce nœud-là, et recopiez chaque valeur
seule sur sa ligne.

## ✅ Comment vous saurez que c'est bon

Les tests comparent votre fiche à ce que déclare `architecture-worker2` au
moment du contrôle. L'heure se recopie telle que `kubectl describe node`
l'affiche, ou au format `2026-11-20T07:28:14Z` de `kubectl get -o yaml`.

```bash
dsoxlab check k8s-lire-un-node
```
