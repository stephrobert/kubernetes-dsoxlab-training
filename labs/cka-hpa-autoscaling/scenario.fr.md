# Faire monter en charge automatiquement avec un HorizontalPodAutoscaler

## La situation

Dans le namespace **`lab`**, l'application **`php-apache`** tourne en un
seul replica derrière le Service du même nom. Chaque requête lui coûte du
CPU, et l'équipe veut qu'elle grossisse d'elle-même sous la charge, jusqu'à
dix replicas, puis redescende. Le cluster a un metrics-server en état de
marche : `kubectl top pods` répond.

Vous êtes sur le control plane, avec `kubectl` configuré.

## Ce que vous devez obtenir

1. Un HorizontalPodAutoscaler **`php-apache-hpa`** dans `lab`, en
   `autoscaling/v2`, qui vise le Deployment `php-apache`, entre **1** et
   **10** replicas, sur une utilisation CPU moyenne cible de **50 %** des
   requests.

2. Le HPA **lit des métriques** : sa cible affiche un pourcentage, pas
   `<unknown>`.

3. Une **montée en charge observée** : sous une charge que vous générez
   depuis un Pod du cluster, le HPA a fait passer le Deployment à au moins
   **deux** replicas. Le contrôleur en laisse la trace.

4. La charge est **coupée** à la fin : aucun Pod générateur ne tourne plus
   dans `lab`.

## Les repères utiles

Le HPA compare l'utilisation CPU des Pods à leurs `requests` : sans
requests, la cible reste `<unknown>` et rien ne bouge. Il relit les
métriques toutes les quinze secondes et décide toutes les trente ; comptez
une à deux minutes entre le début de la charge et le premier Pod
supplémentaire. `kubectl get hpa -w` montre les transitions en direct, et
`kubectl describe hpa` les décisions prises.

Une boucle de `wget` depuis un Pod `busybox` vers le Service suffit à
saturer un replica. Un Pod lancé pour ça se supprime quand on a fini.

## Comment vous saurez que c'est bon

Les tests lisent le HPA, ses métriques courantes, les events du contrôleur
d'autoscaling, et cherchent un générateur de charge encore en marche.

```bash
dsoxlab check cka-hpa-autoscaling
```
