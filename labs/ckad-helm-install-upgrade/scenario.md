# Installer, mettre à jour et revenir en arrière avec Helm 4

## La situation

L'équipe livre son application web sous forme de **chart Helm**, dans le
répertoire **`~/charts/web`** du control plane. Helm est installé, en
version 4. Le namespace **`lab`** existe, vide.

On vous demande de dérouler le cycle complet d'une release, celui que
l'exploitation fera chaque semaine : installer, monter en charge, puis
revenir en arrière quand la montée en charge pose problème.

## Ce que vous devez obtenir

1. Une release **`web`** dans `lab`, installée depuis `~/charts/web`, avec
   **un** replica.

2. La release **mise à jour** avec **deux** replicas.

3. La release **revenue à sa première révision** : un replica, et
   l'historique qui montre les trois révisions, install, upgrade, rollback.

4. L'application **tourne** et **répond** : le Deployment est prêt, et son
   Service sert la page nginx.

## Les repères utiles

Une release Helm garde son historique dans le cluster : chaque `install`,
`upgrade` ou `rollback` crée une révision, et `helm history` les liste avec
leur description. Un rollback ne supprime pas la révision qu'il annule : il
en crée une nouvelle.

Le nombre de replicas de ce chart est une **valeur**, dans son
`values.yaml`, et se change à la ligne de commande.

## Comment vous saurez que c'est bon

Les tests lisent l'historique de la release, les valeurs de chaque
révision, l'état du Deployment, et interrogent le Service.

```bash
dsoxlab check ckad-helm-install-upgrade
```
