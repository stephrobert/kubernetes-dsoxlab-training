# Challenge : sauvegarder, restaurer et remettre un cluster en ordre

## La situation

Cette nuit, quelqu'un a supprimé le namespace **`facturation`** et son
ConfigMap **`tarifs`**. Depuis, un objet a été écrit dans le cluster :
**`intrus-apres-sauvegarde`**, dans `default`. La sauvegarde de la veille est
dans **`/var/backups/etcd/etcd-veille.db`**.

Le même audit relève deux autres dettes : le dépôt de manifestes **`~/depot`**
ne s'applique plus, et un certificat du plan de contrôle arrive à échéance.

Vous êtes sur **`k8s-cp.lab`**, le plan de contrôle, avec `kubectl`, `etcdctl`,
`etcdutl` et les droits `sudo`. Aucune procédure n'est donnée.

## Ce que vous devez obtenir

1. Une **sauvegarde fraîche** d'etcd dans **`/var/backups/etcd/etcd-fraiche.db`**,
   prise **avant** toute restauration.
2. **etcd** tourne sur un **répertoire de données neuf**, restauré depuis la
   sauvegarde de la veille, et le cluster est **sain** : API et deux nœuds Ready.
3. **`facturation`** et **`tarifs`** sont revenus **à l'identique**.
4. **`intrus-apres-sauvegarde`** n'existe plus.
5. Les manifestes de **`~/depot`** emploient les **API courantes** et leurs objets
   existent dans le namespace **`depot`**, avec leurs réglages.
6. **Aucun certificat** du plan de contrôle n'expire dans moins de **trente
   jours**.

## Notation

Chaque état compte pour une part égale ; le seuil de réussite est de 70 %.
Seul le verdict s'affiche.
