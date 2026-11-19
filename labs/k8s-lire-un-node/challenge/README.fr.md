# Challenge : Lire ce que déclare un Node worker

## 📍 La situation

Le cluster kind **`architecture`** fait tourner un control plane et trois
workers. Votre kubectl le vise déjà. La fiche **`~/lire-un-node/fiche.txt`**
attend ce que le nœud **`architecture-worker2`** dit de lui-même.

## 🎯 Ce que vous devez obtenir

Pour le nœud `architecture-worker2`, complétez la fiche :

1. Après **`runtime`** : le programme qui lance ses conteneurs, et sa version.

2. Après **`version-kubelet`** : la version de son kubelet.

3. Après **`cpu`** et **`memoire`** : sa **capacité** en processeur et en
   mémoire.

4. Après **`condition-ready`** : la valeur de sa condition **Ready**.

## 🧭 Les repères utiles

`kubectl get nodes -o wide` donne une ligne par nœud, avec le runtime et la
version du kubelet. `kubectl describe node` donne la fiche complète : les
conditions (`Conditions`), la capacité (`Capacity`), ce qui reste aux Pods
(`Allocatable`), puis les versions (`System Info`).

`Capacity`, c'est ce que la machine possède. `Allocatable`, c'est ce qui reste
aux Pods. La fiche demande la **capacité**.

## ✅ Comment vous saurez que c'est bon

Les tests comparent votre fiche à ce que déclare `architecture-worker2` au
moment du contrôle. Plusieurs façons d'écrire sont acceptées : une version
avec ou sans son `v`, une mémoire en Ki, Mi ou Gi.

```bash
dsoxlab check k8s-lire-un-node
```
