# Isoler la base de données : seul le backend y accède

## La situation

Dans le namespace **`database`**, la base **`db`** écoute sur le port 5432,
derrière le Service du même nom. Deux applications tournent à côté :
**`backend`**, qui a besoin de la base, et **`frontend`**, qui n'a rien à y
faire. Aujourd'hui, tout le monde peut s'y connecter, y compris depuis les
autres namespaces : un Pod nommé **`intrus`**, dans le namespace `autre`,
porte le label `app=backend` et atteint la base sans difficulté.

Vous êtes sur le control plane, avec `kubectl` configuré.

## Ce que vous devez obtenir

1. Une NetworkPolicy **`db-allow-backend`** dans `database`, qui s'applique
   à la base et ne laisse entrer que les Pods **`app=backend` du même
   namespace**, sur le port **5432** en TCP.

2. `backend` atteint toujours `db` sur 5432.

3. `frontend` n'y arrive plus, et `intrus` non plus, malgré son label.

4. La base peut toujours **sortir** : elle résout des noms. La politique ne
   restreint que ce qui entre.

## Les repères utiles

Une NetworkPolicy sélectionne des Pods par `podSelector`, et dit dans
`policyTypes` ce qu'elle contrôle, l'entrée, la sortie, ou les deux. Dès
qu'un Pod est sélectionné pour l'entrée, tout ce que la politique ne cite
pas est refusé : c'est ce qui isole.

Une règle `from` avec un `podSelector` seul ne vise que le namespace de la
politique. Y ajouter un `namespaceSelector` vide ouvre à tous les
namespaces : c'est l'erreur qui laisserait entrer `intrus`.

`kubectl exec backend -n database -- nc -z -w 3 db 5432` répond 0 si la
connexion s'établit, et rend la main au bout de trois secondes sinon.

## Comment vous saurez que c'est bon

Les tests lisent la politique, puis tentent les connexions depuis
`backend`, `frontend` et `intrus`, et une résolution de nom depuis `db`.

```bash
dsoxlab check cka-networkpolicy-isolate-db
```
