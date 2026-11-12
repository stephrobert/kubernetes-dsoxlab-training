# Choisir et déployer le bon workload pour trois besoins

## La situation

Sur le cluster kind **`multi`**, que votre `kubectl` vise déjà, l'entrepôt de la
boutique a trois besoins à servir dans le namespace **`entrepot`**, pour
l'instant vide. Le cluster compte un control plane et deux workers. Le cahier
des charges décrit chaque besoin ; c'est à vous de choisir le type d'objet qui
le sert. Le répertoire **`~/entrepot/`** contient la définition d'une ressource
personnalisée, **`collecte-crd.yaml`**, que personne n'a encore installée.

L'image à utiliser pour la base comme pour l'agent :

```text
busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
```

## Le cahier des charges

1. **La base `inventaire`** tourne en **trois réplicas** à **identité stable**,
   créés dans l'ordre et nommés **`inventaire-0`**, **`inventaire-1`** et
   **`inventaire-2`**, tous **Ready**.
2. Chaque réplica se joint par un **nom stable** de la forme
   **`inventaire-N.<service>`**, servi par un Service **sans adresse de
   cluster**.
3. Chaque réplica a **son propre volume**, monté sur **`/data`**. Le fichier
   **`/data/marque`** du réplica 1 porte en première ligne **`inventaire-1`**.
   Supprimez le Pod `inventaire-1` : le Pod recréé relit ce fichier **intact**.
4. **L'agent `collecteur`** tourne en **un exemplaire sur chaque nœud**, et
   chaque exemplaire est **Ready**.
5. Le nœud du control plane **garde son taint** : l'agent y tourne parce qu'il
   le **tolère**, pas parce que le taint a été retiré.
6. La ressource personnalisée **`Collecte`** est installée et **Established**.
   La Collecte **`journaux`**, dans `entrepot`, a pour cible **`/var/log`**,
   collecte toutes les **60 secondes** et garde **30 jours**, rien de plus.
7. L'API **refuse** toute Collecte gardée **plus de 90 jours**. Le fichier fourni
   ne l'impose pas encore.

## Comment vous serez noté

Le challenge est noté sur l'**état final** du cluster, jamais sur les commandes
tapées. Les **sept exigences pèsent toutes autant**. Le seuil est de **70 sur
100**, et **trois exigences sont bloquantes** : elles doivent réussir quel que
soit le total. Ce sont la donnée du réplica 1 relue intacte (exigence 3), le
taint du control plane gardé et toléré (exigence 5), et la Collecte `journaux`
conforme avec sa ressource Established (exigence 6).

Quatre **indices** sont proposés, et chacun retire des points du barème avant
le calcul de la note : 2, 3, 5 puis 5, soit 15 au plus. Sans indice, sept
exigences donnent 100, six en donnent 86 et cinq en donnent 71. Avec le premier
indice, cinq exigences donnent encore 70 ; avec les deux premiers, elles n'en
donnent plus que 68, sous le seuil. Avec les quatre, il faut au moins six
exigences (73).

Aucune procédure n'est donnée : les leçons du module ont tout enseigné.

```bash
dsoxlab check  k8s-challenge-choisir-le-bon-workload
dsoxlab submit k8s-challenge-choisir-le-bon-workload
```
