# Épingler une image par son digest, et prouver que le tag ne suffit pas

## La situation

Dans le namespace **`chaine`**, le Deployment **`pinned-app`** tourne en deux
exemplaires. Rien n'est en panne, et c'est le problème : il référence son
image par le tag `nginx:1.27-alpine`.

Un tag est un **nom mutable**. Celui qui contrôle le registre peut le faire
pointer ailleurs demain, et le prochain redémarrage d'un Pod tirera une autre
image sous le même nom, sans qu'aucun manifeste ne change. L'audit de sécurité
demande que les images de production soient référencées de façon **immuable**.

## Ce que vous devez obtenir

1. Le Deployment `pinned-app` référence son image par son **digest**, sous la
   forme `nginx@sha256:...`, et non plus par un tag.

2. Le digest déclaré est **celui de l'image réellement exécutée**. Un digest
   de la bonne forme mais copié d'ailleurs ne vaut rien : c'est précisément ce
   que le dernier test vérifie.

3. Les **deux exemplaires tournent** après le changement. Une référence
   immuable qui empêche le Pod de démarrer n'est pas une amélioration.

4. Le namespace reste `chaine`, le Deployment garde son nom, et vous ne
   changez pas d'image : c'est bien `nginx:1.27-alpine` qui doit être épinglée,
   pas une autre version.

## Les repères utiles

Le digest ne se lit pas dans le manifeste, il se demande au **runtime de
conteneurs** du nœud, ou au registre. Le cluster tourne sous containerd, et
`docker` n'est pas installé : les commandes d'inspection d'images sont celles
de `crictl` et de `ctr`.

Kubernetes, lui, écrit ce qu'il a réellement résolu dans l'état de chaque Pod,
sous `status.containerStatuses[].imageID`. C'est la source la plus directe, et
elle ne ment pas : c'est ce que le nœud exécute.

Attention à la forme. Le champ `image` attend `dépôt@sha256:<hexadécimal>`, et
le dépôt peut s'écrire `nginx` ou `docker.io/library/nginx` selon ce que vous
lisez. Les deux sont acceptés tant que le digest est le bon.

## Comment vous saurez que c'est bon

Les tests lisent l'état du cluster, jamais les commandes tapées. Le dernier
compare le digest que vous avez **déclaré** à celui que le nœud a
**résolu** : c'est le seul qui distingue un épinglage réel d'une chaîne qui
ressemble à un digest.

```bash
dsoxlab check cks-image-pinned-digest
```
