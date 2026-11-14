# Contenir un déni de service dans son namespace

## La situation

Sur le cluster kubeadm partagé, le namespace **`bac-a-sable`** est ouvert à
toutes les équipes pour leurs essais. Rien ne le plafonne. Le Deployment
**`gourmand`** y tourne, deux réplicas qui ne déclarent **ni requests ni
limits** : chacun garde un bloc de mémoire et occupe un processeur par
rafales. Ici, la charge est bornée exprès, pour que le nœud reste sûr. Une
vraie charge ne s'arrêterait pas là.

Dans le namespace **`annuaire`**, une application de deux réplicas répond
derrière son Service. Elle doit continuer de répondre, quoi qu'il tourne dans
`bac-a-sable`.

Vous êtes sur le plan de contrôle, avec `kubectl` configuré.

## Ce que vous devez obtenir

1. **`bac-a-sable`** porte un **ResourceQuota** qui plafonne, au plus :
   `requests.cpu` à **1**, `requests.memory` à **1Gi**, `limits.cpu` à **2** et
   `limits.memory` à **2Gi**.
2. Un conteneur qui ne déclare aucune ressource dans `bac-a-sable` reçoit **par
   défaut** des requests de **100m** de processeur et **128Mi** de mémoire, et
   des limits de **300m** de processeur et **256Mi** de mémoire.
3. Une **création au-delà du quota** est refusée par le cluster.
4. Les **Pods en marche** de `gourmand`, toujours au nombre de deux, portent
   des **requests et des limits**.
5. Pendant que `gourmand` tourne bornée, l'application d'**`annuaire`** garde
   ses deux réplicas et **répond**.

## La méthode, pas à pas

**Regarder d'abord la menace.** `kubectl get pods -n bac-a-sable -o
custom-columns=NOM:.metadata.name,QOS:.status.qosClass` montre des Pods
`BestEffort` : aucune request, aucune limit, rien de réservé et rien de
plafonné. `kubectl describe node` liste, nœud par nœud, ce que les Pods ont
demandé : ces deux-là ne comptent pour rien, quoi qu'ils consomment. Un déni de
service vise le processeur et la mémoire des nœuds, le nombre de Pods et
d'objets, les requêtes vers l'API server et le stockage.

**Plafonner le namespace.** Un ResourceQuota nomme chaque ressource qu'il
plafonne : `requests.cpu`, `requests.memory`, `limits.cpu`, `limits.memory`, et
au besoin `pods` ou un nombre d'objets. Une clé qu'il ne nomme pas n'est pas
plafonnée.

**Donner des valeurs par défaut en même temps.** Dès qu'un quota porte sur les
requests ou les limits, un Pod qui n'en déclare pas est refusé, puisque l'API
ne peut pas le décompter. Un LimitRange de type `Container` remplit
`defaultRequest` et `default` à l'arrivée. Posez les deux ensemble, sinon le
prochain redémarrage d'une application du namespace échoue.

**Éprouver le refus pour de vrai.** Créez un Pod qui demande plus que ce qui
reste dans le quota : le cluster répond `exceeded quota`, avec ce qui est
demandé, utilisé et plafonné. `kubectl describe resourcequota -n bac-a-sable`
montre les compteurs.

**Borner ce qui tourne déjà.** Le quota et les valeurs par défaut s'appliquent
à la création d'un Pod, jamais aux Pods déjà en marche. `kubectl rollout
restart` recrée ceux de `gourmand`, qui reçoivent alors les valeurs par défaut.
Ne supprimez pas la charge : la leçon est de la contenir pendant qu'elle tourne.

**Vérifier le voisin.** `kubectl get svc -n annuaire` donne l'adresse du
Service ; quelques requêtes `curl` depuis le nœud prouvent qu'il répond.

## Comment vous saurez que ça marche

Les tests lisent le quota de `bac-a-sable`, y créent deux Pods sondes, l'un qui
ne déclare rien et l'autre qui demande trop, et regardent ce que le cluster en
fait. Puis ils lisent les Pods en marche de `gourmand` et envoient de vraies
requêtes HTTP à `annuaire` pendant que la charge tourne.

```bash
dsoxlab check k8s-contenir-un-deni-de-service
```
