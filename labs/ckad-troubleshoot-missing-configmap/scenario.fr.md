# Un Pod bloqué par un ConfigMap qui n'existe pas

## La situation

Dans le namespace **`lab`**, le Pod **`broken-app`** a été livré il y a une
heure, et il n'a toujours pas démarré. `kubectl logs` ne rend rien : il n'y
a même pas de conteneur à interroger. L'application lit un fichier de
configuration au démarrage, **`/config/settings.conf`**, puis sert des
pages web.

Le collègue qui l'a livrée est parti en congé. Son manifeste est dans le
cluster ; sa configuration, apparemment, non.

## Ce que vous devez obtenir

1. La cause du blocage, lue dans les **events** du Pod.

2. La ressource manquante créée, avec la clé **`settings.conf`** dont le
   contenu comporte la ligne `mode=production`.

3. Le Pod `broken-app` en **`Running`**, sans que vous l'ayez recréé :
   Kubernetes réessaie tout seul dès que ce qui manque apparaît.

4. L'application **sert** : sa page répond en HTTP.

## Les repères utiles

Un Pod en `ContainerCreating` qui ne bouge pas n'a pas de logs : le
conteneur n'existe pas encore. Ce qui l'empêche de naître est raconté dans
ses events, en bas de `kubectl describe pod`, avec le nom de ce qui manque.

Un volume qui référence un ConfigMap absent bloque le Pod indéfiniment, et
le débloque dès que le ConfigMap existe : pas besoin de le supprimer.

## Comment vous saurez que c'est bon

Les tests lisent le ConfigMap, l'état du Pod, et interrogent l'application
depuis le nœud.

```bash
dsoxlab check ckad-troubleshoot-missing-configmap
```
