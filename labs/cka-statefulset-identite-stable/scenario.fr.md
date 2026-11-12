# Donner une identité stable à chaque réplica avec un StatefulSet

## La situation

Sur le cluster kind **`lab`**, que votre `kubectl` vise déjà, le namespace
**`identites`** fait tourner l'**`annuaire`** en **Deployment** à trois
réplicas. Ses Pods portent des noms tirés au hasard, changent de nom à chaque
recréation et ne gardent rien. Or chaque réplica de l'annuaire doit être joint
par un nom qui ne bouge pas, et garder ses propres données.

L'image de l'annuaire :

```text
busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
```

## Ce que vous devez obtenir

1. Un **StatefulSet `annuaire`** à **trois réplicas** : les Pods **`annuaire-0`**,
   **`annuaire-1`** et **`annuaire-2`** sont tous **Ready**.
2. Un **Service headless `annuaire`** sélectionne ces Pods, et le StatefulSet le
   désigne comme son Service.
3. Depuis un autre Pod, chaque nom stable, **`annuaire-0.annuaire`** à
   **`annuaire-2.annuaire`**, se résout vers son Pod.
4. Chaque réplica a **sa propre revendication**, issue d'un gabarit nommé
   **`donnees`**, **Bound** et montée sur **`/data`**.
5. Le fichier **`/data/identite`** du réplica 1 porte en première ligne
   **`annuaire-1`**. Supprimez le Pod `annuaire-1` : le Pod recréé relit ce
   fichier, sans qu'il ait été réécrit.
6. Le **Deployment `annuaire`** a laissé la place : un seul annuaire répond.

## Les repères utiles

Un Deployment donne des Pods interchangeables. Un StatefulSet numérote ses Pods
de 0 à n-1, les crée dans l'ordre, et rend à un Pod recréé le même nom et le
même volume.

Les noms stables ne se résolvent que derrière un Service **sans adresse de
cluster**, que le StatefulSet désigne. Le nom court `annuaire-1` seul ne se
résout pas : il lui faut le nom du Service.

Un volume par réplica ne se déclare pas dans les volumes du Pod, mais dans un
**gabarit de revendication** du StatefulSet. La classe par défaut du cluster
crée chaque volume à la demande.

Écrivez le fichier témoin une seule fois, depuis le Pod en marche. Si la
commande du conteneur l'écrit à chaque démarrage, rien ne prouve plus qu'il a
survécu.

## Comment vous saurez que c'est bon

Chaque test vérifie un des six états ci-dessus. Pour les noms stables, le test
résout chaque nom depuis un autre réplica et compare l'adresse obtenue à celle
du Pod. Pour la donnée, il lit le fichier et les événements du StatefulSet, qui
disent combien de fois le Pod `annuaire-1` a été créé.

```bash
dsoxlab check cka-statefulset-identite-stable
```
