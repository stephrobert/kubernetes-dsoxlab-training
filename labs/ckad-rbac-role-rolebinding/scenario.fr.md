# Donner un accès en lecture seule aux Pods avec RBAC

## La situation

Une développeuse, connue du cluster sous le nom **`dev-user`**, doit suivre
ses déploiements dans le namespace **`lab`** : voir les Pods, et lire leurs
logs. Rien de plus. Elle ne doit ni créer ni supprimer quoi que ce soit, ni
voir ce qui tourne dans les autres namespaces.

Le namespace existe, avec une application dedans, le Pod **`journal`**, qui
écrit dans ses logs. Pour l'instant, `dev-user` n'a aucun droit.

## Ce que vous devez obtenir

1. Un Role **`pod-reader`** dans `lab`, qui autorise à lire les Pods et
   leurs logs.

2. Un RoleBinding **`read-pods-binding`** dans `lab`, qui donne ce Role à
   l'utilisatrice `dev-user`.

3. `dev-user` peut lister les Pods de `lab` et lire les logs de `journal`.

4. `dev-user` ne peut **pas** créer de Pod dans `lab`, et ne peut **pas**
   lister les Pods de `default`.

## Les repères utiles

`kubectl auth can-i <verbe> <ressource> -n <namespace> --as <utilisateur>`
répond `yes` ou `no` sans rien créer : c'est votre instrument de mesure,
avant comme après. Vous pouvez aussi exécuter une commande **en tant que**
`dev-user`, avec `--as`.

Les logs d'un Pod ne sont pas le Pod : ils sont une sous-ressource, qui se
nomme à part.

## Comment vous saurez que c'est bon

Les tests lisent le Role et le RoleBinding, puis ils interrogent l'API en
tant que `dev-user`, pour ce qui doit passer comme pour ce qui doit être
refusé.

```bash
dsoxlab check ckad-rbac-role-rolebinding
```
