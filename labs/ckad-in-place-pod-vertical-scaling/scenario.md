# Redimensionner un Pod en place, sans le redémarrer

## La situation

Le Pod **`scaling-pod`** du namespace **`lab`** tourne depuis des semaines
avec un budget devenu trop juste : `100m` de CPU demandés, `128Mi` de
mémoire en limite. Il tient une session longue qu'on ne veut **pas
interrompre**. Il faut lui donner plus, maintenant, sans le recréer et sans
que son conteneur redémarre.

Le Pod a été livré avec une politique de redimensionnement qui l'autorise.
Longtemps, changer les ressources d'un Pod signifiait le supprimer ; ce
n'est plus vrai.

## Ce que vous devez obtenir

1. `scaling-pod` demande **`200m`** de CPU et se limite à **`256Mi`** de
   mémoire.

2. Le Pod n'a **pas été recréé** : c'est le même objet, avec la même date de
   création, et son conteneur affiche **zéro redémarrage**.

3. Le noyau applique la nouvelle limite : lue depuis l'intérieur du
   conteneur, elle vaut 256Mi.

## Les repères utiles

`kubectl edit` refuse de changer les ressources d'un Pod : ce champ passe
par une **sous-ressource** dédiée, que `kubectl patch` sait viser. Le
statut du Pod indique ensuite les ressources réellement allouées par le
kubelet, qui peuvent différer un instant de celles demandées.

La limite de mémoire qu'un conteneur subit se lit dans son cgroup.

## Comment vous saurez que c'est bon

Les tests lisent les ressources du Pod, sa date de création, son compteur
de redémarrages, et la limite dans le cgroup du conteneur.

```bash
dsoxlab check ckad-in-place-pod-vertical-scaling
```
