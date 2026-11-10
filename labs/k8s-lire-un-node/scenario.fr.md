# Lire ce que déclare un Node worker

## La situation

Le cluster kind **`architecture`** fait tourner un control plane et trois
workers. Votre `kubectl` le vise déjà. La fiche
**`~/lire-un-node/fiche.txt`** attend ce que le worker
**`architecture-worker2`** dit de lui-même.

## Ce que vous devez obtenir

Pour le Node `architecture-worker2` :

1. **`runtime`** porte son runtime de conteneurs et la version de ce runtime.

2. **`version-kubelet`** porte la version de son kubelet.

3. **`cpu`** et **`memoire`** portent sa **capacité** en CPU et en mémoire.

4. **`condition-ready`** porte le statut de sa condition **Ready**.

## Les repères utiles

Un Node est un objet comme un autre : son kubelet y écrit sans cesse ce que la
machine offre et comment elle se porte. `kubectl get nodes -o wide` donne un
résumé d'une ligne par Node, runtime compris ; `kubectl describe node` donne
la fiche entière : **Conditions**, **Capacity** et **Allocatable**, puis
**System Info**, où se trouvent les versions du kubelet et du runtime.

Capacity, c'est ce que la machine possède ; Allocatable, ce qu'il reste aux
Pods une fois le système servi. La fiche demande la **capacité**.

## Comment vous saurez que c'est bon

Les tests confrontent votre fiche à ce que déclare `architecture-worker2` au
moment du contrôle. Les formes équivalentes sont acceptées : une version avec
ou sans son `v`, une mémoire en Ki, Mi ou Gi.

```bash
dsoxlab check k8s-lire-un-node
```
