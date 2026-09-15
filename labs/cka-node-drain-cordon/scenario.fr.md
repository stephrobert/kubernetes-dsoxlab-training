# Vider un worker pour une maintenance, sans couper le service

## La situation

Le worker **`k8s-w1.lab`** doit recevoir une mise à jour de noyau ce soir,
avec redémarrage. L'application **`web`**, dans le namespace **`lab`**,
tourne en quatre replicas répartis sur les deux nœuds, et le service ne doit
pas être interrompu pendant l'opération.

Un Pod hors de tout contrôleur, **`outil-diag`**, traîne aussi sur ce
worker : un collègue l'a lancé à la main la semaine dernière et il peut
disparaître.

Vous êtes sur le control plane, avec `kubectl` configuré.

## Ce que vous devez obtenir

1. Un **PodDisruptionBudget** nommé **`web-pdb`**, dans le namespace `lab`,
   qui garantit qu'**au moins deux** Pods de `web` restent disponibles à tout
   moment. Il doit viser les Pods de l'application, pas un label inventé.

2. Le worker `k8s-w1.lab` **retiré du scheduling puis évacué** de tous les
   Pods qui peuvent l'être : ceux de `web` sont recréés sur l'autre nœud,
   `outil-diag` est supprimé, et le DaemonSet du réseau, lui, reste en place.

3. La maintenance faite, le worker **remis en service** : il accepte de
   nouveau des Pods.

4. Un ConfigMap **`drain-evidence`** dans `lab`, avec deux clés :
   `drained-node` qui vaut le nom du nœud vidé, et `status` qui vaut
   `completed`.

## Les repères utiles

Retirer un nœud du scheduling et l'évacuer sont deux gestes distincts, et
l'ordre compte. L'évacuation passe par l'API d'éviction, qui respecte les
budgets de disruption : c'est ce qui rend l'opération sûre, et c'est aussi
ce qui la fait attendre quand le budget est atteint.

L'évacuation refuse par défaut ce qu'elle ne saurait pas recréer : les Pods
gérés par un DaemonSet, ceux qui n'ont aucun contrôleur, et ceux qui
portent des volumes `emptyDir`. Chacun de ces refus a son option, et la
consigne dit ce qu'il faut en faire.

## Comment vous saurez que c'est bon

Les tests lisent le budget et son état, la date de création de chaque Pod
de `web` et le nœud qui le porte, l'état du worker, et le ConfigMap.

```bash
dsoxlab check cka-node-drain-cordon
```
