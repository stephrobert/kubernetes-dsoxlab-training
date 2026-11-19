# Challenge : Rendre lisible la santé d'un cluster et rédiger son bulletin

## La situation

On vous confie un cluster kubeadm de trois nœuds pour la journée. Avant de
toucher quoi que ce soit, l'équipe veut un **bulletin de santé**. Problème :
`kubectl top` ne répond rien, car **metrics-server n'est pas installé**.

Son manifeste officiel, épinglé en **version 0.9.0**, vous attend dans
**`~/sante/metrics-server-v0.9.0.yaml`**. Le namespace **`sante`** porte les
Pods à surveiller.

Vous êtes sur le control plane, avec `kubectl` configuré.

## Ce que vous devez obtenir

1. **`kubectl top nodes` répond** : la Metrics API (`v1beta1.metrics.k8s.io`)
   est disponible.
2. Un ConfigMap **`bulletin`** dans le namespace `sante` porte deux clés :
   - **`pod-le-plus-gourmand`** : le nom du Pod de `sante` qui consomme le plus
     de **mémoire**, tel que `kubectl top` le mesure ;
   - **`noeud-le-plus-reserve`** : le nom du nœud dont le **CPU allouable est
     le plus réservé par les demandes** (`requests`) des Pods qui y tournent.

## Les repères

Sur un cluster kubeadm, les kubelets servent des certificats auto-signés.
metrics-server les refuse par défaut : la Metrics API reste alors indisponible
et `kubectl top` répond `Metrics API not available`. En lab, l'option
`--kubelet-insecure-tls` lève ce refus ; en production, on signe les
certificats des kubelets.

Deux mesures ne disent pas la même chose. `kubectl top` montre la
**consommation du moment**. La section `Allocated resources` de
`kubectl describe node` montre ce qui est **réservé** par les demandes, que le
Pod s'en serve ou non. C'est sur cette réservation que le scheduler décide.

Le Pod gourmand change à chaque `dsoxlab run` : mesurez, ne devinez pas.

## Comment vous saurez que ça marche

Les tests interrogent la Metrics API et l'APIService, recalculent eux-mêmes le
Pod le plus gourmand et le nœud le plus réservé, puis comparent avec votre
bulletin.

```bash
dsoxlab check k8s-observer-la-sante-d-un-cluster
```
