# Isoler un Pod du noyau de l'hôte, et le prouver en lisant sa version

## La situation

Un conteneur ordinaire partage le **noyau de la machine** avec tous les
autres, et avec le nœud lui-même. Une faille de ce noyau est une faille pour
tout ce qui tourne dessus.

L'équipe sécurité veut qu'une charge de travail sensible s'exécute dans un
**bac à sable** : un runtime qui interpose son propre noyau applicatif entre
le conteneur et la machine.

Le nœud est prêt. `containerd` connaît désormais **deux** runtimes : celui qui
sert par défaut, et un second nommé `runsc`. Dans le namespace
**`bac-a-sable`**, un Pod **`ordinaire`** tourne déjà avec le runtime par
défaut : c'est votre point de comparaison, n'y touchez pas.

## Ce que vous devez obtenir

1. Un objet qui déclare le second runtime au cluster, sous le nom
   **`gvisor`**. Son handler doit correspondre exactement au nom que
   `containerd` emploie.

2. Un Pod **`confine`** dans `bac-a-sable`, image `busybox:1.37`, qui
   s'exécute dans ce bac à sable et qui **tourne**.

3. Depuis l'intérieur de ce Pod, la version du noyau n'est **pas** celle de la
   machine.

4. Le Pod `ordinaire`, lui, continue de lire le noyau de la machine.

## Les repères utiles

L'objet qui fait le pont entre un nom employé par les Pods et un runtime connu
de `containerd` n'a **pas de namespace** : il vaut pour tout le cluster.

Le nom que `containerd` donne au runtime se lit dans sa configuration, sous
`/etc/containerd/config.toml`. Il n'est pas forcément celui que vous
choisirez pour l'objet Kubernetes, et c'est justement ce que cet objet relie.

Un Pod dont le runtime demandé est inconnu de `containerd` ne démarre pas et
**reste en attente**, sans message évident : `kubectl describe pod` le dit
dans ses events.

Le champ qui choisit le runtime d'un Pod ne se modifie pas sur un Pod
existant. Il faut le recréer.

`cat /proc/version` dans un conteneur dit quel noyau il voit. `uname -r` sur
le nœud dit celui de la machine.

## Comment vous saurez que c'est bon

Le dernier test compare le noyau vu par **les deux** Pods, et celui de la
machine. Il ne cherche pas un mot particulier : il constate que le Pod confiné
et le Pod ordinaire ne lisent pas le même noyau, et que le second lit bien
celui du nœud. Sans ce point de comparaison, la mesure ne voudrait rien dire.

```bash
dsoxlab check cks-runtime-sandbox-gvisor
```
