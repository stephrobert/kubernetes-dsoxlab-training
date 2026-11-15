# Vider, maintenir et remettre en service un nœud, puis monter le cluster de version

## La situation

Le cluster kubeadm tourne en **1.36.4**, une version mineure en retard. Dans le
namespace **`maintenance`**, l'application **`catalogue`** sert en **quatre
exemplaires**, répartis sur le plan de contrôle et le worker. Un outil de
diagnostic, le Pod **`outil-diag`**, traîne sur le worker sans contrôleur ;
l'équipe ne le regrettera pas.

Le planning de la nuit :

- le worker **`k8s-w1.lab`** part en maintenance matérielle, puis revient ;
- ensuite, tout le cluster monte en **1.37.0** ;
- et à aucun moment `catalogue` ne doit tomber sous **deux exemplaires
  disponibles**.

En pleine nuit, l'équipe du catalogue demande en plus de porter tout de suite
**`MAX_CONNEXIONS`** de sa configuration (le ConfigMap **`catalogue-config`**)
de `50` à **`200`**. Ses manifestes vivent dans le dépôt git **`~/maintenance`**,
et c'est lui qui fait foi au prochain déploiement.

Vous êtes sur **`k8s-cp.lab`**, le plan de contrôle, avec `kubectl` configuré
et les droits `sudo`. `ssh k8s-w1.lab` ouvre une session sur le worker, où vous
avez aussi `sudo`. Aucune procédure n'est donnée : le module vous a appris ce
qu'il faut.

## Ce que vous devez obtenir

1. Un **PodDisruptionBudget** nommé **`catalogue-pdb`** garantit **au moins
   deux** Pods de `catalogue` disponibles, et vise bien ses Pods.
2. Le worker a été **évacué** : les Pods de `catalogue` qu'il portait ont été
   recréés ailleurs, `outil-diag` a disparu, et le DaemonSet du réseau y est
   **resté**.
3. Le worker est **remis en service** : il accepte de nouveau des Pods.
4. Un ConfigMap **`drain-evidence`**, dans `maintenance`, garde la trace de
   l'opération : la clé **`drained-node`** nomme le nœud vidé, la clé
   **`status`** vaut **`completed`**.
5. L'**API server** annonce la version **1.37.0**.
6. **Chaque nœud** annonce **1.37.0**, **aucun** n'est resté inordonnançable,
   et `catalogue` a **ses quatre exemplaires prêts**.
7. Dans le cluster, `MAX_CONNEXIONS` vaut **`200`**, et le **dernier commit**
   du dépôt `~/maintenance` porte **la même valeur**.

## Comment vous serez noté

Sept états, à poids égal. Le seuil est de **70 sur 100**, et les états **2 et
6** sont **bloquants** : le worker évacué, et tout le cluster monté sans perdre
l'application. Réussir les autres ne compense pas l'un d'eux manqué.

Les tests lisent l'état du cluster et le dépôt git, jamais les commandes
tapées. Pour l'état 3, le correcteur lance un Pod éphémère,
`sonde-placement`, que le scheduler doit placer sur le worker, puis le retire.
Le retour se limite au verdict : réussi ou non, et la note.

```bash
dsoxlab check  k8s-challenge-maintenir-un-noeud
dsoxlab submit k8s-challenge-maintenir-un-noeud
```
