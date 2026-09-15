# Trois sondes sur un Pod : startup, liveness, readiness

## La situation

L'application **`probed-app`** du namespace **`lab`** est un serveur web,
image `nginx:1.27-alpine`, qui répond sur le port 80. Elle a deux défauts
connus : elle met parfois **longtemps à démarrer**, jusqu'à une minute, et
il lui arrive de **se figer** sans mourir. Sans sondes, Kubernetes la croit
en bonne santé dans les deux cas, et lui envoie du trafic.

L'équipe veut les trois sondes, chacune pour ce qu'elle sait faire.

## Ce que vous devez obtenir

1. Un Pod **`probed-app`** dans `lab`, avec cette image, qui déclare son
   port 80.

2. Une sonde de **démarrage** en HTTP sur ce port, qui tolère un démarrage
   lent : au moins **une minute** d'échecs consécutifs avant d'abandonner.

3. Une sonde de **vivacité** en HTTP sur ce port, qui relance le conteneur
   s'il ne répond plus.

4. Une sonde de **disponibilité** en HTTP sur ce port, qui retire le Pod du
   trafic tant qu'il ne répond pas.

5. Le Pod est **`Running`** et **`Ready`**, sans redémarrage : c'est la
   preuve que les trois sondes trouvent ce qu'elles cherchent.

## Les repères utiles

Une sonde HTTP qui vise un mauvais chemin ou un mauvais port échoue en
silence : le Pod reste `Running`, mais jamais `Ready`, ou redémarre en
boucle. `kubectl describe pod` raconte chaque échec de sonde dans ses
events.

La tolérance d'une sonde est un produit : le nombre d'échecs admis
multiplié par l'intervalle entre deux essais.

## Comment vous saurez que c'est bon

Les tests lisent les trois sondes dans la définition du Pod, puis son état :
`Ready`, sans redémarrage.

```bash
dsoxlab check ckad-probes-all-types
```
