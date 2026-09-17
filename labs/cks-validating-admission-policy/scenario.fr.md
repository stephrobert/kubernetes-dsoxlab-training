# Faire refuser une image non épinglée par le cluster lui-même, sans webhook

## La situation

Le namespace **`production`** accepte n'importe quelle image, y compris désignée par
un simple **tag**. Or un tag n'est qu'un nom : il peut être redirigé vers un
autre contenu sans que rien ne change dans le manifeste, et le Pod redémarré
tirera alors autre chose que ce qui avait été validé.

Un lab voisin vous a fait épingler une image. Celui-ci vous demande le geste de
l'exploitant, qui n'exige plus la discipline de chacun : **faire refuser** par
le cluster ce qui ne l'est pas.

Un Pod **`conforme`** tourne déjà dans ce namespace, épinglé par son digest.
N'y touchez pas : il sert à vérifier que votre politique ne bloque pas tout.

## Ce que vous devez obtenir

1. Créer dans `production` un Pod dont l'image est désignée par un **tag** est
   **refusé**.

2. Créer un Pod dont l'image est **épinglée par son digest** reste **accepté**.

3. Le refus vient du **cluster lui-même**, sans composant supplémentaire à
   installer ni à maintenir en vie.

4. Les autres namespaces ne sont pas affectés, à commencer par ceux du système,
   dont les images ne sont pas épinglées.

## Les repères utiles

Ce qu'il faut poser est **natif** et évalué par l'API server. `kubectl
api-resources --api-group=admissionregistration.k8s.io` en donne la liste.

Il en faut **deux** : la règle, et ce qui dit **où** elle s'applique. La
première seule est un objet parfaitement valide qui n'agit sur rien.

La règle s'écrit en **CEL**. Pour parcourir les conteneurs d'un Pod, une forme
exige que **tous** satisfassent la condition, une autre qu'**au moins un** la
satisfasse. Elles ne protègent pas de la même chose.

Du côté de la liaison, deux champs décident de tout : celui qui choisit ce
qu'on fait des violations, où deux valeurs sur trois **laissent passer**, et
celui qui restreint la portée. Sans restriction, la politique vaudrait pour
**tout** le cluster.

Chaque namespace porte un label que Kubernetes pose lui-même et qui vaut son
nom.

Laissez quelques secondes à l'API server avant de conclure.

## Comment vous saurez que c'est bon

Le dernier test crée réellement les **deux** Pods, l'un par tag et l'autre par
digest, et vérifie que le premier est refusé et le second accepté. Relire votre
politique ne prouverait rien : une règle sans liaison n'agit sur rien, et une
liaison qui se contente d'avertir laisse passer.

```bash
dsoxlab check cks-validating-admission-policy
```
